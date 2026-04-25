from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from sqlalchemy import select

from app.core.database import SessionLocal
from app.ml.metrics import compute_metrics, save_confusion_matrix_plot, save_report, save_roc_plot
from app.models.db_models import RawEvent, SessionRecord
from app.services.feature_engineering import FEATURE_COLUMNS, build_feature_vector
from app.services.model_manager import model_manager
from app.services.training_data_service import TrainingDataService


def evaluate() -> None:
    parser = argparse.ArgumentParser(description="Evaluate active model")
    parser.add_argument("--window-size", type=int, default=120)
    parser.add_argument("--stride", type=int, default=80)
    parser.add_argument("--risk-threshold", type=float, default=70.0)
    args = parser.parse_args()

    if not model_manager.has_active_model():
        raise RuntimeError("No active model. Train model first.")

    db = SessionLocal()
    try:
        training_data_service = TrainingDataService(db)
        frame = training_data_service.build_training_dataframe(
            window_size=args.window_size,
            stride=args.stride,
        )

        if frame.empty:
            raise RuntimeError("No labeled data available for evaluation")

        bundle = model_manager._load_bundle()
        model = bundle["model"]

        X = frame[FEATURE_COLUMNS].astype(float).to_numpy()
        y_true = frame["label"].astype(int).to_numpy()
        y_prob = model.predict_proba(X)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        metrics = compute_metrics(y_true, y_pred, y_prob)
        detection_delay = _compute_detection_delay(
            db,
            model,
            window_size=args.window_size,
            stride=max(5, args.stride // 2),
            risk_threshold=args.risk_threshold,
        )
        unseen_bot_recall = _compute_unseen_bot_recall(db, model, window_size=args.window_size)

        report = {
            "metrics": metrics,
            "detection_delay": detection_delay,
            "unseen_bot_recall": unseen_bot_recall,
            "samples": int(len(frame)),
            "sessions": int(frame["session_id"].nunique()),
        }

        report_dir = Path("./models_artifacts/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        save_confusion_matrix_plot(y_true, y_pred, str(report_dir / "eval_confusion_matrix.png"))
        save_roc_plot(y_true, y_prob, str(report_dir / "eval_roc.png"))
        save_report(report, str(report_dir / "evaluation_report.json"))

        print("Evaluation report saved to models_artifacts/reports/evaluation_report.json")
        print(report)
    finally:
        db.close()


def _compute_detection_delay(db, model, window_size: int, stride: int, risk_threshold: float) -> dict:
    bot_sessions_stmt = select(SessionRecord).where(SessionRecord.true_label == "bot")
    bot_sessions = list(db.execute(bot_sessions_stmt).scalars().all())

    delays = []

    for session in bot_sessions:
        events_stmt = (
            select(RawEvent)
            .where(RawEvent.session_id == session.id)
            .order_by(RawEvent.sequence_no.asc())
        )
        events = list(db.execute(events_stmt).scalars().all())
        if len(events) < 20:
            continue

        merged_env = {**(session.client_fingerprint or {}), **(session.environment or {})}

        detected_at = None
        for end_idx in range(window_size, len(events) + 1, stride):
            window = events[max(0, end_idx - window_size) : end_idx]
            features = build_feature_vector(window, merged_env)
            X = np.array([[features.get(col, 0.0) for col in FEATURE_COLUMNS]], dtype=float)
            probability_bot = float(model.predict_proba(X)[0][1])
            if probability_bot * 100.0 >= risk_threshold:
                detected_at = end_idx
                break

        delays.append(detected_at if detected_at is not None else len(events))

    if not delays:
        return {"avg_events_to_detect": None, "median_events_to_detect": None}

    return {
        "avg_events_to_detect": float(np.mean(delays)),
        "median_events_to_detect": float(np.median(delays)),
        "count": int(len(delays)),
    }


def _compute_unseen_bot_recall(db, model, window_size: int) -> dict:
    metadata = model_manager._load_metadata()
    seen_sources = set(metadata.get("seen_bot_sources", []))

    unseen_stmt = select(SessionRecord).where(SessionRecord.true_label == "bot")
    all_bots = list(db.execute(unseen_stmt).scalars().all())
    unseen_bots = [session for session in all_bots if session.source not in seen_sources]

    if not unseen_bots:
        return {"recall": None, "count": 0}

    hits = 0
    total = 0

    for session in unseen_bots:
        events_stmt = (
            select(RawEvent)
            .where(RawEvent.session_id == session.id)
            .order_by(RawEvent.sequence_no.asc())
        )
        events = list(db.execute(events_stmt).scalars().all())
        if len(events) < 20:
            continue

        merged_env = {**(session.client_fingerprint or {}), **(session.environment or {})}
        window = events[-window_size:]
        features = build_feature_vector(window, merged_env)
        X = np.array([[features.get(col, 0.0) for col in FEATURE_COLUMNS]], dtype=float)
        prob_bot = float(model.predict_proba(X)[0][1])
        prediction = 1 if prob_bot >= 0.5 else 0

        hits += int(prediction == 1)
        total += 1

    recall = hits / total if total else None
    return {"recall": recall, "count": total}


if __name__ == "__main__":
    evaluate()
