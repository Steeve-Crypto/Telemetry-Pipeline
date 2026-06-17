"use client";

import { Activity, AlertTriangle, Cpu, ExternalLink, Radio } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Overview", icon: Activity, enabled: true },
  { href: "/devices", label: "Devices", icon: Cpu, enabled: false },
  { href: "/anomalies", label: "Anomalies", icon: AlertTriangle, enabled: false },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-border bg-surface px-4 py-6">
      <div className="px-2">
        <Link href="/" className="group flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-input bg-accent text-surface">
            <Radio className="h-4 w-4" strokeWidth={2} />
          </span>
          <div>
            <p className="font-display text-lg leading-none text-ink">Signal</p>
            <p className="text-[10px] uppercase tracking-widest text-muted">Telemetry</p>
          </div>
        </Link>
      </div>

      <nav className="mt-8 flex flex-1 flex-col gap-1" aria-label="Main">
        {nav.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;

          if (!item.enabled) {
            return (
              <span
                key={item.href}
                className="flex cursor-not-allowed items-center gap-3 rounded-input px-3 py-2 text-sm text-muted/50"
                title="Coming soon"
              >
                <Icon className="h-4 w-4" strokeWidth={1.5} />
                {item.label}
              </span>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-input px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-accent/10 font-medium text-accent"
                  : "text-muted hover:bg-canvas hover:text-ink",
              )}
            >
              <Icon className="h-4 w-4" strokeWidth={1.5} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <a
        href="http://localhost:3000"
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto flex items-center gap-2 rounded-input px-3 py-2 text-xs text-muted transition-colors hover:bg-canvas hover:text-ink"
      >
        <ExternalLink className="h-3.5 w-3.5" />
        Grafana ops
      </a>
    </aside>
  );
}