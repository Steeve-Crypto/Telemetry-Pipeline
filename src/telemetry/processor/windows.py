"""Tumbling and sliding window utilities."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from telemetry.models import EnrichedEvent


@dataclass
class WindowBuffer:
    events: deque[EnrichedEvent] = field(default_factory=deque)
    window_start: datetime | None = None
    window_end: datetime | None = None


class TumblingWindow:
    """Tumbling window keyed by device_id + sensor_type."""

    def __init__(self, window_size_seconds: int, slide_interval_seconds: int | None = None) -> None:
        self.window_size = timedelta(seconds=window_size_seconds)
        self.slide_interval = (
            timedelta(seconds=slide_interval_seconds)
            if slide_interval_seconds
            else self.window_size
        )
        self._buffers: dict[str, WindowBuffer] = defaultdict(WindowBuffer)
        self._last_emit: dict[str, datetime] = {}

    def add(self, event: EnrichedEvent) -> list[tuple[str, list[EnrichedEvent]]]:
        key = f"{event.device_id}:{event.sensor_type}"
        buf = self._buffers[key]
        buf.events.append(event)

        if buf.window_start is None:
            buf.window_start = event.timestamp
            buf.window_end = event.timestamp + self.window_size

        completed: list[tuple[str, list[EnrichedEvent]]] = []
        while event.timestamp >= buf.window_end:
            window_events = [e for e in buf.events if buf.window_start <= e.timestamp < buf.window_end]
            if window_events:
                completed.append((key, window_events))
            buf.window_start = buf.window_end
            buf.window_end = buf.window_start + self.window_size
            buf.events = deque(e for e in buf.events if e.timestamp >= buf.window_start)

        last = self._last_emit.get(key)
        if last is None or (event.timestamp - last) >= self.slide_interval:
            if buf.events:
                self._last_emit[key] = event.timestamp
                completed.append((key, list(buf.events)))

        return completed