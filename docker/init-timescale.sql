CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS telemetry_events (
    event_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    ingest_latency_ms DOUBLE PRECISION,
    metrics JSONB NOT NULL,
    tags JSONB,
    is_anomaly BOOLEAN DEFAULT FALSE,
    anomaly_label TEXT,
    PRIMARY KEY (event_id, timestamp)
);

SELECT create_hypertable('telemetry_events', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_events_device_time ON telemetry_events (device_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS window_stats (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    field TEXT NOT NULL,
    count INT NOT NULL,
    mean DOUBLE PRECISION NOT NULL,
    min DOUBLE PRECISION NOT NULL,
    max DOUBLE PRECISION NOT NULL,
    std DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS anomaly_scores (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    is_anomaly BOOLEAN NOT NULL,
    severity TEXT NOT NULL,
    methods JSONB,
    drift_detected BOOLEAN DEFAULT FALSE,
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_anomaly_device_time ON anomaly_scores (device_id, timestamp DESC);