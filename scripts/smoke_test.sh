#!/usr/bin/env bash
# Local Docker Compose smoke test (same checks as CI)
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Starting stack..."
docker compose up --build -d

echo "==> Waiting for pipeline API..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:8081/health >/dev/null; then
    echo "Pipeline healthy"
    break
  fi
  if [[ $i -eq 60 ]]; then
    echo "Pipeline failed to start"
    docker compose logs pipeline --tail 30
    exit 1
  fi
  sleep 5
done

echo "==> Waiting for events..."
sleep 15
METRICS=$(curl -sf http://localhost:8081/api/metrics)
echo "$METRICS" | python3 -c "
import json, sys
m = json.load(sys.stdin)
assert m.get('events_ingested', 0) > 0, 'No events ingested'
print(f\"OK: {m['events_ingested']} events, {m.get('anomalies_detected', 0)} anomalies\")
"

echo "==> Smoke test passed"