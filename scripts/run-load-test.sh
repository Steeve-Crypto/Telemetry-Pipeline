#!/usr/bin/env bash
# Run telemetry load tests targeting 100k+ events/sec.
set -euo pipefail

cd "$(dirname "$0")/.."

MODE="${MODE:-direct}"
EVENTS="${EVENTS:-100000}"
TARGET_EPS="${TARGET_EPS:-100000}"
WORKERS="${WORKERS:-4}"
CONFIG="${CONFIG:-config/pipeline.load.yaml}"

echo "==> Load test mode=${MODE} events=${EVENTS} target_eps=${TARGET_EPS}"

case "${MODE}" in
  direct)
    telemetry-load \
      --mode direct \
      --config "${CONFIG}" \
      --events "${EVENTS}" \
      --target-eps "${TARGET_EPS}" \
      --workers "${WORKERS}" \
      --warmup 1000 \
      --report load_test_report.json
    ;;
  kafka-producer)
    telemetry-load \
      --mode kafka-producer \
      --config "${CONFIG}" \
      --events "${EVENTS}" \
      --target-eps "${TARGET_EPS}" \
      --workers "${WORKERS}" \
      --report load_test_report.json
    ;;
  e2e-kafka)
    DURATION="${DURATION:-30}"
    telemetry-load \
      --mode e2e-kafka \
      --config "${CONFIG}" \
      --duration "${DURATION}" \
      --target-eps "${TARGET_EPS}" \
      --workers "${WORKERS}" \
      --report load_test_report.json
    ;;
  *)
    echo "Unknown MODE=${MODE} (direct|kafka-producer|e2e-kafka)" >&2
    exit 1
    ;;
esac

echo "==> Report: load_test_report.json"