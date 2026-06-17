#!/usr/bin/env bash
# Render and validate the telemetry-pipeline Helm chart
set -euo pipefail

cd "$(dirname "$0")/.."
CHART=helm/telemetry-pipeline

if ! command -v helm >/dev/null 2>&1; then
  echo "helm not installed — skipping render (install: https://helm.sh/docs/intro/install/)"
  exit 0
fi

echo "==> helm lint"
helm lint "$CHART" -f "$CHART/values.yaml"
helm lint "$CHART" -f "$CHART/values.yaml" -f "$CHART/values-production.yaml"

echo "==> helm template (dev)"
helm template telemetry-pipeline "$CHART" --namespace telemetry > /tmp/telemetry-helm-dev.yaml
grep -q "kind: Deployment" /tmp/telemetry-helm-dev.yaml

echo "==> helm template (production)"
helm template telemetry-pipeline "$CHART" \
  -f "$CHART/values-production.yaml" \
  --namespace telemetry > /tmp/telemetry-helm-prod.yaml

echo "==> Helm chart OK"