# telemetry-pipeline Helm Chart

Kubernetes deployment for the telemetry pipeline stack:

- Pipeline API (HPA, probes, graceful shutdown)
- Simulator (optional)
- TimescaleDB (StatefulSet)
- Redpanda (Kafka) + topic init Job
- VictoriaMetrics (Prometheus-compatible metrics)
- Ingress

## Install

```bash
# Build images first
docker build -f docker/Dockerfile -t telemetry-pipeline:latest .
docker build -f docker/Dockerfile.simulator -t telemetry-pipeline-simulator:latest .

helm upgrade --install telemetry-pipeline ./helm/telemetry-pipeline \
  --namespace telemetry --create-namespace
```

## Production

```bash
helm upgrade --install telemetry-pipeline ./helm/telemetry-pipeline \
  -f helm/telemetry-pipeline/values-production.yaml \
  --set secrets.create=false \
  --set secrets.existingSecretName=telemetry-pipeline-secrets \
  --namespace telemetry
```

## Key values

| Value | Description |
|-------|-------------|
| `pipeline.replicas` | Pipeline deployment size |
| `pipeline.autoscaling.*` | HPA min/max/target CPU |
| `kafka.tenants` | Per-tenant Kafka topics |
| `secrets.create` | Create dev Secret (disable in prod) |
| `victoriametrics.enabled` | Free PromQL metrics backend |
| `simulator.enabled` | Synthetic load generator |

## Lint / dry-run

```bash
./scripts/helm-lint.sh
helm template telemetry-pipeline ./helm/telemetry-pipeline --debug
```

## Uninstall

```bash
helm uninstall telemetry-pipeline -n telemetry
```