import { cn } from "@/lib/utils";

type Severity = "low" | "medium" | "high" | "critical";

interface SeverityChipProps {
  severity: Severity;
  className?: string;
}

const styles: Record<Severity, string> = {
  low: "bg-severity-low/15 text-severity-low",
  medium: "bg-severity-medium/15 text-severity-medium",
  high: "bg-severity-high/15 text-severity-high",
  critical: "bg-severity-critical/15 text-severity-critical",
};

export function SeverityChip({ severity, className }: SeverityChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium capitalize",
        styles[severity],
        className,
      )}
    >
      {severity}
    </span>
  );
}