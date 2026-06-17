export interface PipelineMetrics {
  events_ingested: number;
  events_valid: number;
  events_invalid: number;
  events_deduped: number;
  anomalies_detected: number;
  avg_ingest_latency_ms: number;
  p95_ingest_latency_ms: number;
  avg_processing_latency_ms: number;
  p95_processing_latency_ms: number;
  p99_processing_latency_ms: number;
  processing_rate_eps: number;
  latency_histogram: Record<string, number>;
}

export type ConnectionStatus = "live" | "connecting" | "offline";