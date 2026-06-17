# Signal — Telemetry Frontend

Fable-inspired product UI for the telemetry pipeline. Phase 1: design system + overview shell wired to `/api/metrics`.

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