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

export interface TelemetryEvent {
  device_id: string;
  sensor_type: string;
  timestamp: string;
  metrics: Record<string, number>;
  sequence?: number;
  tags?: Record<string, string>;
  tenant_id?: string;
  is_anomaly?: boolean;
  anomaly_label?: string;
}

export interface AnomalyScore {
  device_id: string;
  sensor_type: string;
  timestamp: string;
  score: number;
  is_anomaly: boolean;
  severity: "low" | "medium" | "high" | "critical";
  methods?: Record<string, number>;
  drift_detected?: boolean;
  message: string;
  tenant_id?: string;
}

export type ConnectionStatus = "live" | "connecting" | "offline";

export interface SparklineHistory {
  ingested: number[];
  valid: number[];
  anomalies: number[];
  throughput: number[];
}

export interface ChartPoint {
  time: string;
  label: string;
  temperature?: number;
  pressure?: number;
  vibration?: number;
}