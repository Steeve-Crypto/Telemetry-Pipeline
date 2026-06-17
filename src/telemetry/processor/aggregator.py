"""Windowed statistical aggregation."""

from __future__ import annotations

import statistics
from datetime import datetime

from telemetry.models import EnrichedEvent, WindowStats


class WindowAggregator:
    def aggregate(
        self,
        key: str,
        events: list[EnrichedEvent],
    ) -> list[WindowStats]:
        if not events:
            return []

        device_id, sensor_type = key.split(":", 1)
        tenant_id = events[0].tenant_id
        window_start = min(e.timestamp for e in events)
        window_end = max(e.timestamp for e in events)

        field_values: dict[str, list[float]] = {}
        for event in events:
            for field_name, value in event.metrics.items():
                field_values.setdefault(field_name, []).append(value)

        stats: list[WindowStats] = []
        for field_name, values in field_values.items():
            stats.append(
                WindowStats(
                    tenant_id=tenant_id,
                    device_id=device_id,
                    sensor_type=sensor_type,
                    window_start=window_start,
                    window_end=window_end,
                    field=field_name,
                    count=len(values),
                    mean=statistics.fmean(values),
                    min=min(values),
                    max=max(values),
                    std=statistics.pstdev(values) if len(values) > 1 else 0.0,
                )
            )
        return stats

    @staticmethod
    def latest_timestamp(events: list[EnrichedEvent]) -> datetime:
        return max(e.timestamp for e in events)