from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.schemas import EventsBatchRequest, SessionCreateRequest
from app.repositories.session_repo import SessionRepository
from app.services.feature_engineering import build_feature_vector


class TelemetryService:
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)

    def create_session(self, payload: SessionCreateRequest):
        return self.session_repo.create_session(payload)

    def ingest_events(self, payload: EventsBatchRequest) -> int:
        session = self.session_repo.get_session(payload.session_id)
        if session is None:
            raise ValueError(f"Session {payload.session_id} does not exist")

        accepted = self.session_repo.append_events(payload.session_id, payload.events)

        if settings.export_raw_events:
            self._export_raw_events(payload.session_id, payload.events)

        return accepted

    def label_session(self, session_id: str, label: str):
        session = self.session_repo.set_label(session_id, label)
        if session is None:
            raise ValueError(f"Session {session_id} does not exist")
        return session

    def build_features_for_session(self, session_id: str, window_size: int = 120) -> dict[str, float]:
        session = self.session_repo.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} does not exist")

        events = self.session_repo.get_events(session_id=session_id)
        if not events:
            raise ValueError("No events found for session")

        sliced = events[-window_size:]
        merged_environment = {
            **(session.client_fingerprint or {}),
            **(session.environment or {}),
        }
        return build_feature_vector(sliced, merged_environment)

    def _export_raw_events(self, session_id: str, events) -> None:
        target_dir = Path(settings.raw_events_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        day = datetime.utcnow().strftime("%Y-%m-%d")
        output_path = target_dir / f"events_{day}.jsonl"

        with output_path.open("a", encoding="utf-8") as out:
            for event in events:
                row = {
                    "session_id": session_id,
                    "event_type": event.event_type,
                    "ts_ms": event.ts_ms,
                    "x": event.x,
                    "y": event.y,
                    "scroll_x": event.scroll_x,
                    "scroll_y": event.scroll_y,
                    "target_id": event.target_id,
                    "target_tag": event.target_tag,
                    "target_class": event.target_class,
                    "pointer_type": event.pointer_type,
                    "in_viewport": event.in_viewport,
                    "payload": event.payload,
                }
                out.write(json.dumps(row, ensure_ascii=True) + "\n")
