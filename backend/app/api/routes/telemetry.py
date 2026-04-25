from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import EventsBatchRequest, EventsBatchResponse
from app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/events", tags=["telemetry"])


@router.post("/batch", response_model=EventsBatchResponse)
def ingest_events_batch(payload: EventsBatchRequest, db: Session = Depends(get_db)):
    service = TelemetryService(db)
    try:
        accepted = service.ingest_events(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return EventsBatchResponse(accepted=accepted, session_id=payload.session_id)
