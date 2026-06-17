"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { MethodBreakdownChart } from "@/components/charts/method-breakdown-chart";
import { SeverityDonut } from "@/components/charts/severity-donut";
import { ConnectionStatusBadge } from "@/components/shell/connection-status";
import { TenantSwitcher } from "@/components/shell/tenant-switcher";
import { SeverityChip } from "@/components/ui/severity-chip";
import { FilterChips } from "@/components/ui/filter-chips";
import { PageHeader } from "@/components/ui/page-header";
import { useTenant } from "@/contexts/tenant-context";
import { fetchRecentAnomalies } from "@/lib/api";
import type { AnomalyScore, ConnectionStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const severityBorder: Record<AnomalyScore["severity"], string> = {
  low: "border-l-severity-low",
  medium: "border-l-severity-medium",
  high: "border-l-severity-high",
  critical: "border-l-severity-critical",
};

export function AnomaliesPage() {
  const { tenantId } = useTenant();
  const [anomalies, setAnomalies] = useState<AnomalyScore[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const { data, ok } = await fetchRecentAnomalies(100, tenantId);
    setAnomalies(data);
    setStatus(ok ? "live" : "offline");
  }, [tenantId]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 2500);
    return () => clearInterval(id);
  }, [refresh]);

  const severities = useMemo(
    () => [...new Set(anomalies.map((a) => a.severity))].sort(),
    [anomalies],
  );

  const filtered = useMemo(() => {
    if (!severityFilter) {
      return anomalies;
    }
    return anomalies.filter((a) => a.severity === severityFilter);
  }, [anomalies, severityFilter]);

  const selected = filtered.find(
    (a) => `${a.device_id}-${a.timestamp}` === selectedId,
  ) ?? filtered[0];

  useEffect(() => {
    if (filtered[0] && !selectedId) {
      setSelectedId(`${filtered[0].device_id}-${filtered[0].timestamp}`);
    }
  }, [filtered, selectedId]);

  return (
    <div className="flex flex-1 flex-col px-8 py-8">
      <PageHeader
        title="Anomalies"
        description="Investigate ensemble detections, severity mix, and method contributions."
      >
        <TenantSwitcher />
        <ConnectionStatusBadge status={status} />
      </PageHeader>

      <div className="mt-6">
        <FilterChips
          options={severities}
          value={severityFilter}
          onChange={setSeverityFilter}
          allLabel="All severities"
        />
      </div>

      <section className="mt-8 grid gap-6 xl:grid-cols-3">
        <article className="rounded-card border border-border bg-surface p-6 shadow-card">
          <h2 className="font-display text-lg text-ink">Severity mix</h2>
          <p className="mt-1 text-sm text-muted">Distribution across the current window</p>
          <div className="mt-4">
            <SeverityDonut anomalies={filtered} />
          </div>
        </article>

        <article className="xl:col-span-2 rounded-card border border-border bg-surface p-6 shadow-card">
          <h2 className="font-display text-lg text-ink">Detection breakdown</h2>
          <p className="mt-1 text-sm text-muted">
            Method scores for the selected anomaly
          </p>
          {selected ? (
            <div className="mt-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-ink">{selected.device_id}</span>
                <SeverityChip severity={selected.severity} />
              </div>
              <MethodBreakdownChart anomaly={selected} />
              <p className="mt-3 text-xs leading-relaxed text-muted">{selected.message}</p>
            </div>
          ) : (
            <p className="mt-8 text-sm text-muted">No anomalies to analyze.</p>
          )}
        </article>
      </section>

      <section className="mt-6 space-y-3">
        {filtered.map((item) => {
          const id = `${item.device_id}-${item.timestamp}`;
          const active = selected?.device_id === item.device_id && selected?.timestamp === item.timestamp;

          return (
            <button
              key={id}
              type="button"
              onClick={() => setSelectedId(id)}
              className={cn(
                "w-full rounded-card border border-border border-l-4 bg-surface p-4 text-left shadow-card transition-colors",
                severityBorder[item.severity],
                active && "ring-2 ring-accent/20",
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-sm text-ink">{item.device_id}</span>
                <SeverityChip severity={item.severity} />
              </div>
              <p className="mt-2 text-sm text-muted">{item.message}</p>
              <p className="mt-2 text-xs tabular-nums text-muted">
                score {item.score.toFixed(2)} · {new Date(item.timestamp).toLocaleString()}
              </p>
            </button>
          );
        })}
      </section>
    </div>
  );
}