"use client";

import { CheckCircle2, Circle } from "lucide-react";

import type { OnboardingStep } from "@/hooks/use-onboarding-progress";
import { cn } from "@/lib/utils";

interface OnboardingChecklistProps {
  steps: OnboardingStep[];
  className?: string;
  compact?: boolean;
}

export function OnboardingChecklist({
  steps,
  className,
  compact = false,
}: OnboardingChecklistProps) {
  const complete = steps.every((step) => step.done);

  if (complete) {
    return null;
  }

  return (
    <section
      className={cn(
        "rounded-card border border-border bg-surface shadow-card",
        compact ? "p-4" : "p-6",
        className,
      )}
      aria-label="Onboarding checklist"
    >
      <header className={cn(compact ? "mb-3" : "mb-4")}>
        <h2 className={cn("font-display text-ink", compact ? "text-lg" : "text-xl")}>
          Get started
        </h2>
        {!compact && (
          <p className="mt-1 text-sm text-muted">
            Three steps from cold start to actionable signal.
          </p>
        )}
      </header>

      <ol className="space-y-3">
        {steps.map((step, index) => (
          <li
            key={step.id}
            className={cn(
              "flex gap-3 rounded-input border border-border px-3 py-3",
              step.done ? "bg-accent/5" : "bg-canvas/60",
            )}
          >
            {step.done ? (
              <CheckCircle2
                className="mt-0.5 h-4 w-4 shrink-0 text-accent"
                strokeWidth={1.5}
                aria-hidden
              />
            ) : (
              <Circle
                className="mt-0.5 h-4 w-4 shrink-0 text-muted"
                strokeWidth={1.5}
                aria-hidden
              />
            )}
            <div>
              <p className="text-sm font-medium text-ink">
                <span className="sr-only">
                  Step {index + 1} {step.done ? "complete" : "incomplete"}:
                </span>
                {step.title}
              </p>
              <p className="mt-0.5 text-xs text-muted">{step.description}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}