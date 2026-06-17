"use client";

import { ExternalLink, LayoutDashboard } from "lucide-react";
import { useMemo, useState } from "react";

import {
  OPS_DASHBOARDS,
  grafanaEmbedUrl,
  grafanaExternalUrl,
  type OpsDashboard,
} from "@/lib/grafana";
import { cn } from "@/lib/utils";

export default function OpsPage() {
  const [active, setActive] = useState<OpsDashboard>(OPS_DASHBOARDS[0]);
  const embedUrl = useMemo(() => grafanaEmbedUrl(active), [active]);

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted">Ops</p>
          <h1 className="font-display text-2xl text-ink">Grafana dashboards</h1>
          <p className="mt-1 max-w-xl text-sm text-muted">
            Embedded Signal-themed ops views. Open in Grafana for editing and drill-down.
          </p>
        </div>
        <a
          href={grafanaExternalUrl(active)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-input border border-border bg-surface px-3 py-2 text-sm text-ink transition-colors hover:bg-canvas"
        >
          <ExternalLink className="h-4 w-4" strokeWidth={1.5} />
          Open in Grafana
        </a>
      </header>

      <div
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="Grafana dashboards"
      >
        {OPS_DASHBOARDS.map((dashboard) => (
          <button
            key={dashboard.id}
            type="button"
            role="tab"
            aria-selected={active.id === dashboard.id}
            onClick={() => setActive(dashboard)}
            className={cn(
              "inline-flex items-center gap-2 rounded-input px-3 py-2 text-sm transition-colors",
              active.id === dashboard.id
                ? "bg-accent/10 font-medium text-accent"
                : "text-muted hover:bg-canvas hover:text-ink",
            )}
          >
            <LayoutDashboard className="h-4 w-4" strokeWidth={1.5} />
            {dashboard.label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-hidden rounded-card border border-border bg-surface shadow-card">
        <iframe
          key={active.id}
          title={`Grafana — ${active.label}`}
          src={embedUrl}
          className="h-full w-full border-0"
          allow="fullscreen"
        />
      </div>
    </div>
  );
}