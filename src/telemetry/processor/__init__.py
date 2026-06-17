"""Stream processing."""

from telemetry.processor.aggregator import WindowAggregator
from telemetry.processor.windows import TumblingWindow

__all__ = ["TumblingWindow", "WindowAggregator"]