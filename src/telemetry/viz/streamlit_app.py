"""Streamlit real-time dashboard."""

from __future__ import annotations

import json
import time
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


def fetch_json(url: str) -> list | dict:
    try:
        resp = requests.get(url, timeout=2)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


def main() -> None:
    st.set_page_config(page_title="Telemetry Dashboard", layout="wide")
    st.title("Real-Time Telemetry Dashboard")

    api_base = st.sidebar.text_input("API base URL", "http://localhost:8080")
    refresh_ms = st.sidebar.slider("Refresh interval (ms)", 500, 5000, 1000)
    auto_refresh = st.sidebar.checkbox("Auto refresh", value=True)

    metrics = fetch_json(f"{api_base}/api/metrics")
    if isinstance(metrics, dict) and metrics:
        cols = st.columns(6)
        cols[0].metric("Ingested", metrics.get("events_ingested", 0))
        cols[1].metric("Valid", metrics.get("events_valid", 0))
        cols[2].metric("Invalid", metrics.get("events_invalid", 0))
        cols[3].metric("Anomalies", metrics.get("anomalies_detected", 0))
        cols[4].metric("P95 Proc (ms)", f"{metrics.get('p95_processing_latency_ms', 0):.1f}")
        cols[5].metric("Throughput (eps)", f"{metrics.get('processing_rate_eps', 0):.1f}")
        st.caption(
            f"Ingest avg: {metrics.get('avg_ingest_latency_ms', 0):.1f} ms | "
            f"Proc avg: {metrics.get('avg_processing_latency_ms', 0):.1f} ms"
        )

    events = fetch_json(f"{api_base}/api/events?limit=200")
    anomalies = fetch_json(f"{api_base}/api/anomalies?limit=50")

    left, right = st.columns(2)

    with left:
        st.subheader("Recent Events")
        if events:
            df = pd.json_normalize(events)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            metric_cols = [c for c in df.columns if c.startswith("metrics.")]
            if metric_cols:
                chart_df = df[["timestamp"] + metric_cols].set_index("timestamp")
                chart_df.columns = [c.replace("metrics.", "") for c in chart_df.columns]
                st.line_chart(chart_df)
            st.dataframe(df[["device_id", "sensor_type", "timestamp"] + metric_cols].tail(20))
        else:
            st.info("No events yet. Start the pipeline and simulator.")

    with right:
        st.subheader("Anomaly Alerts")
        if anomalies:
            adf = pd.DataFrame(anomalies)
            st.dataframe(
                adf[["timestamp", "device_id", "score", "severity", "message"]],
                use_container_width=True,
            )
        else:
            st.success("No anomalies detected.")

    st.caption(f"Last updated: {datetime.now().isoformat(timespec='seconds')}")

    if auto_refresh:
        time.sleep(refresh_ms / 1000.0)
        st.rerun()


if __name__ == "__main__":
    main()