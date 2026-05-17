from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.tree import DecisionTreeClassifier, export_text

from app.core.database import SessionLocal
from app.ml.metrics import (
    compute_metrics,
    save_confusion_matrix_plot,
    save_decision_tree_plot,
    save_feature_importance_plot,
    save_report,
    save_roc_plot,
)
from app.repositories.prediction_repo import PredictionRepository
from app.services.feature_engineering import (
    BEHAVIORAL_FEATURE_COLUMNS,
    ENVIRONMENT_FEATURE_COLUMNS,
    FEATURE_COLUMNS,
)
from app.services.model_manager import model_manager
from app.services.training_data_service import TrainingDataService


def train() -> None:
    parser = argparse.ArgumentParser(description="Train decision tree for human-vs-bot")
    parser.add_argument("--window-size", type=int, default=120)
    parser.add_argument("--stride", type=int, default=80)
    parser.add_argument("--tree-max-depth", type=int, default=6)
    parser.add_argument("--tree-min-samples-leaf", type=int, default=5)
    parser.add_argument(
        "--include-env-in-tree",
        action="store_true",
        help="Allow environment features in tree (can introduce leakage).",
    )
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

        feature_columns = (
            list(FEATURE_COLUMNS) if args.include_env_in_tree else list(BEHAVIORAL_FEATURE_COLUMNS)
        )

        X = frame[feature_columns].astype(float).to_numpy()
        y = frame["label"].astype(int).to_numpy()
        groups = frame["session_id"].astype(str).to_numpy()

        if len(np.unique(y)) < 2:
            raise RuntimeError("Training requires both classes: human and bot")

        splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        train_idx, test_idx = next(splitter.split(X, y, groups=groups))

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = DecisionTreeClassifier(
            max_depth=args.tree_max_depth,
            min_samples_leaf=args.tree_min_samples_leaf,
            class_weight="balanced",
            random_state=42,
        )
        model.fit(X_train, y_train)

        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)
        metrics = compute_metrics(y_test, y_pred, y_prob)

        report_dir = Path("./models_artifacts/reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        save_confusion_matrix_plot(y_test, y_pred, str(report_dir / f"confusion_matrix_{timestamp}.png"))
        save_roc_plot(y_test, y_prob, str(report_dir / f"roc_{timestamp}.png"))

        tree_plot_path = report_dir / f"decision_tree_{timestamp}.png"
        tree_rules_path = report_dir / f"decision_tree_rules_{timestamp}.txt"
        tree_importance_path = report_dir / f"decision_tree_feature_importance_{timestamp}.png"
        training_report_path = report_dir / f"training_report_{timestamp}.json"

        save_decision_tree_plot(
            decision_tree_model=model,
            feature_names=feature_columns,
            output_path=str(tree_plot_path),
            max_depth=min(4, args.tree_max_depth),
        )
        tree_rules = export_text(
            model,
            feature_names=feature_columns,
            max_depth=10,
            decimals=4,
            show_weights=True,
        )
        tree_rules_path.write_text(tree_rules, encoding="utf-8")
        save_feature_importance_plot(
            feature_importances=model.feature_importances_,
            feature_names=feature_columns,
            output_path=str(tree_importance_path),
        )

        seen_bot_sources = sorted(
            set(frame[(frame["label"] == 1) & (frame.index.isin(train_idx))]["source"].astype(str).tolist())
        )

        report = {
            "model": "decision_tree",
            "metrics": metrics,
            "window_size": args.window_size,
            "stride": args.stride,
            "tree_max_depth": args.tree_max_depth,
            "tree_min_samples_leaf": args.tree_min_samples_leaf,
            "include_env_in_tree": args.include_env_in_tree,
            "feature_set": "all" if args.include_env_in_tree else "behavioral",
            "feature_columns": feature_columns,
            "seen_bot_sources": seen_bot_sources,
        }
        save_report(report, str(training_report_path))

        metadata = {
            "version": f"decision_tree_{timestamp}",
            "algorithm": "decision_tree",
            "feature_set_version": "v1",
            "metrics": metrics,
            "window_size": args.window_size,
            "stride": args.stride,
            "include_env_in_tree": args.include_env_in_tree,
            "seen_bot_sources": seen_bot_sources,
        }
        artifact_name, artifact_path = model_manager.save_bundle(
            bundle={
                "model": model,
                "feature_columns": feature_columns,
            },
            metadata=metadata,
        )

        prediction_repo = PredictionRepository(db)
        prediction_repo.upsert_model_version(
            name="behavioral-biometrics",
            version=metadata["version"],
            algorithm="decision_tree",
            metrics=metrics,
            artifact_path=artifact_path,
            model_metadata={
                "artifact_name": artifact_name,
                "window_size": args.window_size,
                "stride": args.stride,
                "include_env_in_tree": args.include_env_in_tree,
                "feature_set": "all" if args.include_env_in_tree else "behavioral",
                "selected_feature_columns": feature_columns,
                "excluded_environment_features_for_tree": []
                if args.include_env_in_tree
                else list(ENVIRONMENT_FEATURE_COLUMNS),
                "seen_bot_sources": seen_bot_sources,
                "training_report": training_report_path.name,
                "decision_tree_diagram": tree_plot_path.name,
                "decision_tree_rules": tree_rules_path.name,
                "decision_tree_feature_importance": tree_importance_path.name,
            },
        )

        print("Training finished")
        print("Selected model: decision_tree")
        print(f"Version: {metadata['version']}")
        print(f"Metrics: {metrics}")
        print(f"Artifact: {artifact_path}")
        print(f"Training report: {training_report_path}")
        print(f"Decision tree diagram: {tree_plot_path}")
        print(f"Decision tree rules: {tree_rules_path}")
        print(f"Decision tree feature importance: {tree_importance_path}")
    finally:
        db.close()


if __name__ == "__main__":
    train()
