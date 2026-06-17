# Signal — Telemetry Frontend

Fable-inspired product UI for the telemetry pipeline.

- **Phase 1**: design system + overview shell
- **Phase 2**: sparklines, sensor chart, anomaly timeline, latency bars (Recharts)
- **Phase 3**: devices fleet, device detail, anomalies explorer, tenant switcher

## Stack

| Layer | Framework / library |
|-------|-------------------|
| App framework | **Next.js 15** (App Router, API route BFF) |
| UI runtime | **React 19** + **TypeScript** |
| Styling | **Tailwind CSS 3** (Fable design tokens) |
| Charts | **Recharts 2** (line, area, bar, donut) |
| Icons | **Lucide React** |
| Utilities | **clsx** + **tailwind-merge** |
| Fonts | **next/font** — Fraunces, Inter, IBM Plex Mono |

## Dev

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3001 (pipeline API expected at http://localhost:8081).

## Docker

```bash
docker compose up frontend pipeline
```

## Stack

- Next.js 15 (App Router)
- Tailwind CSS + Fable design tokens
- Fraunces / Inter / IBM Plex Mono
- API proxy: `GET /api/metrics` → pipeline `VizAPI`