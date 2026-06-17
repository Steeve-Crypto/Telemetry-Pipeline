"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { SensorSeriesChart } from "@/components/charts/sensor-series-chart";
import { AnomalyFeed } from "@/components/overview/anomaly-feed";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { TagPill } from "@/components/ui/tag-pill";
import { useTenant } from "@/contexts/tenant-context";
import { fetchRecentAnomalies, fetchRecentEvents } from "@/lib/api";
import { deviceHealth, healthColor, healthLabel } from "@/lib/device-health";
import { eventsToChartPoints } from "@/lib/transforms";
import type { AnomalyScore, TelemetryEvent } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

interface DeviceDetailPageProps {
  deviceId: string;
}

export function DeviceDetailPage({ deviceId }: DeviceDetailPageProps) {
  const { tenantId } = useTenant();
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyScore[]>([]);

  const refresh = useCallback(async () => {
    const [eventsRes, anomaliesRes] = await Promise.all([
      fetchRecentEvents(300, tenantId, deviceId),
      fetchRecentAnomalies(30, tenantId, deviceId),
    ]);
    setEvents(eventsRes.data);
    setAnomalies(anomaliesRes.data);
  }, [tenantId, deviceId]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 2500);
    return () => clearInterval(id);
  }, [refresh]);

  const latest = events[0];
  const chartPoints = useMemo(() => eventsToChartPoints(events), [events]);
  const health = latest ? deviceHealth(latest.timestamp) : "offline";
  const tagEntries = Object.entries(latest?.enriched_tags ?? latest?.tags ?? {}).slice(0, 8);

  return (
    <div className="flex flex-1 flex-col px-8 py-8">
      <Link
        href="/devices"
        className="mb-4 inline-flex w-fit items-center gap-2 text-xs text-muted transition-colors hover:text-accent"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to devices
      </Link>

      <PageHeader
        title={deviceId}
        description={latest ? `${latest.sensor_type} telemetry stream` : "Loading device signal…"}
      >
        <span className="inline-flex items-center gap-1.5 rounded-pill border border-border px-3 py-1.5 text-xs text-muted">
          <span className={cn("h-2 w-2 rounded-full", healthColor(health))} />
          {healthLabel(health)}
        </span>
      </PageHeader>

      {latest && (
        <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(latest.metrics)
            .slice(0, 4)
            .map(([key, value]) => (
              <MetricCard
                key={key}
                label={key}
                value={formatNumber(value, 2)}
                accent={key === "temperature" ? "alert" : "accent"}
              />
            ))}
        </section>
      )}

      {tagEntries.length > 0 && (
        <section className="mt-6 flex flex-wrap gap-2">
          {tagEntries.map(([label, value]) => (
            <TagPill key={label} label={label} value={value} />
          ))}
        </section>
      )}

      <section className="mt-8 grid gap-6 xl:grid-cols-3">
        <article className="xl:col-span-2 rounded-card border border-border bg-surface p-6 shadow-card">
          <h2 className="font-display text-lg text-ink">24h signal</h2>
          <p className="mt-1 text-sm text-muted">Recent metric samples for this device</p>
          <div className="mt-4">
            <SensorSeriesChart data={chartPoints} />
          </div>
        </article>
        <AnomalyFeed anomalies={anomalies} className="min-h-[20rem]" />
      </section>
    </div>
  );
}