from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.db_models import EnforcementAction, ModelVersion, Prediction


class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_prediction(self, session_id: str) -> Prediction | None:
        stmt = (
            select(Prediction)
            .where(Prediction.session_id == session_id)
            .order_by(Prediction.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def create_prediction(
        self,
        session_id: str,
        predicted_label: str,
        probability_bot: float,
        confidence: float,
        risk_score: float,
        feature_snapshot: dict,
        model_version_id: str | None,
    ) -> Prediction:
        prediction = Prediction(
            session_id=session_id,
            predicted_label=predicted_label,
            probability_bot=probability_bot,
            confidence=confidence,
            risk_score=risk_score,
            feature_snapshot=feature_snapshot,
            model_version_id=model_version_id,
        )
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def create_action(
        self,
        session_id: str,
        action: str,
        reason: str,
        prediction_id: str | None,
        action_metadata: dict | None = None,
    ) -> EnforcementAction:
        record = EnforcementAction(
            session_id=session_id,
            action=action,
            reason=reason,
            prediction_id=prediction_id,
            action_metadata=action_metadata or {},
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest_action(self, session_id: str) -> EnforcementAction | None:
        stmt = (
            select(EnforcementAction)
            .where(EnforcementAction.session_id == session_id)
            .order_by(EnforcementAction.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_active_model(self) -> ModelVersion | None:
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.is_active.is_(True))
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def upsert_model_version(
        self,
        name: str,
        version: str,
        algorithm: str,
        metrics: dict,
        artifact_path: str,
        model_metadata: dict,
    ) -> ModelVersion:
        self.db.execute(update(ModelVersion).values(is_active=False))
        model_version = ModelVersion(
            name=name,
            version=version,
            algorithm=algorithm,
            metrics=metrics,
            artifact_path=artifact_path,
            model_metadata=model_metadata,
            is_active=True,
        )
        self.db.add(model_version)
        self.db.commit()
        self.db.refresh(model_version)
        return model_version
