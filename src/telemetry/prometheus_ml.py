"""Prometheus metrics for ML evaluation quality."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest

from telemetry.anomaly.evaluator import EvalReport
from telemetry.config import PrometheusConfig


class MlMetricsExporter:
    def __init__(self, config: PrometheusConfig, registry: CollectorRegistry | None = None) -> None:
        self._registry = registry or CollectorRegistry()
        ns = config.namespace
        labels = ["dataset", "method"]
        self._precision = Gauge(
            f"{ns}_ml_precision",
            "Anomaly detection precision from labeled eval",
            labelnames=labels,
            registry=self._registry,
        )
        self._recall = Gauge(
            f"{ns}_ml_recall",
            "Anomaly detection recall from labeled eval",
            labelnames=labels,
            registry=self._registry,
        )
        self._f1 = Gauge(
            f"{ns}_ml_f1",
            "Anomaly detection F1 from labeled eval",
            labelnames=labels,
            registry=self._registry,
        )

    def set_eval_metrics(self, report: EvalReport) -> None:
        dataset = report.dataset
        self._precision.labels(dataset=dataset, method="ensemble").set(report.precision)
        self._recall.labels(dataset=dataset, method="ensemble").set(report.recall)
        self._f1.labels(dataset=dataset, method="ensemble").set(report.f1)

        for method, stats in report.per_method.items():
            self._precision.labels(dataset=dataset, method=method).set(stats["precision"])
            self._recall.labels(dataset=dataset, method=method).set(stats["recall"])
            self._f1.labels(dataset=dataset, method=method).set(stats["f1"])

    def render(self) -> tuple[bytes, str]:
        return generate_latest(self._registry), CONTENT_TYPE_LATEST