"use client";

import { AlertTriangle } from "lucide-react";

import { SeverityChip } from "@/components/ui/severity-chip";
import type { AnomalyScore } from "@/lib/types";
import { cn } from "@/lib/utils";

interface AnomalyFeedProps {
  anomalies: AnomalyScore[];
  className?: string;
}

const severityBorder: Record<AnomalyScore["severity"], string> = {
  low: "border-l-severity-low",
  medium: "border-l-severity-medium",
  high: "border-l-severity-high",
  critical: "border-l-severity-critical",
};

function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function AnomalyFeed({ anomalies, className }: AnomalyFeedProps) {
  return (
    <section
      className={cn(
        "flex h-full flex-col rounded-card border border-border bg-surface shadow-card",
        className,
      )}
    >
      <header className="border-b border-border px-5 py-4">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-alert/10 text-alert">
            <AlertTriangle className="h-4 w-4" strokeWidth={1.5} />
          </span>
          <div>
            <h2 className="font-display text-lg text-ink">Anomaly feed</h2>
            <p className="text-xs text-muted">Latest detections from the ensemble</p>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {anomalies.length === 0 ? (
          <div className="flex h-full min-h-48 flex-col items-center justify-center rounded-input bg-canvas/60 px-4 text-center">
            <div className="h-10 w-10 rounded-full bg-accent/10" />
            <p className="mt-3 text-sm font-medium text-ink">All clear</p>
            <p className="mt-1 text-xs text-muted">No anomalies in the current window</p>
          </div>
        ) : (
          <ol className="relative space-y-3 before:absolute before:bottom-2 before:left-[11px] before:top-2 before:w-px before:bg-border">
            {anomalies.slice(0, 12).map((item, index) => (
              <li
                key={`${item.device_id}-${item.timestamp}-${index}`}
                className={cn(
                  "relative ml-6 animate-fade-in rounded-input border border-border border-l-4 bg-canvas/40 px-3 py-3",
                  severityBorder[item.severity],
                )}
              >
                <span
                  className="absolute -left-6 top-4 h-2.5 w-2.5 rounded-full border-2 border-surface bg-accent"
                  aria-hidden
                />
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-mono text-xs text-ink">{item.device_id}</p>
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">
                      {item.message || "Anomaly detected"}
                    </p>
                  </div>
                  <SeverityChip severity={item.severity} />
                </div>
                <div className="mt-2 flex items-center justify-between text-[10px] text-muted">
                  <span className="tabular-nums">score {item.score.toFixed(2)}</span>
                  <time dateTime={item.timestamp}>{formatTime(item.timestamp)}</time>
                </div>
                {item.drift_detected && (
                  <p className="mt-1.5 text-[10px] font-medium uppercase tracking-wide text-alert">
                    Drift detected
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}