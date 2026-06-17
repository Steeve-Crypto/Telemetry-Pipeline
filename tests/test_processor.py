"""Windowed aggregation tests."""

from datetime import datetime, timedelta, timezone

from telemetry.models import EnrichedEvent
from telemetry.processor.aggregator import WindowAggregator
from telemetry.processor.windows import TumblingWindow


def _event(device: str, offset_sec: int, temp: float) -> EnrichedEvent:
    return EnrichedEvent(
        device_id=device,
        sensor_type="industrial",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=offset_sec),
        metrics={"temperature": temp, "pressure": 4.5, "vibration": 3.0},
    )


def test_tumbling_window_emits_batches():
    window = TumblingWindow(window_size_seconds=10, slide_interval_seconds=10)
    agg = WindowAggregator()
    all_stats = []
    for i in range(15):
        for key, events in window.add(_event("d1", i, 60 + i)):
            all_stats.extend(agg.aggregate(key, events))
    assert len(all_stats) >= 1
    temp_stats = [s for s in all_stats if s.field == "temperature"]
    assert temp_stats[0].count >= 1
    assert temp_stats[0].mean > 0


def test_aggregator_computes_stats():
    agg = WindowAggregator()
    events = [_event("d1", i, float(60 + i)) for i in range(5)]
    stats = agg.aggregate("d1:industrial", events)
    temp = next(s for s in stats if s.field == "temperature")
    assert temp.count == 5
    assert temp.min == 60.0
    assert temp.max == 64.0