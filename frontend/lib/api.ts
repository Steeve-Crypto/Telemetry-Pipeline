import type { PipelineMetrics } from "./types";

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