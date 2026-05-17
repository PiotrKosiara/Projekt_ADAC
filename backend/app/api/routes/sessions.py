import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import RawEvent, SessionRecord
from app.models.schemas import (
    HumanBehaviorProfileResponse,
    LabelSessionRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionStatusResponse,
)
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


@router.get("/human-behavior-profile", response_model=HumanBehaviorProfileResponse)
def get_human_behavior_profile(db: Session = Depends(get_db)):
    sessions_stmt = select(SessionRecord).where(SessionRecord.true_label == "human")
    sessions = list(db.execute(sessions_stmt).scalars().all())

    if not sessions:
        raise HTTPException(status_code=404, detail="No human sessions found")

    move_steps: list[float] = []
    move_dts: list[float] = []
    speeds: list[float] = []
    click_intervals: list[float] = []
    scroll_deltas: list[float] = []
    pauses: list[float] = []

    human_sessions = 0
    human_events = 0

    for session in sessions:
        events_stmt = (
            select(RawEvent)
            .where(RawEvent.session_id == session.id)
            .order_by(RawEvent.sequence_no.asc())
        )
        events = list(db.execute(events_stmt).scalars().all())
        if len(events) < 20:
            continue

        human_sessions += 1
        human_events += len(events)

        last_event_ts: int | None = None
        last_click_ts: int | None = None
        last_move: tuple[float, float, int] | None = None

        for event in events:
            if last_event_ts is not None:
                gap_ms = event.ts_ms - last_event_ts
                if 160 <= gap_ms <= 6000:
                    pauses.append(float(gap_ms))
            last_event_ts = event.ts_ms

            if event.event_type == "scroll" and event.scroll_y is not None:
                scroll_deltas.append(abs(float(event.scroll_y)))

            if event.event_type == "click":
                if last_click_ts is not None:
                    click_gap = event.ts_ms - last_click_ts
                    if 30 <= click_gap <= 15000:
                        click_intervals.append(float(click_gap))
                last_click_ts = event.ts_ms

            if event.event_type == "mousemove" and event.x is not None and event.y is not None:
                if last_move is not None:
                    dx = float(event.x) - last_move[0]
                    dy = float(event.y) - last_move[1]
                    dist = math.hypot(dx, dy)
                    dt_ms = event.ts_ms - last_move[2]
                    if 0 < dt_ms <= 1200 and 0 < dist <= 1200:
                        move_steps.append(float(dist))
                        move_dts.append(float(dt_ms))
                        speeds.append(float(dist) / (float(dt_ms) / 1000.0))
                last_move = (float(event.x), float(event.y), event.ts_ms)

    if human_sessions == 0:
        raise HTTPException(status_code=404, detail="No human sessions with enough events")

    total_gaps = len(pauses) + len(move_dts) + len(click_intervals)
    pause_prob = (len(pauses) / total_gaps) if total_gaps else 0.0

    return HumanBehaviorProfileResponse(
        human_sessions=human_sessions,
        human_events=human_events,
        move_step_mean_px=_mean(move_steps, 18.0),
        move_step_std_px=_std(move_steps, 9.0),
        move_dt_mean_ms=_mean(move_dts, 16.0),
        move_dt_p90_ms=_p90(move_dts, 30.0),
        speed_mean_px_s=_mean(speeds, 950.0),
        speed_p90_px_s=_p90(speeds, 2400.0),
        click_interval_mean_ms=_mean(click_intervals, 680.0),
        click_interval_p90_ms=_p90(click_intervals, 1600.0),
        scroll_delta_mean=_mean(scroll_deltas, 260.0),
        scroll_delta_p90=_p90(scroll_deltas, 600.0),
        pause_prob=max(0.02, min(0.35, pause_prob)),
        pause_mean_ms=_mean(pauses, 280.0),
        pause_p90_ms=_p90(pauses, 720.0),
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


def _mean(values: list[float], default: float) -> float:
    if not values:
        return float(default)
    return float(sum(values) / len(values))


def _std(values: list[float], default: float) -> float:
    if len(values) < 2:
        return float(default)
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return float(math.sqrt(variance))


def _p90(values: list[float], default: float) -> float:
    if not values:
        return float(default)
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * 0.9))
    idx = max(0, min(len(ordered) - 1, idx))
    return float(ordered[idx])
