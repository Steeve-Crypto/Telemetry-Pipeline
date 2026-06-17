"use client";

import { Activity, AlertTriangle, Cpu, LayoutDashboard, Radio } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Overview", icon: Activity },
  { href: "/devices", label: "Devices", icon: Cpu },
  { href: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/ops", label: "Ops", icon: LayoutDashboard },
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
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;

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

    </aside>
  );
}