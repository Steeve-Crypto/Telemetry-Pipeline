import { cn, formatNumber } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: number | string;
  unit?: string;
  hint?: string;
  accent?: "default" | "accent" | "alert";
  className?: string;
}

export function MetricCard({
  label,
  value,
  unit,
  hint,
  accent = "default",
  className,
}: MetricCardProps) {
  const display =
    typeof value === "number" ? formatNumber(value, Number.isInteger(value) ? 0 : 1) : value;

  return (
    <article
      className={cn(
        "animate-fade-in rounded-card border border-border bg-surface p-5 shadow-card",
        className,
      )}
    >
      <p className="text-sm font-medium text-muted">{label}</p>
      <p
        className={cn(
          "mt-2 font-display text-3xl font-medium tabular-nums tracking-tight animate-count-up",
          accent === "accent" && "text-accent",
          accent === "alert" && "text-alert",
        )}
      >
        {display}
        {unit && (
          <span className="ml-1 font-sans text-base font-normal text-muted">{unit}</span>
        )}
      </p>
      {hint && <p className="mt-2 text-xs text-muted">{hint}</p>}
    </article>
  );
}