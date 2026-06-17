"use client";

import { cn } from "@/lib/utils";

interface FilterChipsProps {
  options: string[];
  value: string | null;
  onChange: (value: string | null) => void;
  allLabel?: string;
}

export function FilterChips({
  options,
  value,
  onChange,
  allLabel = "All types",
}: FilterChipsProps) {
  const chips = [null, ...options];

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by sensor type">
      {chips.map((option) => {
        const active = value === option;
        const label = option ?? allLabel;

        return (
          <button
            key={label}
            type="button"
            onClick={() => onChange(option)}
            className={cn(
              "rounded-pill border px-3 py-1.5 text-xs font-medium transition-colors",
              active
                ? "border-accent bg-accent/10 text-accent"
                : "border-border bg-surface text-muted hover:border-accent/30 hover:text-ink",
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}