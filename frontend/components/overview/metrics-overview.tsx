"use client";

import { Radio } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { ConnectionStatusBadge } from "@/components/shell/connection-status";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { fetchPipelineMetrics } from "@/lib/api";
import type { ConnectionStatus, PipelineMetrics } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

const POLL_MS = 2000;

export function MetricsOverview() {
  const [metrics, setMetrics] = useState<PipelineMetrics | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setStatus((prev) => (prev === "offline" ? "connecting" : prev));
    const { metrics: data, ok } = await fetchPipelineMetrics();
    setMetrics(data);
    setStatus(ok ? "live" : "offline");
    if (ok) {
      setLastUpdated(new Date());
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const hasSignal = (metrics?.events_ingested ?? 0) > 0;

  return (
    <div className="flex flex-1 flex-col px-8 py-8">
      <PageHeader
        title="Overview"
        description="Ingest → understand → act. Live pipeline health from your telemetry API."
      >
        <ConnectionStatusBadge status={status} />
        {lastUpdated && (
          <time className="text-xs text-muted" dateTime={lastUpdated.toISOString()}>
            Updated {lastUpdated.toLocaleTimeString()}
          </time>
        )}
      </PageHeader>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Ingested"
          value={metrics?.events_ingested ?? 0}
          hint="Total events received"
        />
        <MetricCard
          label="Valid"
          value={metrics?.events_valid ?? 0}
          accent="accent"
          hint="Passed schema validation"
        />
        <MetricCard
          label="Anomalies"
          value={metrics?.anomalies_detected ?? 0}
          accent="alert"
          hint="Ensemble detections"
        />
        <MetricCard
          label="Throughput"
          value={formatNumber(metrics?.processing_rate_eps ?? 0, 1)}
          unit="eps"
          hint="Processing rate"
        />
      </section>

      <section className="mt-4 grid gap-4 sm:grid-cols-3">
        <MetricCard
          label="Invalid"
          value={metrics?.events_invalid ?? 0}
          className="sm:col-span-1"
        />
        <MetricCard
          label="Deduped"
          value={metrics?.events_deduped ?? 0}
          className="sm:col-span-1"
        />
        <MetricCard
          label="P95 processing"
          value={formatNumber(metrics?.p95_processing_latency_ms ?? 0, 1)}
          unit="ms"
          className="sm:col-span-1"
        />
      </section>

      <section className="mt-8">
        {!hasSignal && status !== "connecting" ? (
          <EmptyState
            icon={Radio}
            title="Waiting for signal"
            description={
              status === "offline"
                ? "Cannot reach the pipeline API. Start docker compose or set TELEMETRY_API_URL."
                : "Pipeline is healthy but no events yet. Start the simulator or connect a device."
            }
          />
        ) : (
          <div className="rounded-card border border-border bg-surface p-6 shadow-card">
            <h2 className="font-display text-lg text-ink">Latency snapshot</h2>
            <p className="mt-1 text-sm text-muted">
              Ingest and processing latency from the live metrics endpoint.
            </p>
            <dl className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["Avg ingest", metrics?.avg_ingest_latency_ms, "ms"],
                ["P95 ingest", metrics?.p95_ingest_latency_ms, "ms"],
                ["Avg processing", metrics?.avg_processing_latency_ms, "ms"],
                ["P99 processing", metrics?.p99_processing_latency_ms, "ms"],
              ].map(([label, value, unit]) => (
                <div key={label as string} className="rounded-input bg-canvas px-4 py-3">
                  <dt className="text-xs text-muted">{label}</dt>
                  <dd className="mt-1 font-mono text-lg tabular-nums text-ink">
                    {formatNumber((value as number) ?? 0, 1)}
                    <span className="ml-1 text-sm text-muted">{unit as string}</span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </section>
    </div>
  );
}