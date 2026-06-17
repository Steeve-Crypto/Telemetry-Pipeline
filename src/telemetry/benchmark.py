"""Formal latency/throughput benchmark harness with Prometheus export."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import structlog

from telemetry.config import load_pipeline_config, load_sensors_config
from telemetry.pipeline import InMemoryPipeline
from telemetry.prometheus import PrometheusExporter
from telemetry.simulator.generator import SensorSimulator

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkReport:
    events_total: int
    events_valid: int
    events_invalid: int
    anomalies_detected: int
    duration_seconds: float
    throughput_eps: float
    avg_processing_latency_ms: float
    p50_processing_latency_ms: float
    p95_processing_latency_ms: float
    p99_processing_latency_ms: float
    max_processing_latency_ms: float
    latency_histogram: dict[str, int]
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)

    def print_summary(self) -> None:
        print("\n=== Telemetry Pipeline Benchmark ===")
        print(f"  Events:       {self.events_total:,}")
        print(f"  Valid:        {self.events_valid:,}")
        print(f"  Anomalies:    {self.anomalies_detected:,}")
        print(f"  Duration:     {self.duration_seconds:.2f}s")
        print(f"  Throughput:   {self.throughput_eps:,.0f} eps")
        print(f"  Avg latency:  {self.avg_processing_latency_ms:.2f} ms")
        print(f"  P50 latency:  {self.p50_processing_latency_ms:.2f} ms")
        print(f"  P95 latency:  {self.p95_processing_latency_ms:.2f} ms")
        print(f"  P99 latency:  {self.p99_processing_latency_ms:.2f} ms")
        print(f"  Max latency:  {self.max_processing_latency_ms:.2f} ms")
        print("====================================\n")


async def run_benchmark(
    events: int,
    warmup: int,
    anomaly_rate: float,
    report_path: str | None = None,
    config_path: str = "config/pipeline.yaml",
    sensors_path: str = "config/sensors.yaml",
) -> BenchmarkReport:
    pipeline_config = load_pipeline_config(Path(config_path))
    sensors_config = load_sensors_config(Path(sensors_path))
    pipeline_config.storage.backend = "memory"
    pipeline_config.viz.enabled = False
    pipeline_config.prometheus.enabled = True
    pipeline_config.simulator.anomaly_rate = anomaly_rate

    pipeline, queue = InMemoryPipeline.create(pipeline_config, sensors_config)
    sim = SensorSimulator(pipeline_config, sensors_config, seed=42)
    prometheus = PrometheusExporter(pipeline_config.prometheus)

    latencies: list[float] = []
    await pipeline.start()

    # Warmup
    for i in range(warmup):
        device = f"industrial-device-{i % 5:03d}"
        event = sim.generate_event(device, inject_anomaly=False)
        t0 = time.perf_counter()
        await pipeline.process_event(event)
        latencies.append((time.perf_counter() - t0) * 1000)

    latencies.clear()
    pipeline._metrics = type(pipeline._metrics)()
    start = time.perf_counter()

    for i in range(events):
        device = f"industrial-device-{i % 10:03d}"
        inject = i % int(1 / max(anomaly_rate, 0.001)) == 0 if anomaly_rate > 0 else False
        event = sim.generate_event(device, inject_anomaly=inject)
        t0 = time.perf_counter()
        await pipeline.process_event(event)
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)
        prometheus.update(pipeline.metrics, processing_latency_ms=latency_ms)

    duration = time.perf_counter() - start
    await pipeline.stop()

    sorted_lat = sorted(latencies)
    p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)]

    histogram = pipeline._processing_latency.histogram(
        pipeline_config.metrics.latency_histogram_buckets_ms
    )

    report = BenchmarkReport(
        events_total=events,
        events_valid=pipeline.metrics.events_valid,
        events_invalid=pipeline.metrics.events_invalid,
        anomalies_detected=pipeline.metrics.anomalies_detected,
        duration_seconds=duration,
        throughput_eps=events / max(duration, 1e-6),
        avg_processing_latency_ms=sum(latencies) / len(latencies),
        p50_processing_latency_ms=p50,
        p95_processing_latency_ms=p95,
        p99_processing_latency_ms=p99,
        max_processing_latency_ms=max(latencies),
        latency_histogram=histogram,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    if report_path:
        Path(report_path).write_text(json.dumps(report.to_dict(), indent=2))
        logger.info("benchmark_report_written", path=report_path)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Telemetry pipeline benchmark harness")
    parser.add_argument("--config", default="config/pipeline.yaml")
    parser.add_argument("--sensors", default="config/sensors.yaml")
    parser.add_argument("--events", type=int, default=10_000)
    parser.add_argument("--warmup", type=int, default=500)
    parser.add_argument("--anomaly-rate", type=float, default=0.02)
    parser.add_argument("--report", default="benchmark_report.json")
    args = parser.parse_args()

    report = asyncio.run(
        run_benchmark(
            events=args.events,
            warmup=args.warmup,
            anomaly_rate=args.anomaly_rate,
            report_path=args.report,
            config_path=args.config,
            sensors_path=args.sensors,
        )
    )
    report.print_summary()


if __name__ == "__main__":
    main()