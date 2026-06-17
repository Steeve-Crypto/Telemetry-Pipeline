import Link from "next/link";
import { ChevronRight } from "lucide-react";

import type { DeviceSummary } from "@/lib/types";
import { deviceHealth, healthColor, healthLabel } from "@/lib/device-health";
import { cn, formatNumber } from "@/lib/utils";

interface DeviceCardProps {
  device: DeviceSummary;
}

export function DeviceCard({ device }: DeviceCardProps) {
  const health = deviceHealth(device.last_seen);
  const metricPreview = Object.entries(device.last_metrics).slice(0, 3);

  return (
    <Link
      href={`/devices/${encodeURIComponent(device.device_id)}`}
      className="group block rounded-card border border-border bg-surface p-5 shadow-card transition-all hover:border-accent/30 hover:shadow-[0_8px_28px_rgba(26,24,20,0.08)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-mono text-sm font-medium text-ink">{device.device_id}</p>
          <p className="mt-1 text-xs capitalize text-muted">{device.sensor_type}</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-pill border border-border px-2 py-1 text-[10px] font-medium text-muted">
          <span className={cn("h-2 w-2 rounded-full", healthColor(health))} />
          {healthLabel(health)}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {metricPreview.map(([key, value]) => (
          <span
            key={key}
            className="rounded-pill bg-canvas px-2 py-1 text-[10px] tabular-nums text-muted"
          >
            {key} {formatNumber(value, 1)}
          </span>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-muted">
        <span>{formatNumber(device.event_count)} events</span>
        <span className="inline-flex items-center gap-1 text-accent opacity-0 transition-opacity group-hover:opacity-100">
          View <ChevronRight className="h-3.5 w-3.5" />
        </span>
      </div>
    </Link>
  );
}