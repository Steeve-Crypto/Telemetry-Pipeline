import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/lib/types";

interface ConnectionStatusBadgeProps {
  status: ConnectionStatus;
}

const config: Record<ConnectionStatus, { label: string; dot: string }> = {
  live: { label: "Live", dot: "bg-accent animate-pulse" },
  connecting: { label: "Connecting", dot: "bg-severity-medium animate-pulse" },
  offline: { label: "Offline", dot: "bg-severity-critical" },
};

export function ConnectionStatusBadge({ status }: ConnectionStatusBadgeProps) {
  const { label, dot } = config[status];

  return (
    <span className="inline-flex items-center gap-2 rounded-pill border border-border bg-surface px-3 py-1.5 text-xs font-medium text-muted">
      <span className={cn("h-2 w-2 rounded-full", dot)} aria-hidden />
      {label}
    </span>
  );
}