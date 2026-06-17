"""CLI to provision Kafka topics (including per-tenant partitions)."""

from __future__ import annotations

import argparse
import asyncio

import structlog

from telemetry.config import load_pipeline_config
from telemetry.ingestion.kafka_admin import ensure_kafka_topics
from telemetry.ingestion.kafka_topics import consumer_topics
from telemetry.logging_setup import configure_logging

logger = structlog.get_logger(__name__)


async def run(config_path: str) -> list[str]:
    pipeline_config = load_pipeline_config(config_path)
    configure_logging(pipeline_config.logging)
    kafka = pipeline_config.ingestion.kafka
    tenancy = pipeline_config.tenancy
    topics = await ensure_kafka_topics(kafka, tenancy)
    return topics


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Kafka topics for telemetry pipeline")
    parser.add_argument("--config", default="config/pipeline.yaml")
    args = parser.parse_args()

    topics = asyncio.run(run(args.config))
    print("\n=== Kafka Topics ===")
    for topic in topics:
        print(f"  {topic}")
    print("====================\n")
    logger.info("kafka_init_complete", topics=topics)


if __name__ == "__main__":
    main()