FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir -e .

COPY docker/healthcheck-pipeline.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

ENV PYTHONUNBUFFERED=1
ENV TELEMETRY_PIPELINE_CONFIG_PATH=/app/config/pipeline.yaml
ENV TELEMETRY_SENSORS_CONFIG_PATH=/app/config/sensors.yaml

EXPOSE 8765 8080

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
  CMD ["/healthcheck.sh"]

CMD ["telemetry-pipeline", "--config", "/app/config/pipeline.yaml", "--sensors", "/app/config/sensors.yaml"]