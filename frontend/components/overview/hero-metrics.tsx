"use client";

import { Sparkline } from "@/components/charts/sparkline";
import { MetricCard } from "@/components/ui/metric-card";
import type { PipelineMetrics, SparklineHistory } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

interface HeroMetricsProps {
  metrics: PipelineMetrics | null;
  sparklines: SparklineHistory;
}

export function HeroMetrics({ metrics, sparklines }: HeroMetricsProps) {
  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Ingested"
        value={metrics?.events_ingested ?? 0}
        hint="Total events received"
        footer={<Sparkline data={sparklines.ingested} />}
      />
      <MetricCard
        label="Valid"
        value={metrics?.events_valid ?? 0}
        accent="accent"
        hint="Passed schema validation"
        footer={<Sparkline data={sparklines.valid} color="accent" />}
      />
      <MetricCard
        label="Anomalies"
        value={metrics?.anomalies_detected ?? 0}
        accent="alert"
        hint="Ensemble detections"
        footer={<Sparkline data={sparklines.anomalies} color="alert" />}
      />
      <MetricCard
        label="Throughput"
        value={formatNumber(metrics?.processing_rate_eps ?? 0, 1)}
        unit="eps"
        hint="Processing rate"
        footer={<Sparkline data={sparklines.throughput} color="accent" />}
      />
    </section>
  );
}