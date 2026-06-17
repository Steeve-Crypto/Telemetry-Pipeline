import type { AnomalyScore, PipelineMetrics, TelemetryEvent } from "./types";

const DEFAULT_METRICS: PipelineMetrics = {
  events_ingested: 0,
  events_valid: 0,
  events_invalid: 0,
  events_deduped: 0,
  anomalies_detected: 0,
  avg_ingest_latency_ms: 0,
  p95_ingest_latency_ms: 0,
  avg_processing_latency_ms: 0,
  p95_processing_latency_ms: 0,
  p99_processing_latency_ms: 0,
  processing_rate_eps: 0,
  latency_histogram: {},
};

export function getTelemetryApiUrl(): string {
  return process.env.TELEMETRY_API_URL ?? "http://localhost:8081";
}

export async function fetchPipelineMetrics(
  apiKey?: string,
): Promise<{ metrics: PipelineMetrics; ok: boolean }> {
  try {
    const headers: HeadersInit = {};
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const res = await fetch("/api/metrics", {
      headers,
      cache: "no-store",
    });

    if (!res.ok) {
      return { metrics: DEFAULT_METRICS, ok: false };
    }

    const metrics = (await res.json()) as PipelineMetrics;
    return { metrics, ok: true };
  } catch {
    return { metrics: DEFAULT_METRICS, ok: false };
  }
}

async function fetchJson<T>(path: string, apiKey?: string): Promise<{ data: T; ok: boolean }> {
  try {
    const headers: HeadersInit = {};
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const res = await fetch(path, { headers, cache: "no-store" });
    if (!res.ok) {
      return { data: [] as T, ok: false };
    }

    return { data: (await res.json()) as T, ok: true };
  } catch {
    return { data: [] as T, ok: false };
  }
}

export async function fetchRecentEvents(limit = 200, apiKey?: string) {
  return fetchJson<TelemetryEvent[]>(`/api/events?limit=${limit}`, apiKey);
}

export async function fetchRecentAnomalies(limit = 50, apiKey?: string) {
  return fetchJson<AnomalyScore[]>(`/api/anomalies?limit=${limit}`, apiKey);
}

export interface DashboardSnapshot {
  metrics: PipelineMetrics;
  events: TelemetryEvent[];
  anomalies: AnomalyScore[];
  ok: boolean;
}

export async function fetchDashboardSnapshot(apiKey?: string): Promise<DashboardSnapshot> {
  const [metricsRes, eventsRes, anomaliesRes] = await Promise.all([
    fetchPipelineMetrics(apiKey),
    fetchRecentEvents(200, apiKey),
    fetchRecentAnomalies(50, apiKey),
  ]);

  const ok = metricsRes.ok || eventsRes.ok || anomaliesRes.ok;

  return {
    metrics: metricsRes.metrics,
    events: eventsRes.data,
    anomalies: anomaliesRes.data,
    ok,
  };
}