# Kubernetes Deployment

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

## Deploy

```bash
# Copy and edit secrets
cp k8s/secret.example.yaml k8s/secret.yaml
# Edit TELEMETRY_TENANT_KEYS and POSTGRES_PASSWORD

kubectl apply -k k8s/
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

## Scaling

The HPA scales pipeline pods from 2–8 based on CPU. Increase `maxReplicas` for higher throughput.