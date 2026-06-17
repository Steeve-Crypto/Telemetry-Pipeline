import type { ChartPoint, SparklineHistory, TelemetryEvent } from "./types";

const SPARKLINE_LEN = 24;

export function appendSparkline(
  history: SparklineHistory,
  metrics: {
    events_ingested: number;
    events_valid: number;
    anomalies_detected: number;
    processing_rate_eps: number;
  },
): SparklineHistory {
  const push = (arr: number[], value: number) => {
    const next = [...arr, value];
    return next.length > SPARKLINE_LEN ? next.slice(-SPARKLINE_LEN) : next;
  };

  return {
    ingested: push(history.ingested, metrics.events_ingested),
    valid: push(history.valid, metrics.events_valid),
    anomalies: push(history.anomalies, metrics.anomalies_detected),
    throughput: push(history.throughput, metrics.processing_rate_eps),
  };
}

export const EMPTY_SPARKLINE: SparklineHistory = {
  ingested: [],
  valid: [],
  anomalies: [],
  throughput: [],
};

export function eventsToChartPoints(events: TelemetryEvent[]): ChartPoint[] {
  return [...events]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map((event) => {
      const d = new Date(event.timestamp);
      return {
        time: d.toISOString(),
        label: d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        temperature: event.metrics.temperature,
        pressure: event.metrics.pressure,
        vibration: event.metrics.vibration,
      };
    });
}