# Telemetry Pipeline — Plan

> **Commit style:** one task = one commit. Keep titles short (`feat(scope): verb object`).
> Example: `feat(grafana): signal theme` — not paragraph-length messages.

## Done

| Area | Status |
|------|--------|
| Core pipeline | Ingestion, validation, windows, anomaly ensemble, TimescaleDB |
| Phase 1–3 | CI, Grafana, Slack, auth, ML eval, ClickHouse profile |
| Phase 4 (infra) | K8s, Helm, ArgoCD, multi-tenant, Kafka topics, VictoriaMetrics, NetPol/PSS, load test |
| Frontend Phases 1–3 | Next.js Signal UI — overview, devices, anomalies, tenant switcher |
| Phase 5 | Grafana Signal theme, dashboard copy/layout, `/ops` embed |

---

## Phase 5 — Grafana + ops UI alignment

**Goal:** Ops dashboards match Signal design tokens; optional embed in product UI.

| # | Task | Commit title |
|---|------|--------------|
| 5.1 | Grafana custom theme JSON (warm bg, teal series, terracotta alerts) | `feat(grafana): signal theme` ✅ |
| 5.2 | Re-layout Overview dashboard (stat strip → hero chart → drill-down) | `feat(grafana): overview layout` ✅ |
| 5.3 | Rename panels to narrative titles (“Signal volume”, “Ingest latency”) | `feat(grafana): panel copy` ✅ |
| 5.4 | Align tenant + ML dashboards to same theme | `feat(grafana): tenant ml theme` ✅ |
| 5.5 | Next.js `/ops` route with embedded Grafana iframe | `feat(frontend): ops embed` ✅ |

**Exit:** Grafana at `:3000` and Signal at `:3001` feel like one product.

---

## Phase 6 — Product polish (Signal frontend)

**Goal:** Fable-level finish; deprecate Streamlit from demo path.

| # | Task | Commit title |
|---|------|--------------|
| 6.1 | Dark/light toggle + `prefers-color-scheme` default | `feat(frontend): theme toggle` |
| 6.2 | Marketing landing page (`/welcome`) with hero + gradient | `feat(frontend): landing page` |
| 6.3 | Onboarding checklist (connect → first event → first anomaly) | `feat(frontend): onboarding` |
| 6.4 | Keyboard shortcuts (`/` search, `g o` overview) | `feat(frontend): shortcuts` |
| 6.5 | SSE `/api/stream` for metrics (replace 1.5s polling) | `feat(api): metrics sse` |
| 6.6 | Lighthouse a11y pass + `prefers-reduced-motion` | `fix(frontend): a11y motion` |
| 6.7 | Remove Streamlit from default `docker compose up` | `chore(compose): drop streamlit default` |

**Exit:** Demo opens `:3001` only; Streamlit optional via profile.

---

## Phase 7 — Real-time depth

**Goal:** Richer API + UI for operators and tenants.

| # | Task | Commit title |
|---|------|--------------|
| 7.1 | `GET /api/devices/:id/summary` (aggregates, health, last anomaly) | `feat(api): device summary` |
| 7.2 | Window stats chart on device detail (Recharts bar/area) | `feat(frontend): window stats chart` |
| 7.3 | Time-range selector (15m / 1h / 24h) on overview + device | `feat(frontend): time range` |
| 7.4 | Anomaly page: group-by-hour timeline + deep link to device | `feat(frontend): anomaly groups` |
| 7.5 | Loki log tail panel on `/ops` (pipeline errors) | `feat(frontend): loki panel` |

**Exit:** Device detail shows windows + history; anomalies navigable end-to-end.

---

## Phase 8 — Production hardening

**Goal:** Safe to run multi-tenant under load in K8s.

| # | Task | Commit title |
|---|------|--------------|
| 8.1 | Helm values for frontend service + `TENANT_API_KEYS` secret | `feat(helm): frontend service` |
| 8.2 | ArgoCD prod overlay (replicas, resources, ingress host) | `feat(gitops): prod overlay` |
| 8.3 | Load test Job in Helm (`telemetry-load` kafka-producer) | `feat(helm): load test job` |
| 8.4 | HPA tuning from load test results (document in README) | `docs(load): hpa guide` |
| 8.5 | External Secrets example for API keys + DB DSN | `feat(k8s): external secrets example` |
| 8.6 | CI: `npm run build` + frontend smoke curl | `ci(frontend): build smoke` |

**Exit:** `helm install` + ArgoCD sync deploys full stack including UI.

---

## Phase 9 — Optional extensions

Pick as needed; each is one commit.

| # | Task | Commit title |
|---|------|--------------|
| 9.1 | ClickHouse storage production profile in Helm | `feat(helm): clickhouse profile` |
| 9.2 | Per-tenant quotas (rate limit + Kafka throttle) | `feat(tenancy): quotas` |
| 9.3 | Webhook alerting from Signal UI config | `feat(frontend): alert settings` |
| 9.4 | Export device CSV / PDF report | `feat(frontend): export report` |

---

## Suggested order

```
Phase 5 (Grafana)  →  Phase 6 (polish)  →  Phase 7 (real-time)
                              ↓
                      Phase 8 (prod)  →  Phase 9 (optional)
```

**Next up:** Phase 6.1 — `feat(frontend): theme toggle`

---

## Commit title cheat sheet

```
feat(scope): add thing      # new feature
fix(scope): thing          # bug fix
docs(scope): thing         # documentation only
chore(scope): thing        # tooling, deps, compose
ci(scope): thing           # GitHub Actions
test(scope): thing         # tests only
```

**Scopes:** `frontend`, `grafana`, `api`, `helm`, `k8s`, `gitops`, `load`, `pipeline`, `compose`, `tenancy`