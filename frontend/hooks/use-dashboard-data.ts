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
const STREAM_INTERVAL_S = "1.5";

export interface DashboardData {
  metrics: PipelineMetrics | null;
  events: TelemetryEvent[];
  anomalies: AnomalyScore[];
  chartPoints: ChartPoint[];
  sparklines: SparklineHistory;
  status: ConnectionStatus;
  lastUpdated: Date | null;
}

interface StreamPayload {
  metrics?: PipelineMetrics;
  events?: TelemetryEvent[];
  anomalies?: AnomalyScore[];
}

function applySnapshot(
  payload: StreamPayload,
  setters: {
    setMetrics: (value: PipelineMetrics | null) => void;
    setEvents: (value: TelemetryEvent[]) => void;
    setAnomalies: (value: AnomalyScore[]) => void;
    setSparklines: React.Dispatch<React.SetStateAction<SparklineHistory>>;
    setStatus: (value: ConnectionStatus) => void;
    setLastUpdated: (value: Date) => void;
  },
) {
  if (payload.metrics) {
    setters.setMetrics(payload.metrics);
    setters.setSparklines((prev) => appendSparkline(prev, payload.metrics!));
  }
  if (payload.events) {
    setters.setEvents(payload.events);
  }
  if (payload.anomalies) {
    setters.setAnomalies(payload.anomalies);
  }

  setters.setStatus("live");
  setters.setLastUpdated(new Date());
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
    let pollId: number | null = null;
    let source: EventSource | null = null;

    const setters = {
      setMetrics,
      setEvents,
      setAnomalies,
      setSparklines,
      setStatus,
      setLastUpdated,
    };

    const startPolling = () => {
      if (pollId !== null) {
        return;
      }

      refresh();
      pollId = window.setInterval(refresh, POLL_MS);
    };

    const tenantQuery = tenantId
      ? `&tenant_id=${encodeURIComponent(tenantId)}`
      : "";
    const streamUrl = `/api/stream?interval=${STREAM_INTERVAL_S}${tenantQuery}`;

    try {
      source = new EventSource(streamUrl);
      source.onopen = () => {
        if (pollId !== null) {
          window.clearInterval(pollId);
          pollId = null;
        }
        setStatus("live");
      };
      source.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as StreamPayload;
          applySnapshot(payload, setters);
        } catch {
          // ignore malformed frames
        }
      };
      source.onerror = () => {
        source?.close();
        source = null;
        setStatus("connecting");
        startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      source?.close();
      if (pollId !== null) {
        window.clearInterval(pollId);
      }
    };
  }, [tenantId, refresh]);

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