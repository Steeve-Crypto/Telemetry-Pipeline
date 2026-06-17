"use client";

import { cn, formatNumber } from "@/lib/utils";

interface LatencyBarsProps {
  items: Array<{ label: string; value: number; unit: string }>;
  className?: string;
}

export function LatencyBars({ items, className }: LatencyBarsProps) {
  const max = Math.max(...items.map((i) => i.value), 1);

  return (
    <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-4", className)}>
      {items.map((item) => {
        const pct = Math.min(100, (item.value / max) * 100);

        return (
          <div key={item.label} className="rounded-input bg-canvas px-4 py-3">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-xs text-muted">{item.label}</span>
              <span className="font-mono text-sm tabular-nums text-ink">
                {formatNumber(item.value, 1)}
                <span className="ml-0.5 text-muted">{item.unit}</span>
              </span>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-pill bg-border">
              <div
                className="h-full rounded-pill bg-accent transition-all duration-500 ease-out"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}