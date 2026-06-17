"""Per-tenant Prometheus metrics tests."""

from telemetry.prometheus import PrometheusExporter, TenantMetricSnapshot
from telemetry.config import PrometheusConfig


def test_per_tenant_counter_labels():
    exporter = PrometheusExporter(PrometheusConfig(per_tenant_labels=True))
    exporter.record_event(TenantMetricSnapshot(tenant_id="acme", ingested=1, valid=1))
    exporter.record_event(TenantMetricSnapshot(tenant_id="globex", ingested=1, valid=1))

    body, _ = exporter.render()
    text = body.decode()
    assert 'telemetry_events_ingested_total{tenant_id="acme"}' in text
    assert 'telemetry_events_ingested_total{tenant_id="globex"}' in text
    assert 'telemetry_events_valid_total{tenant_id="acme"} 1.0' in text


def test_global_metrics_without_tenant_labels():
    exporter = PrometheusExporter(PrometheusConfig(per_tenant_labels=False))
    exporter.record_event(TenantMetricSnapshot(ingested=2, valid=2, throughput_eps=100))

    body, _ = exporter.render()
    text = body.decode()
    assert "tenant_id" not in text
    assert "telemetry_throughput_eps 100.0" in text