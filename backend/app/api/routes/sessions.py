from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import LabelSessionRequest, SessionCreateRequest, SessionCreateResponse, SessionStatusResponse
from app.repositories.prediction_repo import PredictionRepository
from app.repositories.session_repo import SessionRepository
from app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse)
def create_session(payload: SessionCreateRequest, db: Session = Depends(get_db)):
    service = TelemetryService(db)
    session = service.create_session(payload)
    return SessionCreateResponse(session_id=session.id, created_at=session.created_at)


@router.post("/{session_id}/label", response_model=SessionStatusResponse)
def label_session(session_id: str, payload: LabelSessionRequest, db: Session = Depends(get_db)):
    service = TelemetryService(db)
    try:
        session = service.label_session(session_id, payload.true_label)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_repo = SessionRepository(db)
    prediction_repo = PredictionRepository(db)
    event_count = session_repo.count_events(session_id)
    last_action = prediction_repo.get_latest_action(session_id)

    return SessionStatusResponse(
        session_id=session.id,
        source=session.source,
        true_label=session.true_label,
        status=session.status,
        event_count=event_count,
        last_action=last_action.action if last_action else None,
        created_at=session.created_at,
    )


@router.get("/{session_id}", response_model=SessionStatusResponse)
def get_session_status(session_id: str, db: Session = Depends(get_db)):
    session_repo = SessionRepository(db)
    prediction_repo = PredictionRepository(db)

    session = session_repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    event_count = session_repo.count_events(session_id)
    last_action = prediction_repo.get_latest_action(session_id)

    return SessionStatusResponse(
        session_id=session.id,
        source=session.source,
        true_label=session.true_label,
        status=session.status,
        event_count=event_count,
        last_action=last_action.action if last_action else None,
        created_at=session.created_at,
    )
