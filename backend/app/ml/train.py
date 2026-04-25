from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.core.database import SessionLocal
from app.ml.metrics import compute_metrics, save_confusion_matrix_plot, save_roc_plot
from app.repositories.prediction_repo import PredictionRepository
from app.services.feature_engineering import FEATURE_COLUMNS
from app.services.model_manager import model_manager
from app.services.training_data_service import TrainingDataService


def train() -> None:
    parser = argparse.ArgumentParser(description="Train human-vs-bot model")
    parser.add_argument("--window-size", type=int, default=120)
    parser.add_argument("--stride", type=int, default=80)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        training_data_service = TrainingDataService(db)
        frame = training_data_service.build_training_dataframe(
            window_size=args.window_size,
            stride=args.stride,
        )

        if frame.empty:
            raise RuntimeError("No labeled data available. Add labels and collect events first.")

        X = frame[FEATURE_COLUMNS].astype(float).to_numpy()
        y = frame["label"].astype(int).to_numpy()
        groups = frame["session_id"].astype(str).to_numpy()

        if len(np.unique(y)) < 2:
            raise RuntimeError("Training requires both classes: human and bot")

        splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        train_idx, test_idx = next(splitter.split(X, y, groups=groups))

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        models = {
            "logistic_regression": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
                ]
            ),
            "hist_gradient_boosting": HistGradientBoostingClassifier(max_depth=6, random_state=42),
        }

        best_name = None
        best_model = None
        best_metrics = None
        best_proba = None
        best_pred = None

        for name, model in models.items():
            model.fit(X_train, y_train)
            prob = model.predict_proba(X_test)[:, 1]
            pred = (prob >= 0.5).astype(int)
            metrics = compute_metrics(y_test, pred, prob)
            if best_metrics is None or metrics["f1"] > best_metrics["f1"]:
                best_name = name
                best_model = model
                best_metrics = metrics
                best_proba = prob
                best_pred = pred

        assert best_model is not None and best_metrics is not None and best_name is not None

        report_dir = Path("./models_artifacts/reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        save_confusion_matrix_plot(y_test, best_pred, str(report_dir / f"confusion_matrix_{timestamp}.png"))
        save_roc_plot(y_test, best_proba, str(report_dir / f"roc_{timestamp}.png"))

        seen_bot_sources = sorted(
            set(frame[(frame["label"] == 1) & (frame.index.isin(train_idx))]["source"].astype(str).tolist())
        )

        metadata = {
            "version": f"{best_name}_{timestamp}",
            "algorithm": best_name,
            "feature_set_version": "v1",
            "metrics": best_metrics,
            "window_size": args.window_size,
            "stride": args.stride,
            "seen_bot_sources": seen_bot_sources,
        }
        artifact_name, artifact_path = model_manager.save_bundle(
            bundle={
                "model": best_model,
                "feature_columns": FEATURE_COLUMNS,
            },
            metadata=metadata,
        )

        prediction_repo = PredictionRepository(db)
        prediction_repo.upsert_model_version(
            name="behavioral-biometrics",
            version=metadata["version"],
            algorithm=best_name,
            metrics=best_metrics,
            artifact_path=artifact_path,
            model_metadata={
                "artifact_name": artifact_name,
                "window_size": args.window_size,
                "stride": args.stride,
                "seen_bot_sources": seen_bot_sources,
            },
        )

        print("Training finished")
        print(f"Selected model: {best_name}")
        print(f"Version: {metadata['version']}")
        print(f"Metrics: {best_metrics}")
        print(f"Artifact: {artifact_path}")
    finally:
        db.close()


if __name__ == "__main__":
    train()
