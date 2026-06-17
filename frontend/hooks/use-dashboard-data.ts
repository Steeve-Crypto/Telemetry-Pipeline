"use client";

import { useCallback, useEffect, useState } from "react";

import { useTenant } from "@/contexts/tenant-context";
import { fetchDashboardSnapshot } from "@/lib/api";
import { appendSparkline, EMPTY_SPARKLINE, eventsToChartPoints } from "@/lib/transforms";
import type {
  AnomalyScore,
  ChartPoint,
  ConnectionStatus,
  PipelineMetrics,
  SparklineHistory,
  TelemetryEvent,
} from "@/lib/types";

const POLL_MS = 1500;

export interface DashboardData {
  metrics: PipelineMetrics | null;
  events: TelemetryEvent[];
  anomalies: AnomalyScore[];
  chartPoints: ChartPoint[];
  sparklines: SparklineHistory;
  status: ConnectionStatus;
  lastUpdated: Date | null;
}

export function useDashboardData(): DashboardData {
  const { tenantId } = useTenant();
  const [metrics, setMetrics] = useState<PipelineMetrics | null>(null);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyScore[]>([]);
  const [sparklines, setSparklines] = useState<SparklineHistory>(EMPTY_SPARKLINE);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setStatus((prev) => (prev === "offline" ? "connecting" : prev));

    const snapshot = await fetchDashboardSnapshot(tenantId);

    setMetrics(snapshot.metrics);
    setEvents(snapshot.events);
    setAnomalies(snapshot.anomalies);
    setSparklines((prev) => appendSparkline(prev, snapshot.metrics));
    setStatus(snapshot.ok ? "live" : "offline");

    if (snapshot.ok) {
      setLastUpdated(new Date());
    }
  }, [tenantId]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  return {
    metrics,
    events,
    anomalies,
    chartPoints: eventsToChartPoints(events),
    sparklines,
    status,
    lastUpdated,
  };
}