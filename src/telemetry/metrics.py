"""Pipeline latency and throughput metrics."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class LatencyTracker:
    max_samples: int = 10_000
    _samples: deque[float] = field(default_factory=lambda: deque(maxlen=10_000))
    _start_times: dict[str, float] = field(default_factory=dict)

    def start(self, event_id: str) -> None:
        self._start_times[event_id] = time.perf_counter()

    def end(self, event_id: str) -> float | None:
        start = self._start_times.pop(event_id, None)
        if start is None:
            return None
        latency_ms = (time.perf_counter() - start) * 1000
        self._samples.append(latency_ms)
        return latency_ms

    def record(self, latency_ms: float) -> None:
        self._samples.append(latency_ms)

    @property
    def count(self) -> int:
        return len(self._samples)

    def percentile(self, p: float) -> float:
        if not self._samples:
            return 0.0
        sorted_samples = sorted(self._samples)
        idx = int(len(sorted_samples) * p / 100)
        idx = min(idx, len(sorted_samples) - 1)
        return sorted_samples[idx]

    @property
    def mean(self) -> float:
        if not self._samples:
            return 0.0
        return sum(self._samples) / len(self._samples)

    def histogram(self, buckets: list[int]) -> dict[str, int]:
        counts = {f"<={b}": 0 for b in buckets}
        counts[">max"] = 0
        if not self._samples:
            return counts
        max_bucket = max(buckets)
        for sample in self._samples:
            placed = False
            for b in buckets:
                if sample <= b:
                    counts[f"<={b}"] += 1
                    placed = True
                    break
            if not placed:
                counts[">max"] += 1
        return counts


@dataclass
class ThroughputTracker:
    window_seconds: float = 5.0
    _timestamps: deque[float] = field(default_factory=deque)

    def record(self) -> None:
        now = time.monotonic()
        self._timestamps.append(now)
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    @property
    def events_per_second(self) -> float:
        if len(self._timestamps) < 2:
            return float(len(self._timestamps)) / max(self.window_seconds, 1e-6)
        span = self._timestamps[-1] - self._timestamps[0]
        if span <= 0:
            return float(len(self._timestamps))
        return len(self._timestamps) / span