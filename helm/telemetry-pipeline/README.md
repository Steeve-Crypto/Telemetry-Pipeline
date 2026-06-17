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
| `podSecurity.enabled` | Namespace PSS labels + workload `securityContext` |
| `networkPolicy.enabled` | Default-deny + per-component allow rules |

## Pod Security Standards

The chart labels the namespace with [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/):

- **enforce:** `baseline` (Redpanda/Timescale need writable roots; pipeline/simulator run as UID 1000)
- **warn / audit:** `restricted`

Pipeline and simulator images run as non-root (`USER 1000` in Dockerfiles) with `readOnlyRootFilesystem` and an `emptyDir` mount at `/tmp`.

Disable with `podSecurity.enabled: false` if your cluster manages PSS elsewhere.

## Network policies

When `networkPolicy.enabled` and `networkPolicy.defaultDeny` are true:

| Workload | Ingress | Egress |
|----------|---------|--------|
| Pipeline | Ingress controller, VictoriaMetrics scrape | TimescaleDB :5432, Redpanda :9092 |
| TimescaleDB | Pipeline only | DNS |
| Redpanda | Pipeline, simulator, kafka-init | Intra-cluster Redpanda, DNS |
| VictoriaMetrics | Same namespace (debug) | Pipeline metrics :8080 |
| Simulator | — | Redpanda :9092 |

Tune `networkPolicy.ingressController.namespace` to match your ingress controller namespace.

## Lint / dry-run

```bash
./scripts/helm-lint.sh
helm template telemetry-pipeline ./helm/telemetry-pipeline --debug
```

## Uninstall

```bash
helm uninstall telemetry-pipeline -n telemetry
```