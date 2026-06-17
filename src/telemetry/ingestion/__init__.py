"""Ingestion transports for telemetry events."""

from telemetry.ingestion.base import IngestionSource, create_ingestion_source

__all__ = ["IngestionSource", "create_ingestion_source"]