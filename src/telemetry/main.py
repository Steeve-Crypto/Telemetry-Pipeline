"""Pipeline entry point."""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys

import structlog

from telemetry.config import load_pipeline_config, load_sensors_config
from telemetry.pipeline import TelemetryPipeline

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger(__name__)


async def run_pipeline(config_path: str, sensors_path: str) -> None:
    pipeline_config = load_pipeline_config(config_path)
    sensors_config = load_sensors_config(sensors_path)
    pipeline = TelemetryPipeline(pipeline_config, sensors_config)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("shutdown_signal_received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    await pipeline.start()

    async def _consume() -> None:
        async for event in pipeline._ingestion.events():
            if stop_event.is_set():
                break
            await pipeline.process_event(event)

    consumer = asyncio.create_task(_consume())
    await stop_event.wait()
    await pipeline.stop()
    consumer.cancel()
    try:
        await consumer
    except asyncio.CancelledError:
        pass

    m = pipeline.metrics
    logger.info(
        "pipeline_summary",
        ingested=m.events_ingested,
        valid=m.events_valid,
        invalid=m.events_invalid,
        deduped=m.events_deduped,
        anomalies=m.anomalies_detected,
        avg_latency_ms=round(m.avg_ingest_latency_ms, 2),
        p95_latency_ms=round(m.p95_ingest_latency_ms, 2),
        eps=round(m.processing_rate_eps, 1),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Telemetry processing pipeline")
    parser.add_argument("--config", default="config/pipeline.yaml")
    parser.add_argument("--sensors", default="config/sensors.yaml")
    args = parser.parse_args()

    try:
        import uvloop

        uvloop.install()
    except ImportError:
        pass

    try:
        asyncio.run(run_pipeline(args.config, args.sensors))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()