import { clientFetch } from "./client-fetch";
import type {
  AnomalyScore,
  AppConfig,
  DeviceSummary,
  PipelineMetrics,
  TelemetryEvent,
  WindowStat,
} from "./types";

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
  tenantId?: string | null,
): Promise<{ metrics: PipelineMetrics; ok: boolean }> {
  try {
    const res = await clientFetch("/api/metrics", tenantId);

    if (!res.ok) {
      return { metrics: DEFAULT_METRICS, ok: false };
    }

    const metrics = (await res.json()) as PipelineMetrics;
    return { metrics, ok: true };
  } catch {
    return { metrics: DEFAULT_METRICS, ok: false };
  }
}

async function fetchJson<T>(
  path: string,
  tenantId?: string | null,
  fallback?: T,
): Promise<{ data: T; ok: boolean }> {
  try {
    const res = await clientFetch(path, tenantId);
    if (!res.ok) {
      return { data: (fallback ?? ([] as T)) as T, ok: false };
    }

    return { data: (await res.json()) as T, ok: true };
  } catch {
    return { data: (fallback ?? ([] as T)) as T, ok: false };
  }
}

export async function fetchAppConfig(tenantId?: string | null) {
  return fetchJson<AppConfig>("/api/config", tenantId, {
    tenancy: { enabled: false, default_tenant: "default", tenants: [] },
  });
}

export async function fetchDevices(tenantId?: string | null) {
  return fetchJson<DeviceSummary[]>("/api/devices?limit=200", tenantId);
}

export async function fetchRecentEvents(
  limit = 200,
  tenantId?: string | null,
  deviceId?: string,
) {
  const deviceQuery = deviceId ? `&device_id=${encodeURIComponent(deviceId)}` : "";
  return fetchJson<TelemetryEvent[]>(
    `/api/events?limit=${limit}${deviceQuery}`,
    tenantId,
  );
}

export async function fetchRecentAnomalies(
  limit = 50,
  tenantId?: string | null,
  deviceId?: string,
) {
  const deviceQuery = deviceId ? `&device_id=${encodeURIComponent(deviceId)}` : "";
  return fetchJson<AnomalyScore[]>(
    `/api/anomalies?limit=${limit}${deviceQuery}`,
    tenantId,
  );
}

export async function fetchWindowStats(
  deviceId: string,
  tenantId?: string | null,
  limit = 100,
) {
  return fetchJson<WindowStat[]>(
    `/api/window-stats?device_id=${encodeURIComponent(deviceId)}&limit=${limit}`,
    tenantId,
  );
}

export interface DashboardSnapshot {
  metrics: PipelineMetrics;
  events: TelemetryEvent[];
  anomalies: AnomalyScore[];
  ok: boolean;
}

export async function fetchDashboardSnapshot(
  tenantId?: string | null,
): Promise<DashboardSnapshot> {
  const [metricsRes, eventsRes, anomaliesRes] = await Promise.all([
    fetchPipelineMetrics(tenantId),
    fetchRecentEvents(200, tenantId),
    fetchRecentAnomalies(50, tenantId),
  ]);

  const ok = metricsRes.ok || eventsRes.ok || anomaliesRes.ok;

  return {
    metrics: metricsRes.metrics,
    events: eventsRes.data,
    anomalies: anomaliesRes.data,
    ok,
  };
}