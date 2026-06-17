"use client";

import { Play, Radio } from "lucide-react";

import { LatencyBars } from "@/components/charts/latency-bars";
import { SensorSeriesChart } from "@/components/charts/sensor-series-chart";
import { ConnectionStatusBadge } from "@/components/shell/connection-status";
import { TenantSwitcher } from "@/components/shell/tenant-switcher";
import { AnomalyFeed } from "@/components/overview/anomaly-feed";
import { HeroMetrics } from "@/components/overview/hero-metrics";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import { SERIES_META } from "@/lib/chart-theme";

export function MetricsOverview() {
  const { metrics, events, anomalies, chartPoints, sparklines, status, lastUpdated } =
    useDashboardData();

  const hasSignal = (metrics?.events_ingested ?? 0) > 0 || events.length > 0;
  const showEmpty = !hasSignal && status !== "connecting";

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      {/* Ambient gradient mesh */}
      <div
        className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-accent/8 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -left-24 top-1/3 h-72 w-72 rounded-full bg-alert/6 blur-3xl"
        aria-hidden
      />

      <div className="relative flex flex-1 flex-col px-8 py-8">
        <PageHeader
          title="Overview"
          description="Ingest → understand → act. Live sensor signal with anomaly context."
        >
          <TenantSwitcher />
        <ConnectionStatusBadge status={status} />
          {lastUpdated && (
            <time className="text-xs text-muted" dateTime={lastUpdated.toISOString()}>
              Updated {lastUpdated.toLocaleTimeString()}
            </time>
          )}
        </PageHeader>

        <div className="mt-8">
          <HeroMetrics metrics={metrics} sparklines={sparklines} />
        </div>

        {showEmpty ? (
          <section className="mt-8">
            <EmptyState
              icon={Radio}
              title="Waiting for signal"
              description={
                status === "offline"
                  ? "Cannot reach the pipeline API. Start docker compose or set TELEMETRY_API_URL."
                  : "Pipeline is healthy but no events yet. Start the simulator or connect a device."
              }
              action={
                <p className="inline-flex items-center gap-2 rounded-pill border border-border bg-surface px-4 py-2 text-xs text-muted">
                  <Play className="h-3.5 w-3.5 text-accent" />
                  <code className="font-mono">docker compose up pipeline simulator</code>
                </p>
              }
            />
          </section>
        ) : (
          <>
            <section className="mt-8 grid gap-6 xl:grid-cols-3">
              <article className="xl:col-span-2 rounded-card border border-border bg-surface p-6 shadow-card">
                <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <h2 className="font-display text-xl text-ink">Sensor signal</h2>
                    <p className="mt-1 text-sm text-muted">
                      Temperature, pressure, and vibration from recent events
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {SERIES_META.map((s) => (
                      <span key={s.key} className="inline-flex items-center gap-1.5 text-xs text-muted">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: s.color }}
                        />
                        {s.label}
                      </span>
                    ))}
                  </div>
                </header>
                <SensorSeriesChart data={chartPoints} />
              </article>

              <AnomalyFeed anomalies={anomalies} className="min-h-[22rem] xl:min-h-0" />
            </section>

            <section className="mt-6 rounded-card border border-border bg-surface p-6 shadow-card">
              <header className="mb-4">
                <h2 className="font-display text-lg text-ink">Latency profile</h2>
                <p className="mt-1 text-sm text-muted">
                  Ingest and processing percentiles from the live metrics stream
                </p>
              </header>
              <LatencyBars
                items={[
                  { label: "Avg ingest", value: metrics?.avg_ingest_latency_ms ?? 0, unit: "ms" },
                  { label: "P95 ingest", value: metrics?.p95_ingest_latency_ms ?? 0, unit: "ms" },
                  {
                    label: "Avg processing",
                    value: metrics?.avg_processing_latency_ms ?? 0,
                    unit: "ms",
                  },
                  {
                    label: "P99 processing",
                    value: metrics?.p99_processing_latency_ms ?? 0,
                    unit: "ms",
                  },
                ]}
              />
            </section>
          </>
        )}
      </div>
    </div>
  );
}