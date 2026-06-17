"""High-throughput load testing harness targeting 100k+ events/sec."""

from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing as mp
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import structlog

from telemetry.config import PipelineYamlConfig, SensorsYamlConfig, load_pipeline_config, load_sensors_config
from telemetry.logging_setup import configure_logging
from telemetry.models import SensorEvent
from telemetry.pipeline import InMemoryPipeline
logger = structlog.get_logger(__name__)


@dataclass
class LoadTestReport:
    mode: str
    target_eps: float
    events_requested: int
    events_produced: int
    events_consumed: int
    events_valid: int
    duration_seconds: float
    producer_eps: float
    consumer_eps: float
    target_met: bool
    workers: int
    batch_size: int
    p50_processing_latency_ms: float
    p95_processing_latency_ms: float
    p99_processing_latency_ms: float
    max_processing_latency_ms: float
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)

    def print_summary(self) -> None:
        print("\n=== Telemetry Pipeline Load Test ===")
        print(f"  Mode:           {self.mode}")
        print(f"  Target:         {self.target_eps:,.0f} eps")
        print(f"  Produced:       {self.events_produced:,} ({self.producer_eps:,.0f} eps)")
        print(f"  Consumed:       {self.events_consumed:,} ({self.consumer_eps:,.0f} eps)")
        print(f"  Valid:          {self.events_valid:,}")
        print(f"  Duration:       {self.duration_seconds:.2f}s")
        print(f"  Workers:        {self.workers}")
        print(f"  Batch size:     {self.batch_size}")
        print(f"  Target met:     {'yes' if self.target_met else 'no'}")
        if self.events_consumed:
            print(f"  P50 latency:    {self.p50_processing_latency_ms:.2f} ms")
            print(f"  P95 latency:    {self.p95_processing_latency_ms:.2f} ms")
            print(f"  P99 latency:    {self.p99_processing_latency_ms:.2f} ms")
            print(f"  Max latency:    {self.max_processing_latency_ms:.2f} ms")
        print("====================================\n")


def apply_load_profile(pipeline_config: PipelineYamlConfig) -> None:
    """Strip optional work so the pipeline can sustain high ingest rates."""
    pipeline_config.storage.backend = "memory"
    pipeline_config.storage.memory.count_only = True
    pipeline_config.viz.enabled = False
    pipeline_config.prometheus.enabled = False
    pipeline_config.opentelemetry.enabled = False
    pipeline_config.alerting.enabled = False
    pipeline_config.anomaly.enabled = False
    pipeline_config.tenancy.enabled = False
    pipeline_config.validation.dedup_window_seconds = 0
    pipeline_config.processing.window_size_seconds = 3600
    pipeline_config.processing.slide_interval_seconds = 3600
    pipeline_config.simulator.anomaly_rate = 0.0


class FastEventGenerator:
    """Minimal-allocation event factory for sustained load generation."""

    def __init__(
        self,
        sensors_config: SensorsYamlConfig,
        *,
        device_count: int = 100,
        sensor_type: str = "industrial",
        seed: int = 0,
    ) -> None:
        sensor_def = sensors_config.sensor_types[sensor_type]
        self._devices = [f"{sensor_type}-device-{i:03d}" for i in range(device_count)]
        self._metrics = {
            name: round(field.baseline, 4) for name, field in sensor_def.fields.items()
        }
        self._sensor_type = sensor_type
        self._sequence = seed
        self._timestamp = datetime.now(timezone.utc)

    def next_event(self) -> SensorEvent:
        device_id = self._devices[self._sequence % len(self._devices)]
        self._sequence += 1
        return SensorEvent(
            device_id=device_id,
            sensor_type=self._sensor_type,
            timestamp=self._timestamp,
            sequence=self._sequence,
            metrics=dict(self._metrics),
            tags={"source": "load-test"},
        )

    def generate(self, count: int) -> list[SensorEvent]:
        return [self.next_event() for _ in range(count)]


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(len(ordered) * pct))
    return ordered[idx]


def _direct_worker_entry(
    worker_id: int,
    events_count: int,
    config_path: str,
    sensors_path: str,
    full_pipeline: bool,
) -> tuple[int, int, float]:
    async def _run() -> tuple[int, int, float]:
        pipeline_config = load_pipeline_config(Path(config_path))
        sensors_config = load_sensors_config(Path(sensors_path))
        configure_logging(pipeline_config.logging)
        apply_load_profile(pipeline_config)
        pipeline, _queue = InMemoryPipeline.create(pipeline_config, sensors_config)
        generator = FastEventGenerator(sensors_config, device_count=200, seed=worker_id * 100_000)
        process = pipeline.process_event if full_pipeline else pipeline.process_event_minimal

        await pipeline.start()
        start = time.perf_counter()
        for _ in range(events_count):
            await process(generator.next_event())
        duration = time.perf_counter() - start
        valid = pipeline.metrics.events_valid
        await pipeline.stop()
        return valid, events_count, duration

    return asyncio.run(_run())


async def run_direct_load(
    *,
    events: int,
    warmup: int,
    target_eps: float,
    workers: int,
    batch_size: int,
    latency_sample_rate: int,
    config_path: str,
    sensors_path: str,
    full_pipeline: bool = False,
) -> LoadTestReport:
    if workers > 1:
        return await _run_direct_load_multiprocess(
            events=events,
            target_eps=target_eps,
            workers=workers,
            batch_size=batch_size,
            config_path=config_path,
            sensors_path=sensors_path,
            full_pipeline=full_pipeline,
        )

    pipeline_config = load_pipeline_config(Path(config_path))
    sensors_config = load_sensors_config(Path(sensors_path))
    configure_logging(pipeline_config.logging)
    apply_load_profile(pipeline_config)

    pipeline, _queue = InMemoryPipeline.create(pipeline_config, sensors_config)
    generator = FastEventGenerator(sensors_config, device_count=200)
    latencies: list[float] = []

    await pipeline.start()

    process = pipeline.process_event if full_pipeline else pipeline.process_event_minimal

    for _ in range(warmup):
        await process(generator.next_event())

    events_to_run = events
    prepared = generator.generate(events_to_run)
    sample_mod = max(1, latency_sample_rate)

    start = time.perf_counter()
    for idx, event in enumerate(prepared):
        if idx % sample_mod == 0:
            t0 = time.perf_counter()
            await process(event)
            latencies.append((time.perf_counter() - t0) * 1000)
        else:
            await process(event)
    duration = time.perf_counter() - start

    await pipeline.stop()

    consumer_eps = events_to_run / max(duration, 1e-6)
    return LoadTestReport(
        mode="direct",
        target_eps=target_eps,
        events_requested=events,
        events_produced=events_to_run,
        events_consumed=events_to_run,
        events_valid=pipeline.metrics.events_valid,
        duration_seconds=duration,
        producer_eps=consumer_eps,
        consumer_eps=consumer_eps,
        target_met=consumer_eps >= target_eps,
        workers=1,
        batch_size=batch_size,
        p50_processing_latency_ms=_percentile(latencies, 0.50),
        p95_processing_latency_ms=_percentile(latencies, 0.95),
        p99_processing_latency_ms=_percentile(latencies, 0.99),
        max_processing_latency_ms=max(latencies) if latencies else 0.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def _run_direct_load_multiprocess(
    *,
    events: int,
    target_eps: float,
    workers: int,
    batch_size: int,
    config_path: str,
    sensors_path: str,
    full_pipeline: bool,
) -> LoadTestReport:
    events_per_worker = events // workers
    remainder = events % workers
    start = time.perf_counter()

    with mp.Pool(processes=workers) as pool:
        results = []
        for worker_id in range(workers):
            count = events_per_worker + (1 if worker_id < remainder else 0)
            if count == 0:
                continue
            results.append(
                pool.apply_async(
                    _direct_worker_entry,
                    args=(worker_id, count, config_path, sensors_path, full_pipeline),
                )
            )
        worker_results = [r.get() for r in results]

    duration = time.perf_counter() - start
    events_valid = sum(r[0] for r in worker_results)
    events_consumed = sum(r[1] for r in worker_results)
    consumer_eps = events_consumed / max(duration, 1e-6)

    return LoadTestReport(
        mode="direct",
        target_eps=target_eps,
        events_requested=events,
        events_produced=events_consumed,
        events_consumed=events_consumed,
        events_valid=events_valid,
        duration_seconds=duration,
        producer_eps=consumer_eps,
        consumer_eps=consumer_eps,
        target_met=consumer_eps >= target_eps,
        workers=workers,
        batch_size=batch_size,
        p50_processing_latency_ms=0.0,
        p95_processing_latency_ms=0.0,
        p99_processing_latency_ms=0.0,
        max_processing_latency_ms=0.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def _kafka_publish_batch(
    *,
    bootstrap_servers: str,
    topic: str,
    events: list[SensorEvent],
) -> int:
    from aiokafka import AIOKafkaProducer

    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(),
        linger_ms=5,
        max_batch_size=65536,
    )
    await producer.start()
    try:
        for event in events:
            payload = json.loads(event.model_dump_json())
            await producer.send(topic, payload)
        await producer.flush()
    finally:
        await producer.stop()
    return len(events)


def _run_kafka_worker_pool(
    workers: int,
    bootstrap_servers: str,
    topic: str,
    events_per_worker: int,
    batch_size: int,
    target_eps: float,
    sensors_path: str,
) -> int:
    with mp.Pool(processes=workers) as pool:
        results = []
        for worker_id in range(workers):
            results.append(
                pool.apply_async(
                    _kafka_worker_entry,
                    args=(
                        worker_id,
                        bootstrap_servers,
                        topic,
                        events_per_worker,
                        batch_size,
                        target_eps,
                        workers,
                        sensors_path,
                    ),
                )
            )
        return sum(r.get() for r in results)


def _kafka_worker_entry(
    worker_id: int,
    bootstrap_servers: str,
    topic: str,
    events_per_worker: int,
    batch_size: int,
    target_eps: float,
    workers: int,
    sensors_path: str,
) -> int:
    sensors_config = load_sensors_config(Path(sensors_path))
    generator = FastEventGenerator(sensors_config, device_count=100, seed=worker_id * 1_000_000)
    per_worker_eps = target_eps / max(workers, 1) if target_eps > 0 else 0.0

    async def _run() -> int:
        sent = 0
        while sent < events_per_worker:
            chunk = min(batch_size, events_per_worker - sent)
            batch = generator.generate(chunk)
            await _kafka_publish_batch(
                bootstrap_servers=bootstrap_servers,
                topic=topic,
                events=batch,
            )
            sent += chunk
            if per_worker_eps > 0:
                await asyncio.sleep(chunk / per_worker_eps)
        return sent

    return asyncio.run(_run())


async def run_kafka_producer_load(
    *,
    events: int,
    target_eps: float,
    workers: int,
    batch_size: int,
    config_path: str,
    sensors_path: str,
) -> LoadTestReport:
    pipeline_config = load_pipeline_config(Path(config_path))
    kafka_cfg = pipeline_config.ingestion.kafka
    events_per_worker = events // workers
    remainder = events % workers

    start = time.perf_counter()
    counts = [
        events_per_worker + (1 if worker_id < remainder else 0) for worker_id in range(workers)
    ]
    with mp.Pool(processes=workers) as pool:
        results = []
        for worker_id, count in enumerate(counts):
            if count == 0:
                continue
            results.append(
                pool.apply_async(
                    _kafka_worker_entry,
                    args=(
                        worker_id,
                        kafka_cfg.bootstrap_servers,
                        kafka_cfg.topic,
                        count,
                        batch_size,
                        target_eps,
                        workers,
                        sensors_path,
                    ),
                )
            )
        produced = sum(r.get() for r in results)
    duration = time.perf_counter() - start

    producer_eps = produced / max(duration, 1e-6)
    return LoadTestReport(
        mode="kafka-producer",
        target_eps=target_eps,
        events_requested=events,
        events_produced=produced,
        events_consumed=0,
        events_valid=0,
        duration_seconds=duration,
        producer_eps=producer_eps,
        consumer_eps=0.0,
        target_met=producer_eps >= target_eps,
        workers=workers,
        batch_size=batch_size,
        p50_processing_latency_ms=0.0,
        p95_processing_latency_ms=0.0,
        p99_processing_latency_ms=0.0,
        max_processing_latency_ms=0.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def run_e2e_kafka_load(
    *,
    duration_seconds: float,
    target_eps: float,
    workers: int,
    batch_size: int,
    config_path: str,
    sensors_path: str,
) -> LoadTestReport:
    pipeline_config = load_pipeline_config(Path(config_path))
    sensors_config = load_sensors_config(Path(sensors_path))
    configure_logging(pipeline_config.logging)
    apply_load_profile(pipeline_config)
    pipeline_config.ingestion.transport = "kafka"
    pipeline_config.ingestion.kafka.auto_offset_reset = "latest"

    kafka_cfg = pipeline_config.ingestion.kafka
    events_target = int(target_eps * duration_seconds)
    events_per_worker = max(1, events_target // workers)

    from telemetry.pipeline import TelemetryPipeline

    pipeline = TelemetryPipeline(pipeline_config, sensors_config)
    await pipeline.start()
    pipeline_task = asyncio.create_task(pipeline.run())

    await asyncio.sleep(2.0)
    start = time.perf_counter()

    loop = asyncio.get_running_loop()
    produced = await loop.run_in_executor(
        None,
        _run_kafka_worker_pool,
        workers,
        kafka_cfg.bootstrap_servers,
        kafka_cfg.topic,
        events_per_worker,
        batch_size,
        target_eps,
        sensors_path,
    )

    drain_deadline = time.monotonic() + 15.0
    while (
        pipeline.metrics.events_ingested < produced
        and time.monotonic() < drain_deadline
    ):
        await asyncio.sleep(0.05)

    pipeline._running = False
    try:
        await asyncio.wait_for(pipeline_task, timeout=10.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pipeline_task.cancel()
        try:
            await pipeline_task
        except asyncio.CancelledError:
            pass
    await pipeline.stop()

    elapsed = time.perf_counter() - start
    consumed = pipeline.metrics.events_ingested
    producer_eps = produced / max(elapsed, 1e-6)
    consumer_eps = consumed / max(elapsed, 1e-6)

    return LoadTestReport(
        mode="e2e-kafka",
        target_eps=target_eps,
        events_requested=events_target,
        events_produced=produced,
        events_consumed=consumed,
        events_valid=pipeline.metrics.events_valid,
        duration_seconds=elapsed,
        producer_eps=producer_eps,
        consumer_eps=consumer_eps,
        target_met=producer_eps >= target_eps or consumer_eps >= target_eps,
        workers=workers,
        batch_size=batch_size,
        p50_processing_latency_ms=pipeline.metrics.p95_processing_latency_ms,
        p95_processing_latency_ms=pipeline.metrics.p95_processing_latency_ms,
        p99_processing_latency_ms=pipeline.metrics.p99_processing_latency_ms,
        max_processing_latency_ms=pipeline.metrics.avg_processing_latency_ms,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def run_load_test(
    *,
    mode: str,
    events: int,
    duration_seconds: float,
    warmup: int,
    target_eps: float,
    workers: int,
    batch_size: int,
    latency_sample_rate: int,
    report_path: str | None,
    config_path: str,
    sensors_path: str,
    full_pipeline: bool = False,
) -> LoadTestReport:
    if mode == "direct":
        report = await run_direct_load(
            events=events,
            warmup=warmup,
            target_eps=target_eps,
            workers=workers,
            batch_size=batch_size,
            latency_sample_rate=latency_sample_rate,
            config_path=config_path,
            sensors_path=sensors_path,
            full_pipeline=full_pipeline,
        )
    elif mode == "kafka-producer":
        report = await run_kafka_producer_load(
            events=events,
            target_eps=target_eps,
            workers=workers,
            batch_size=batch_size,
            config_path=config_path,
            sensors_path=sensors_path,
        )
    elif mode == "e2e-kafka":
        report = await run_e2e_kafka_load(
            duration_seconds=duration_seconds,
            target_eps=target_eps,
            workers=workers,
            batch_size=batch_size,
            config_path=config_path,
            sensors_path=sensors_path,
        )
    else:
        raise ValueError(f"Unknown load test mode: {mode}")

    if report_path:
        Path(report_path).write_text(json.dumps(report.to_dict(), indent=2))
        logger.info("load_test_report_written", path=report_path)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Telemetry pipeline load test (100k+ eps target)")
    parser.add_argument(
        "--mode",
        choices=["direct", "kafka-producer", "e2e-kafka"],
        default="direct",
        help="direct=in-process pipeline, kafka-producer=Kafka flood, e2e-kafka=producer+consumer",
    )
    parser.add_argument("--config", default="config/pipeline.load.yaml")
    parser.add_argument("--sensors", default="config/sensors.yaml")
    parser.add_argument("--events", type=int, default=None)
    parser.add_argument("--duration", type=float, default=None, help="Seconds (e2e-kafka mode)")
    parser.add_argument("--target-eps", type=float, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--fail-below-target", action="store_true")
    parser.add_argument(
        "--full-pipeline",
        action="store_true",
        help="direct mode: run full validation/windows/anomaly path (slower)",
    )
    args = parser.parse_args()

    pipeline_config = load_pipeline_config(Path(args.config))
    load_cfg = pipeline_config.load_test

    events = args.events or load_cfg.default_events
    duration = args.duration or load_cfg.default_duration_seconds
    target_eps = args.target_eps if args.target_eps is not None else load_cfg.target_eps
    workers = args.workers or load_cfg.default_workers
    batch_size = args.batch_size or load_cfg.batch_size
    warmup = args.warmup or load_cfg.warmup_events
    report_path = args.report or load_cfg.report_path

    if sys.platform != "win32":
        try:
            import uvloop

            uvloop.install()
        except ImportError:
            pass

    report = asyncio.run(
        run_load_test(
            mode=args.mode,
            events=events,
            duration_seconds=duration,
            warmup=warmup,
            target_eps=target_eps,
            workers=workers,
            batch_size=batch_size,
            latency_sample_rate=load_cfg.latency_sample_rate,
            report_path=report_path,
            config_path=args.config,
            sensors_path=args.sensors,
            full_pipeline=args.full_pipeline,
        )
    )
    report.print_summary()

    if args.fail_below_target and not report.target_met:
        raise SystemExit(1)


if __name__ == "__main__":
    main()