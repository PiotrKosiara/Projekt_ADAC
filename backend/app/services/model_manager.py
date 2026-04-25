from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np

from app.core.config import settings
from app.services.feature_engineering import FEATURE_COLUMNS, to_feature_array


@dataclass
class ModelPrediction:
    predicted_label: str
    probability_bot: float
    confidence: float
    risk_score: float
    model_version: str | None


class ModelManager:
    def __init__(self, artifact_dir: str | None = None) -> None:
        self.artifact_dir = Path(artifact_dir or settings.model_artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.active_artifact_path = self.artifact_dir / "active_model.joblib"
        self.active_metadata_path = self.artifact_dir / "active_model_metadata.json"

    def has_active_model(self) -> bool:
        return self.active_artifact_path.exists()

    def save_bundle(self, bundle: dict, metadata: dict) -> tuple[str, str]:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        artifact_name = f"model_{timestamp}.joblib"
        artifact_path = self.artifact_dir / artifact_name

        joblib.dump(bundle, artifact_path)
        joblib.dump(bundle, self.active_artifact_path)

        metadata = {**metadata, "artifact_name": artifact_name, "saved_at": datetime.utcnow().isoformat()}
        self.active_metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return artifact_name, str(artifact_path)

    def _load_bundle(self) -> dict:
        if not self.active_artifact_path.exists():
            raise FileNotFoundError("No active model artifact found")
        return joblib.load(self.active_artifact_path)

    def _load_metadata(self) -> dict:
        if not self.active_metadata_path.exists():
            return {}
        return json.loads(self.active_metadata_path.read_text(encoding="utf-8"))

    def predict(self, features: dict[str, float]) -> ModelPrediction:
        if self.has_active_model():
            bundle = self._load_bundle()
            model = bundle["model"]
            columns = bundle.get("feature_columns", FEATURE_COLUMNS)
            payload = np.array([[float(features.get(col, 0.0)) for col in columns]], dtype=float)
            probability_bot = float(model.predict_proba(payload)[0][1])
            predicted_label = "bot" if probability_bot >= 0.5 else "human"
            confidence = float(max(probability_bot, 1.0 - probability_bot))
            risk_score = float(np.clip(probability_bot * 100.0, 0.0, 100.0))
            metadata = self._load_metadata()
            return ModelPrediction(
                predicted_label=predicted_label,
                probability_bot=probability_bot,
                confidence=confidence,
                risk_score=risk_score,
                model_version=metadata.get("version"),
            )

        heuristic_probability = self._heuristic_bot_probability(features)
        return ModelPrediction(
            predicted_label="bot" if heuristic_probability >= 0.5 else "human",
            probability_bot=heuristic_probability,
            confidence=max(heuristic_probability, 1.0 - heuristic_probability),
            risk_score=float(np.clip(heuristic_probability * 100.0, 0.0, 100.0)),
            model_version=None,
        )

    def _heuristic_bot_probability(self, features: dict[str, float]) -> float:
        speed_std = float(features.get("speed_std", 0.0))
        angle_std = float(features.get("angle_change_std", 0.0))
        entropy = float(features.get("event_type_entropy", 0.0))
        webdriver = float(features.get("webdriver_flag", 0.0))
        headless = float(features.get("headless_flag", 0.0))

        score = 0.15
        if speed_std < 25:
            score += 0.25
        if angle_std < 0.12:
            score += 0.2
        if entropy < 1.2:
            score += 0.15
        score += webdriver * 0.2 + headless * 0.15
        return float(np.clip(score, 0.01, 0.99))


model_manager = ModelManager()
