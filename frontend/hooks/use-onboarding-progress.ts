"use client";

import { useMemo } from "react";

import type { AnomalyScore, ConnectionStatus, PipelineMetrics } from "@/lib/types";

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  done: boolean;
}

export function useOnboardingProgress(
  status: ConnectionStatus,
  metrics: PipelineMetrics | null,
  anomalies: AnomalyScore[],
): { steps: OnboardingStep[]; complete: boolean } {
  return useMemo(() => {
    const connected = status === "live";
    const hasEvents = (metrics?.events_ingested ?? 0) > 0;
    const hasAnomaly = (metrics?.anomalies_detected ?? 0) > 0 || anomalies.length > 0;

    const steps: OnboardingStep[] = [
      {
        id: "connect",
        title: "Connect to pipeline",
        description: "Reach the telemetry API and confirm live status.",
        done: connected,
      },
      {
        id: "first-event",
        title: "Receive first event",
        description: "Ingest at least one sensor event into the pipeline.",
        done: hasEvents,
      },
      {
        id: "first-anomaly",
        title: "Detect first anomaly",
        description: "Let the ensemble flag an out-of-band signal.",
        done: hasAnomaly,
      },
    ];

    return { steps, complete: steps.every((step) => step.done) };
  }, [status, metrics, anomalies]);
}