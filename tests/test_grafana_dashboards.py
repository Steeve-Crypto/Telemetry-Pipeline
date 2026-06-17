"""Grafana dashboard provisioning sanity checks."""

from __future__ import annotations

import json
from pathlib import Path

DASHBOARDS_DIR = (
    Path(__file__).resolve().parents[1]
    / "docker"
    / "grafana"
    / "provisioning"
    / "dashboards"
)


def _load(name: str) -> dict:
    return json.loads((DASHBOARDS_DIR / name).read_text())


def test_overview_signal_copy() -> None:
    dash = _load("telemetry-overview.json")
    assert dash["title"] == "Signal Overview"
    titles = {p["title"] for p in dash["panels"]}
    assert "Signal volume" in titles
    assert "Ingest rate" in titles
    assert "signal" in dash["tags"]


def test_tenant_ml_use_victoriametrics() -> None:
    for name in ("tenant-metrics.json", "ml-evaluation.json"):
        dash = _load(name)
        assert "signal" in dash["tags"]
        for panel in dash["panels"]:
            ds = panel.get("datasource", {})
            assert ds.get("uid") == "victoriametrics", f"{name} panel {panel.get('title')}"