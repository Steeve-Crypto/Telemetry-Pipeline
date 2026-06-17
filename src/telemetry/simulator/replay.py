"""Replay labeled datasets (NAB-style CSV, pump sensor data)."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog
import websockets

from telemetry.config import PipelineYamlConfig, load_pipeline_config
from telemetry.models import SensorEvent

logger = structlog.get_logger(__name__)


class DatasetReplay:
    def __init__(
        self,
        csv_path: Path,
        device_id: str = "replay-device-001",
        sensor_type: str = "industrial",
        timestamp_col: str = "timestamp",
        value_cols: list[str] | None = None,
        label_col: str | None = "is_anomaly",
        speed_multiplier: float = 1.0,
    ) -> None:
        self.csv_path = csv_path
        self.device_id = device_id
        self.sensor_type = sensor_type
        self.timestamp_col = timestamp_col
        self.value_cols = value_cols
        self.label_col = label_col
        self.speed_multiplier = speed_multiplier
        self._df: pd.DataFrame | None = None

    def load(self) -> pd.DataFrame:
        df = pd.read_csv(self.csv_path)
        if self.timestamp_col not in df.columns:
            df[self.timestamp_col] = pd.date_range("2024-01-01", periods=len(df), freq="1s")
        if self.value_cols is None:
            exclude = {self.timestamp_col, self.label_col, "anomaly", "label"}
            self.value_cols = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]
        self._df = df
        return df

    def to_events(self) -> list[SensorEvent]:
        if self._df is None:
            self.load()
        assert self._df is not None
        events: list[SensorEvent] = []
        for i, row in self._df.iterrows():
            ts = row[self.timestamp_col]
            if isinstance(ts, str):
                timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                timestamp = pd.Timestamp(ts).to_pydatetime()
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            metrics = {col: float(row[col]) for col in self.value_cols or []}
            is_anomaly = None
            anomaly_label = None
            if self.label_col and self.label_col in row.index:
                val = row[self.label_col]
                if pd.notna(val):
                    is_anomaly = bool(int(val))
                    anomaly_label = "dataset_label" if is_anomaly else None

            events.append(
                SensorEvent(
                    device_id=self.device_id,
                    sensor_type=self.sensor_type,
                    timestamp=timestamp,
                    sequence=int(i),
                    metrics=metrics,
                    tags={"source": "replay", "file": self.csv_path.name},
                    is_anomaly=is_anomaly,
                    anomaly_label=anomaly_label,
                )
            )
        return events

    async def replay_websocket(self, pipeline_config: PipelineYamlConfig) -> int:
        events = self.to_events()
        ws_cfg = pipeline_config.ingestion.websocket
        uri = f"ws://{ws_cfg.host if ws_cfg.host != '0.0.0.0' else 'localhost'}:{ws_cfg.port}"
        sent = 0
        async with websockets.connect(uri) as ws:
            prev_ts = None
            for event in events:
                if prev_ts is not None:
                    delta = (event.timestamp - prev_ts).total_seconds()
                    await asyncio.sleep(max(0, delta / self.speed_multiplier))
                prev_ts = event.timestamp
                await ws.send(event.model_dump_json())
                sent += 1
        return sent


async def async_main(args: argparse.Namespace) -> None:
    pipeline = load_pipeline_config(args.config)
    replay = DatasetReplay(
        csv_path=Path(args.csv),
        device_id=args.device_id,
        sensor_type=args.sensor_type,
        timestamp_col=args.timestamp_col,
        value_cols=args.value_cols.split(",") if args.value_cols else None,
        label_col=args.label_col,
        speed_multiplier=args.speed,
    )
    sent = await replay.replay_websocket(pipeline)
    logger.info("replay_finished", events_sent=sent, file=args.csv)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay CSV telemetry datasets")
    parser.add_argument("--csv", required=True, help="Path to CSV dataset")
    parser.add_argument("--config", default="config/pipeline.yaml")
    parser.add_argument("--device-id", default="replay-device-001")
    parser.add_argument("--sensor-type", default="industrial")
    parser.add_argument("--timestamp-col", default="timestamp")
    parser.add_argument("--value-cols", default=None, help="Comma-separated metric columns")
    parser.add_argument("--label-col", default="is_anomaly")
    parser.add_argument("--speed", type=float, default=10.0, help="Replay speed multiplier")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()