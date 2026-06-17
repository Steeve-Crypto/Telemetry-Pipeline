import { cn } from "@/lib/utils";

interface TagPillProps {
  label: string;
  value: string;
  className?: string;
}

export function TagPill({ label, value, className }: TagPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-pill border border-border bg-canvas px-2.5 py-1 text-xs",
        className,
      )}
    >
      <span className="text-muted">{label}</span>
      <span className="font-mono text-ink">{value}</span>
    </span>
  );
}