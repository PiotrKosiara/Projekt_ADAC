from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.db_models import RawEvent, SessionRecord
from app.models.schemas import EventPayload, SessionCreateRequest


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, payload: SessionCreateRequest) -> SessionRecord:
        session = SessionRecord(
            source=payload.source,
            client_fingerprint=payload.client_fingerprint.model_dump(),
            environment=payload.environment,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self.db.get(SessionRecord, session_id)

    def set_label(self, session_id: str, label: str) -> SessionRecord | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        session.true_label = label
        session.status = "labeled"
        self.db.commit()
        self.db.refresh(session)
        return session

    def count_events(self, session_id: str) -> int:
        stmt = select(func.count(RawEvent.id)).where(RawEvent.session_id == session_id)
        return int(self.db.execute(stmt).scalar_one())

    def get_events(self, session_id: str, limit: int | None = None) -> list[RawEvent]:
        stmt = select(RawEvent).where(RawEvent.session_id == session_id).order_by(RawEvent.sequence_no.asc())
        if limit:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def append_events(self, session_id: str, events: list[EventPayload]) -> int:
        current_count = self.count_events(session_id)
        records: list[RawEvent] = []

        for idx, event in enumerate(events, start=1):
            sequence_no = event.sequence_no if event.sequence_no is not None else current_count + idx
            records.append(
                RawEvent(
                    session_id=session_id,
                    sequence_no=sequence_no,
                    event_type=event.event_type,
                    ts_ms=event.ts_ms,
                    x=event.x,
                    y=event.y,
                    scroll_x=event.scroll_x,
                    scroll_y=event.scroll_y,
                    target_id=event.target_id,
                    target_tag=event.target_tag,
                    target_class=event.target_class,
                    pointer_type=event.pointer_type,
                    in_viewport=event.in_viewport,
                    payload=event.payload,
                )
            )

        self.db.add_all(records)
        self.db.commit()
        return len(records)
