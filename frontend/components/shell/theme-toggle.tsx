"use client";

import { Laptop, Moon, Sun } from "lucide-react";

import { useTheme, type ThemePreference } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";

const labels: Record<ThemePreference, string> = {
  system: "System theme",
  light: "Light theme",
  dark: "Dark theme",
};

const icons: Record<ThemePreference, typeof Sun> = {
  system: Laptop,
  light: Sun,
  dark: Moon,
};

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className }: ThemeToggleProps) {
  const { preference, cyclePreference } = useTheme();
  const Icon = icons[preference];

  return (
    <button
      type="button"
      onClick={cyclePreference}
      className={cn(
        "inline-flex items-center gap-2 rounded-input px-3 py-2 text-xs text-muted transition-colors",
        "hover:bg-canvas hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30",
        className,
      )}
      aria-label={labels[preference]}
      title={labels[preference]}
    >
      <Icon className="h-3.5 w-3.5" strokeWidth={1.5} aria-hidden />
      <span className="capitalize">{preference}</span>
    </button>
  );
}