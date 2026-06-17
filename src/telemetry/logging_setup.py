"""Structured logging configuration with JSON output for Loki."""

from __future__ import annotations

import logging
import sys

import structlog

from telemetry.config import LoggingConfig


def configure_logging(config: LoggingConfig) -> None:
    level = getattr(logging, config.level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if config.format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.processors.UnicodeDecoder(), renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=level, stream=sys.stdout, format="%(message)s")