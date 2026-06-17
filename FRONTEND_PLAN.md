# Frontend Plan — Fable-Inspired Redesign

## What exists today

The project has **no custom product UI**. Visualization is split across three surfaces, all functional but visually generic.

### 1. Streamlit dashboard (`telemetry-dashboard`)

~80 lines of default Streamlit chrome. Wide layout, system fonts, purple/white Streamlit theme.

| Area | Content |
|------|---------|
| Header | Plain title: “Real-Time Telemetry Dashboard” |
| Sidebar | API URL text field, refresh slider, auto-refresh checkbox |
| Top row | Six `st.metric` cards (ingested, valid, invalid, anomalies, P95, eps) |
| Left column | `st.line_chart` of recent metrics + raw `st.dataframe` (20 rows) |
| Right column | Anomaly table (timestamp, device, score, severity, message) |
| Footer | ISO timestamp caption |

No branding, no tenant switcher, no auth UI, no empty-state illustration, no dark mode.

### 2. HTTP API (no HTML)

`VizAPI` on `:8080` serves JSON and Prometheus only: `/health`, `/api/events`, `/api/anomalies`, `/api/metrics`, `/metrics`. The API is the data layer for Streamlit; there is no first-party web app.

### 3. Grafana (ops dashboards)

Three provisioned dashboards at `http://localhost:3000` (admin/admin):

| Dashboard | Panels |
|-----------|--------|
| **Telemetry Pipeline Overview** | Stats, time series, tenant/device/sensor variables, anomaly table |
| **Per-Tenant Metrics** | PromQL tenant comparison, ingest/anomaly/latency |
| **ML Evaluation** | F1, precision, recall, per-method quality |

Standard Grafana grid, default theme, SQL + PromQL queries. Built for operators, not end-customers.

---

## Target aesthetic — “Fable made this”

Fable’s work is **narrative-first, typographically confident, and restrained**. For this product, translate that into a telemetry experience that feels like a premium creative tool (Linear / Vercel / Stripe quality), not a boilerplate admin template.

### Design principles

1. **Story arc**: *Ingest → Understand → Act* — every screen answers where data comes from, what changed, and what to do next.
2. **Type is the UI**: One expressive display face for headlines; one neutral grotesk for data density. Numbers are large and calm, never shouty.
3. **Whitespace is structure**: Fewer panels, more breathing room. One primary chart per view; tables are secondary drill-down.
4. **Color with intent**: Warm neutrals (`#F8F5F0` light / `#141210` dark), ink text (`#1A1814`), single accent for live signal (`#2A6B5E` teal) and alert accent (`#C26B4A` terracotta). Severity maps to muted chips, not traffic-light neon.
5. **Motion with purpose**: Subtle count-up on metrics, chart draw-in, anomaly row slide — 200–300ms, ease-out. No decorative parallax.
6. **Craft in empty states**: Illustrated “waiting for signal” moments with one-line narrative copy, not `st.info("No events yet")`.

### Design tokens (starter)

```yaml
font:
  display: "Instrument Serif" | "Fraunces" | custom wordmark
  ui: "Inter" | "Geist" | "Söhne"
  mono: "IBM Plex Mono"  # device IDs, timestamps
color:
  bg: "#F8F5F0"
  surface: "#FFFFFF"
  border: "#E8E4DE"
  text: "#1A1814"
  muted: "#6B6560"
  accent: "#2A6B5E"
  alert: "#C26B4A"
  severity:
    low: "#8A9BA8"
    medium: "#C9A227"
    high: "#C26B4A"
    critical: "#8B2E2E"
radius: 12px cards, 8px inputs, 999px pills
shadow: 0 1px 2px rgba(26,24,20,0.04), 0 8px 24px rgba(26,24,20,0.06)
```

---

## Recommended architecture

Replace Streamlit as the **customer-facing** UI. Keep Grafana for SRE/ML ops.

```
┌─────────────────────────────────────────────────────────┐
│  Next.js 15 (App Router) + Tailwind + shadcn/ui         │
│  frontend/                                              │
│    ├─ (marketing) landing — narrative hero              │
│    ├─ (app) dashboard — live metrics + charts           │
│    ├─ (app) devices/[id] — device story + history       │
│    ├─ (app) anomalies — timeline + filters            │
│    └─ (app) settings — API keys, tenant (if enabled)    │
└───────────────────────┬─────────────────────────────────┘
                        │ REST + SSE (/api/stream)
┌───────────────────────▼─────────────────────────────────┐
│  Existing VizAPI (extend with SSE + window stats)       │
└─────────────────────────────────────────────────────────┘
        Grafana remains parallel for power users / on-call
```

---

## Improvement plan (phased)

### Phase 1 — Design system + shell (1–2 weeks)

- [ ] Add `frontend/` with Next.js, Tailwind, shadcn/ui, dark/light toggle
- [ ] Implement tokens in `globals.css` + `tailwind.config` (Fable palette above)
- [ ] App shell: slim sidebar (logo wordmark, nav icons + labels), top bar (tenant pill, time range, connection status dot)
- [ ] Typography scale: display 32/40 for page titles; tabular nums for metrics
- [ ] Reusable components: `MetricCard`, `SeverityChip`, `DeviceAvatar`, `EmptyState`, `PageHeader`

**Outcome**: Branded shell with placeholder pages that already feel premium.

### Phase 2 — Live dashboard (1–2 weeks)

- [ ] **Overview**: 4 hero metrics (ingested, valid, anomalies, throughput) with sparklines
- [ ] **Primary chart**: multi-series line (temperature / pressure / vibration) — Recharts or Visx, thin strokes, muted grid
- [ ] **Anomaly feed**: right rail timeline with severity chips and one-line “story” (`ensemble=0.82, drift detected`)
- [ ] **SSE or 1s polling** from `/api/metrics` + `/api/events` (replace Streamlit `st.rerun` hack)
- [ ] Empty state: illustration + “Start the simulator or connect a device” CTA

**Outcome**: Replaces Streamlit for day-to-day monitoring.

### Phase 3 — Device & tenant depth (1 week)

- [ ] Device list with search, sensor-type filters, health dot (last event age)
- [ ] Device detail page: metric cards, 24h chart, recent anomalies, enriched tags as pills
- [ ] Tenant switcher in header when `tenancy.enabled` (maps to `X-API-Key`)
- [ ] API extensions: `GET /api/devices`, `GET /api/events?device_id=`, `GET /api/window-stats`

**Outcome**: Multi-tenant SaaS use case is visible in the UI, not only in config.

### Phase 4 — Grafana polish (3–5 days)

- [ ] Custom Grafana theme JSON (match tokens: warm bg, teal series, terracotta alerts)
- [ ] Re-layout dashboards: row 1 narrative stat strip, row 2 single hero time series, row 3 drill-down
- [ ] Consistent panel titles (“Signal volume” not “Events (1h)”)
- [ ] Optional: embed Grafana panels in Next.js via iframe for ops tab

**Outcome**: Ops and customer UIs feel like one product family.

### Phase 5 — Narrative & delight (ongoing)

- [ ] Landing page: hero headline (“Turn sensor noise into signal”), subtle scroll fade, product screenshot on warm gradient
- [ ] Onboarding checklist: connect source → see first event → review first anomaly
- [ ] Keyboard shortcuts (`/` search devices, `g` + `o` go overview)
- [ ] Reduced-motion respect; focus rings on-brand
- [ ] Optional: Loki log tail panel for pipeline errors (operator mode)

**Outcome**: Fable-level “this was designed” feeling, not assembled from widgets.

---

## Page wireframes (text)

### Overview

```
┌─ Sidebar ─┬──────────────────────────────────────────────────┐
│ ◉ Signal    │  Overview          Acme Corp ▾   ● Live  15m ▾  │
│   Devices   │  ─────────────────────────────────────────────  │
│   Anomalies │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│   Ops ↗     │  │ 12.4k│ │ 12.1k│ │  14  │ │ 842  │           │
│             │  │Ingest│ │ Valid│ │ Anom │ │ eps  │           │
│             │  └──────┘ └──────┘ └──────┘ └──────┘           │
│             │  ┌────────────────────────────┬───────────────┐ │
│             │  │     Temperature · Pressure   │ Anomaly feed  │ │
│             │  │     (elegant line chart)     │ ● pump-003    │ │
│             │  │                              │ ● motor-012   │ │
│             │  └────────────────────────────┴───────────────┘ │
└─────────────┴──────────────────────────────────────────────────┘
```

### Anomalies

Timeline-first: grouped by hour, expandable cards with method breakdown bar (statistical / IF / AE / rules), link to device story.

---

## What to deprecate

| Surface | Action |
|---------|--------|
| Streamlit | Keep for quick dev; mark deprecated once Next.js hits parity |
| Raw API | Keep; extend, don’t replace |
| Grafana | Keep for SRE; re-skin, don’t rebuild in React |

---

## Success criteria

- [ ] First impression in &lt;3s: user knows if pipeline is healthy
- [ ] Lighthouse accessibility ≥ 90 on dashboard routes
- [ ] Visual consistency: frontend + Grafana share palette and type hierarchy
- [ ] No default Streamlit purple visible in demo path (`docker compose up` → open new UI on `:3001`)
- [ ] Anomaly severity scannable without reading table columns

---

## Suggested first PR

**`feat(frontend): add design system and overview shell`**

Scope: `frontend/` scaffold, tokens, sidebar layout, mock metrics, Storybook or Ladle for `MetricCard` + `SeverityChip`. No backend changes yet — wires to existing `/api/metrics` when ready.