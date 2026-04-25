from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import PredictionResponse
from app.repositories.prediction_repo import PredictionRepository
from app.repositories.session_repo import SessionRepository
from app.services.model_manager import model_manager
from app.services.policy_engine import PolicyEngine
from app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="", tags=["predictions"])
policy_engine = PolicyEngine()


@router.post("/predict/{session_id}", response_model=PredictionResponse)
def predict_session(session_id: str, db: Session = Depends(get_db)):
    telemetry_service = TelemetryService(db)
    session_repo = SessionRepository(db)
    prediction_repo = PredictionRepository(db)

    session = session_repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        features = telemetry_service.build_features_for_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prediction = model_manager.predict(features)
    decision = policy_engine.decide(prediction.risk_score)

    active_model = prediction_repo.get_active_model()

    prediction_record = prediction_repo.create_prediction(
        session_id=session_id,
        predicted_label=prediction.predicted_label,
        probability_bot=prediction.probability_bot,
        confidence=prediction.confidence,
        risk_score=prediction.risk_score,
        feature_snapshot=features,
        model_version_id=active_model.id if active_model else None,
    )

    action_record = prediction_repo.create_action(
        session_id=session_id,
        action=decision.action,
        reason=decision.reason,
        prediction_id=prediction_record.id,
        action_metadata={"risk_score": prediction.risk_score},
    )

    session.status = "protected"
    db.commit()

    return PredictionResponse(
        session_id=session_id,
        predicted_label=prediction.predicted_label,
        probability_bot=prediction.probability_bot,
        confidence=prediction.confidence,
        risk_score=prediction.risk_score,
        model_version=prediction.model_version,
        enforcement_action=action_record.action,
        enforcement_reason=action_record.reason,
        created_at=prediction_record.created_at,
    )


@router.get("/predictions/{session_id}", response_model=PredictionResponse)
def get_latest_prediction(session_id: str, db: Session = Depends(get_db)):
    prediction_repo = PredictionRepository(db)
    prediction = prediction_repo.get_latest_prediction(session_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail=f"No prediction found for session {session_id}")

    action = prediction_repo.get_latest_action(session_id)

    return PredictionResponse(
        session_id=session_id,
        predicted_label=prediction.predicted_label,
        probability_bot=prediction.probability_bot,
        confidence=prediction.confidence,
        risk_score=prediction.risk_score,
        model_version=prediction.model_version.version if prediction.model_version else None,
        enforcement_action=action.action if action else "observe",
        enforcement_reason=action.reason if action else "Brak decyzji enforcement",
        created_at=prediction.created_at,
    )
