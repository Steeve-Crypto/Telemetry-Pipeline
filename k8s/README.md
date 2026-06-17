# Kubernetes Deployment

> **Recommended:** use the Helm chart (`helm/telemetry-pipeline/`) and ArgoCD GitOps (`gitops/argocd/`).
> The raw manifests below remain for kustomize-based installs.

Deploy the telemetry pipeline to Kubernetes with multi-tenant API keys and horizontal scaling.

## Prerequisites

- Kubernetes 1.28+
- `kubectl` and `kustomize` (built into kubectl 1.21+)
- Container images built locally or pushed to your registry

## Build images

```bash
docker build -f docker/Dockerfile -t telemetry-pipeline:latest .
docker build -f docker/Dockerfile.simulator -t telemetry-pipeline-simulator:latest .
```

## Deploy (Helm)

```bash
helm upgrade --install telemetry-pipeline ./helm/telemetry-pipeline -n telemetry --create-namespace
```

## Deploy (Kustomize — legacy)

```bash
cp k8s/secret.example.yaml k8s/secret.yaml
kubectl apply -k k8s/
```

## GitOps (ArgoCD)

```bash
# Edit repoURL in gitops/argocd/application-*.yaml first
kubectl apply -k gitops/argocd/
```

## Verify

```bash
kubectl -n telemetry get pods
kubectl -n telemetry port-forward svc/telemetry-pipeline 8080:8080

curl http://localhost:8080/health
curl -H "X-API-Key: acme-secret-key" http://localhost:8080/api/events
```

## Multi-tenancy

Each tenant has a dedicated API key (see `tenancy.tenant_api_keys` in `config/pipeline.k8s.yaml`).
Set `TELEMETRY_TENANT_KEYS` in the Secret for runtime overrides.

Events carry `tenant_id` in tags or the top-level field; API queries are scoped to the authenticated tenant.

## Kafka topic-per-tenant

When `ingestion.kafka.topic_per_tenant: true`, each tenant publishes to its own topic
(e.g. `telemetry.events.acme`). The pipeline consumer subscribes to all configured tenant topics.

Provision topics before deploy:

```bash
telemetry-kafka-init --config config/pipeline.k8s.yaml
```

## Scaling

The HPA scales pipeline pods from 2–8 based on CPU. Increase `maxReplicas` for higher throughput.

## Metrics — VictoriaMetrics (free Prometheus alternative)

Docker and K8s use [VictoriaMetrics](https://victoriametrics.com/) instead of Prometheus for
long-term storage. It is PromQL-compatible, uses less RAM, and needs no license.

- Scrape UI: `http://localhost:8428` (Docker) / `kubectl port-forward svc/victoriametrics 8428:8428`
- Grafana datasource: **VictoriaMetrics** (provisioned automatically)
- Per-tenant dashboard: **Dashboards → Telemetry → Per-Tenant Metrics**

To use vanilla Prometheus instead: `docker compose --profile prometheus up -d` and point Grafana
at `http://prometheus:9090`.