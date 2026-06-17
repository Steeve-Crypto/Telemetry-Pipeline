"""High-frequency synthetic sensor data generator with anomaly injection."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog
import websockets

from telemetry.config import PipelineYamlConfig, SensorsYamlConfig, load_pipeline_config, load_sensors_config
from telemetry.ingestion.kafka_producer import KafkaEventProducer
from telemetry.ingestion.kafka_topics import is_topic_per_tenant, known_tenant_ids
from telemetry.models import SensorEvent

logger = structlog.get_logger(__name__)

HEARTBEAT_PATH = Path("/tmp/simulator.heartbeat")


class SensorSimulator:
    def __init__(
        self,
        pipeline_config: PipelineYamlConfig,
        sensors_config: SensorsYamlConfig,
        seed: int = 42,
    ) -> None:
        self._pipeline = pipeline_config
        self._sensors = sensors_config
        self._rng = random.Random(seed)
        self._sequence: dict[str, int] = {}
        self._drift_offsets: dict[str, float] = {}

    @staticmethod
    def _touch_heartbeat() -> None:
        HEARTBEAT_PATH.touch()

    def _device_ids(self) -> list[str]:
        n = self._pipeline.simulator.devices
        types = list(self._sensors.sensor_types.keys())
        return [f"{types[i % len(types)]}-device-{i:03d}" for i in range(n)]

    def _tenant_ids(self) -> list[str]:
        return known_tenant_ids(self._pipeline.tenancy)

    def _tenant_for_device(self, device_id: str) -> str | None:
        kafka_cfg = self._pipeline.ingestion.kafka
        if not is_topic_per_tenant(kafka_cfg, self._pipeline.tenancy):
            return None
        tenants = self._tenant_ids()
        if not tenants:
            return self._pipeline.tenancy.default_tenant
        idx = sum(ord(c) for c in device_id) % len(tenants)
        return tenants[idx]

    def generate_event(self, device_id: str, inject_anomaly: bool | None = None) -> SensorEvent:
        sensor_type = device_id.split("-device-")[0]
        sensor_def = self._sensors.sensor_types[sensor_type]
        seq = self._sequence.get(device_id, 0)
        self._sequence[device_id] = seq + 1

        metrics: dict[str, float] = {}
        for field_name, field_def in sensor_def.fields.items():
            value = self._rng.gauss(field_def.baseline, field_def.noise_std)
            value = max(field_def.min, min(field_def.max, value))
            metrics[field_name] = round(value, 4)

        is_anomaly = False
        anomaly_label = None
        rate = self._pipeline.simulator.anomaly_rate
        if inject_anomaly is None:
            inject_anomaly = self._rng.random() < rate

        if inject_anomaly and sensor_def.anomaly_patterns:
            pattern = self._rng.choice(sensor_def.anomaly_patterns)
            anomaly_label = f"{pattern.type}:{pattern.field}"
            is_anomaly = True
            field = pattern.field
            if pattern.type == "spike" and field in metrics and pattern.multiplier:
                metrics[field] = min(
                    sensor_def.fields[field].max,
                    metrics[field] * pattern.multiplier,
                )
            elif pattern.type == "drift" and field in metrics and pattern.slope:
                key = f"{device_id}:{field}"
                self._drift_offsets[key] = self._drift_offsets.get(key, 0.0) + pattern.slope
                metrics[field] = min(
                    sensor_def.fields[field].max,
                    metrics[field] + self._drift_offsets[key],
                )
            elif pattern.type == "flatline" and field in metrics:
                metrics[field] = sensor_def.fields[field].baseline

        tags = {"source": "simulator"}
        tenant_id = self._tenant_for_device(device_id)
        if tenant_id:
            tags["tenant_id"] = tenant_id

        return SensorEvent(
            device_id=device_id,
            sensor_type=sensor_type,
            timestamp=datetime.now(timezone.utc),
            sequence=seq,
            metrics=metrics,
            tags=tags,
            tenant_id=tenant_id,
            is_anomaly=is_anomaly if inject_anomaly else None,
            anomaly_label=anomaly_label,
        )

    async def run_websocket(self, duration_seconds: float | None = None) -> int:
        ws_cfg = self._pipeline.ingestion.websocket
        uri = f"ws://{ws_cfg.host if ws_cfg.host != '0.0.0.0' else 'localhost'}:{ws_cfg.port}"
        devices = self._device_ids()
        interval = self._pipeline.simulator.interval_ms / 1000.0
        sent = 0
        start = time.monotonic()

        async with websockets.connect(uri) as ws:
            logger.info("simulator_connected", uri=uri, devices=len(devices))
            while duration_seconds is None or (time.monotonic() - start) < duration_seconds:
                device_id = self._rng.choice(devices)
                event = self.generate_event(device_id)
                await ws.send(event.model_dump_json())
                sent += 1
                self._touch_heartbeat()
                if self._pipeline.simulator.burst_mode and sent % 50 == 0:
                    for _ in range(10):
                        burst_event = self.generate_event(self._rng.choice(devices))
                        await ws.send(burst_event.model_dump_json())
                        sent += 1
                await asyncio.sleep(interval)
        return sent

    async def run_kafka(self, duration_seconds: float | None = None) -> int:
        kafka_cfg = self._pipeline.ingestion.kafka
        producer = KafkaEventProducer(kafka_cfg, self._pipeline.tenancy)
        await producer.connect()
        devices = self._device_ids()
        interval = self._pipeline.simulator.interval_ms / 1000.0
        sent = 0
        start = time.monotonic()

        try:
            logger.info(
                "simulator_kafka_connected",
                servers=kafka_cfg.bootstrap_servers,
                topic_per_tenant=kafka_cfg.topic_per_tenant,
            )
            while duration_seconds is None or (time.monotonic() - start) < duration_seconds:
                device_id = self._rng.choice(devices)
                event = self.generate_event(device_id)
                await producer.publish(event)
                sent += 1
                self._touch_heartbeat()
                if self._pipeline.simulator.burst_mode and sent % 50 == 0:
                    for _ in range(10):
                        burst_event = self.generate_event(self._rng.choice(devices))
                        await producer.publish(burst_event)
                        sent += 1
                await asyncio.sleep(interval)
        finally:
            await producer.disconnect()
        return sent

    async def run(self, duration_seconds: float | None = None) -> int:
        transport = self._pipeline.ingestion.transport
        if transport == "kafka":
            return await self.run_kafka(duration_seconds)
        return await self.run_websocket(duration_seconds)

    async def run_to_queue(self, queue: asyncio.Queue, count: int) -> None:
        devices = self._device_ids()
        for i in range(count):
            device_id = devices[i % len(devices)]
            inject = i % 50 == 0  # deterministic anomalies for tests
            await queue.put(self.generate_event(device_id, inject_anomaly=inject))


async def async_main(args: argparse.Namespace) -> None:
    pipeline = load_pipeline_config(args.config)
    sensors = load_sensors_config(args.sensors)
    if args.devices:
        pipeline.simulator.devices = args.devices
    if args.interval_ms:
        pipeline.simulator.interval_ms = args.interval_ms
    if args.anomaly_rate is not None:
        pipeline.simulator.anomaly_rate = args.anomaly_rate

    sim = SensorSimulator(pipeline, sensors, seed=args.seed)
    sent = await sim.run(duration_seconds=args.duration)
    logger.info("simulator_finished", events_sent=sent, transport=pipeline.ingestion.transport)


def main() -> None:
    parser = argparse.ArgumentParser(description="Telemetry sensor simulator")
    parser.add_argument("--config", default="config/pipeline.yaml")
    parser.add_argument("--sensors", default="config/sensors.yaml")
    parser.add_argument("--duration", type=float, default=None, help="Run duration in seconds")
    parser.add_argument("--devices", type=int, default=None)
    parser.add_argument("--interval-ms", type=int, default=None)
    parser.add_argument("--anomaly-rate", type=float, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()