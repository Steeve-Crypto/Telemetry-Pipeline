# ArgoCD GitOps

Deploy the telemetry pipeline from Git using [ArgoCD](https://argo-cd.readthedocs.io/) and the Helm chart in `helm/telemetry-pipeline/`.

## Prerequisites

- Kubernetes cluster with ArgoCD installed (`kubectl create namespace argocd` + [ArgoCD manifests](https://argo-cd.readthedocs.io/en/stable/getting_started/))
- Container images built and pushed to your registry
- Git repository URL updated in Application manifests

## Bootstrap

1. Update `repoURL` in `application-dev.yaml` and `application-production.yaml` to your Git remote.

2. Register the AppProject and Applications:

```bash
kubectl apply -k gitops/argocd/
```

3. Open ArgoCD UI and sync **telemetry-pipeline-dev** (or enable automated sync — already on for dev).

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443
# https://localhost:8080 — admin password from argocd-initial-admin-secret
```

## Environments

| Application | Values | Sync |
|-------------|--------|------|
| `telemetry-pipeline-dev` | `values.yaml` | Automated prune + self-heal |
| `telemetry-pipeline-production` | `values.yaml` + `values-production.yaml` | Manual (enable automated after CI gates) |

## Production secrets

Set `secrets.create: false` in `values-production.yaml` and provision:

```bash
kubectl -n telemetry create secret generic telemetry-pipeline-secrets \
  --from-literal=POSTGRES_PASSWORD='...' \
  --from-literal=TELEMETRY_TENANT_KEYS='{"acme":"..."}'
```

Then set `secrets.existingSecretName: telemetry-pipeline-secrets` in values.

## Image promotion

Update Helm parameters in `application-production.yaml` or tag `targetRevision` after CI builds:

```yaml
helm:
  parameters:
    - name: images.pipeline.tag
      value: "0.2.0"
```

## App-of-Apps (optional)

Point a parent ArgoCD Application at `gitops/argocd/` to manage all child apps from one repo path.