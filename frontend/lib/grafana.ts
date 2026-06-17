const GRAFANA_BASE =
  process.env.NEXT_PUBLIC_GRAFANA_URL ?? "http://localhost:3000";

export type OpsDashboard = {
  id: string;
  label: string;
  uid: string;
  slug: string;
};

export const OPS_DASHBOARDS: OpsDashboard[] = [
  {
    id: "overview",
    label: "Overview",
    uid: "telemetry-overview",
    slug: "signal-overview",
  },
  {
    id: "tenant",
    label: "Tenant signal",
    uid: "telemetry-tenant-metrics",
    slug: "tenant-signal",
  },
  {
    id: "ml",
    label: "ML evaluation",
    uid: "telemetry-ml-eval",
    slug: "ml-evaluation",
  },
];

export function grafanaEmbedUrl(dashboard: OpsDashboard): string {
  const params = new URLSearchParams({
    orgId: "1",
    kiosk: "tv",
    theme: "light",
  });
  return `${GRAFANA_BASE}/d/${dashboard.uid}?${params}`;
}

export function grafanaExternalUrl(dashboard: OpsDashboard): string {
  return `${GRAFANA_BASE}/d/${dashboard.uid}`;
}