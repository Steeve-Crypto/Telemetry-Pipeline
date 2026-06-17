"""ML evaluation for anomaly detection against labeled datasets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog

from telemetry.anomaly.detector import AnomalyDetector
from telemetry.config import AnomalyConfig, EvalConfig, SensorsYamlConfig
from telemetry.models import EnrichedEvent, SensorEvent

logger = structlog.get_logger(__name__)


@dataclass
class ConfusionCounts:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.tn + self.fn
        return (self.tp + self.tn) / total if total else 0.0


@dataclass
class ThresholdResult:
    threshold: float
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    tn: int
    fn: int


@dataclass
class EvalReport:
    dataset: str
    total_events: int
    labeled_events: int
    warmup_events: int
    threshold: float
    confusion: ConfusionCounts
    precision: float
    recall: float
    f1: float
    accuracy: float
    per_method: dict[str, dict[str, float]] = field(default_factory=dict)
    threshold_sweep: list[ThresholdResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        data = asdict(self)
        data["confusion"] = asdict(self.confusion)
        data["threshold_sweep"] = [asdict(t) for t in self.threshold_sweep]
        return data

    def print_summary(self) -> None:
        c = self.confusion
        print("\n=== Anomaly Detection Evaluation ===")
        print(f"  Dataset:      {self.dataset}")
        print(f"  Labeled:      {self.labeled_events:,} / {self.total_events:,}")
        print(f"  Threshold:    {self.threshold:.2f}")
        print(f"  Precision:    {self.precision:.3f}")
        print(f"  Recall:       {self.recall:.3f}")
        print(f"  F1:           {self.f1:.3f}")
        print(f"  Accuracy:     {self.accuracy:.3f}")
        print(f"  Confusion:    TP={c.tp} FP={c.fp} TN={c.tn} FN={c.fn}")
        if self.per_method:
            print("  Per-method F1:")
            for method, stats in sorted(self.per_method.items()):
                print(f"    {method:20s} F1={stats['f1']:.3f} P={stats['precision']:.3f} R={stats['recall']:.3f}")
        print("====================================\n")


def _to_enriched(event: SensorEvent) -> EnrichedEvent:
    return EnrichedEvent(**event.model_dump())


def _update_confusion(counts: ConfusionCounts, actual: bool, predicted: bool) -> None:
    if actual and predicted:
        counts.tp += 1
    elif actual and not predicted:
        counts.fn += 1
    elif not actual and predicted:
        counts.fp += 1
    else:
        counts.tn += 1


def _ensemble_predicted(result: object | None, threshold: float) -> bool:
    if result is None:
        return False
    return bool(getattr(result, "is_anomaly", False) or getattr(result, "score", 0.0) >= threshold)


def _method_predicted(result: object | None, method: str, threshold: float) -> bool:
    if result is None:
        return False
    methods = getattr(result, "methods", {})
    return float(methods.get(method, 0.0)) >= threshold


def _evaluate_at_threshold(
    events: list[SensorEvent],
    scores: list[object | None],
    threshold: float,
) -> ConfusionCounts:
    counts = ConfusionCounts()
    for event, result in zip(events, scores, strict=True):
        if event.is_anomaly is None:
            continue
        _update_confusion(counts, event.is_anomaly, _ensemble_predicted(result, threshold))
    return counts


def evaluate_detector(
    events: list[SensorEvent],
    detector: AnomalyDetector,
    config: AnomalyConfig,
    eval_config: EvalConfig,
    *,
    dataset_name: str = "dataset",
) -> EvalReport:
    labeled = [e for e in events if e.is_anomaly is not None]
    if not labeled:
        raise ValueError("No labeled events (is_anomaly column required)")

    warmup = min(eval_config.warmup_events, len(labeled) // 2)
    threshold = eval_config.threshold if eval_config.threshold is not None else config.alert_threshold

    scores: list[object | None] = []
    for i, event in enumerate(labeled):
        result = detector.detect(_to_enriched(event))
        if i >= warmup:
            scores.append(result)
        else:
            scores.append(None)

    eval_events = labeled[warmup:]
    eval_scores = scores[warmup:]

    confusion = _evaluate_at_threshold(eval_events, eval_scores, threshold)

    per_method: dict[str, dict[str, float]] = {}
    for method in config.ensemble_weights:
        method_counts = ConfusionCounts()
        for event, result in zip(eval_events, eval_scores, strict=True):
            if event.is_anomaly is None:
                continue
            _update_confusion(
                method_counts,
                event.is_anomaly,
                _method_predicted(result, method, threshold),
            )
        per_method[method] = {
            "precision": method_counts.precision,
            "recall": method_counts.recall,
            "f1": method_counts.f1,
            "tp": method_counts.tp,
            "fp": method_counts.fp,
            "tn": method_counts.tn,
            "fn": method_counts.fn,
        }

    sweep: list[ThresholdResult] = []
    for step in eval_config.threshold_sweep:
        t = round(step, 2)
        c = _evaluate_at_threshold(eval_events, eval_scores, t)
        sweep.append(
            ThresholdResult(
                threshold=t,
                precision=c.precision,
                recall=c.recall,
                f1=c.f1,
                tp=c.tp,
                fp=c.fp,
                tn=c.tn,
                fn=c.fn,
            )
        )

    report = EvalReport(
        dataset=dataset_name,
        total_events=len(events),
        labeled_events=len(labeled),
        warmup_events=warmup,
        threshold=threshold,
        confusion=confusion,
        precision=confusion.precision,
        recall=confusion.recall,
        f1=confusion.f1,
        accuracy=confusion.accuracy,
        per_method=per_method,
        threshold_sweep=sweep,
    )
    logger.info(
        "eval_complete",
        dataset=dataset_name,
        f1=report.f1,
        precision=report.precision,
        recall=report.recall,
    )
    return report


def evaluate_from_csv(
    csv_path: Path,
    pipeline_config: object,
    sensors_config: SensorsYamlConfig,
    eval_config: EvalConfig,
    *,
    device_id: str = "eval-device-001",
    sensor_type: str = "industrial",
    label_col: str = "is_anomaly",
) -> EvalReport:
    from telemetry.simulator.replay import DatasetReplay

    replay = DatasetReplay(
        csv_path=csv_path,
        device_id=device_id,
        sensor_type=sensor_type,
        label_col=label_col,
    )
    events = replay.to_events()
    detector = AnomalyDetector(pipeline_config.anomaly, sensors_config)
    return evaluate_detector(
        events,
        detector,
        pipeline_config.anomaly,
        eval_config,
        dataset_name=csv_path.name,
    )


def write_eval_report(report: EvalReport, path: str | Path) -> Path:
    out = Path(path)
    out.write_text(json.dumps(report.to_dict(), indent=2))
    return out