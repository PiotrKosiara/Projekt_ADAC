from __future__ import annotations

from collections import defaultdict

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import RawEvent, SessionRecord
from app.services.feature_engineering import FEATURE_COLUMNS, build_feature_vector


class TrainingDataService:
    def __init__(self, db: Session):
        self.db = db

    def build_training_dataframe(
        self,
        window_size: int = 120,
        stride: int = 80,
        min_events: int = 30,
    ) -> pd.DataFrame:
        stmt = select(SessionRecord).where(SessionRecord.true_label.in_(["human", "bot"]))
        sessions = list(self.db.execute(stmt).scalars().all())

        rows: list[dict] = []

        for session in sessions:
            events_stmt = (
                select(RawEvent)
                .where(RawEvent.session_id == session.id)
                .order_by(RawEvent.sequence_no.asc())
            )
            events = list(self.db.execute(events_stmt).scalars().all())
            if len(events) < min_events:
                continue

            merged_env = {
                **(session.client_fingerprint or {}),
                **(session.environment or {}),
            }

            start_indices = list(range(0, max(1, len(events) - window_size + 1), max(1, stride)))
            if not start_indices:
                start_indices = [0]

            for start in start_indices:
                window = events[start : start + window_size]
                if len(window) < min_events:
                    continue
                features = build_feature_vector(window, merged_env)
                rows.append(
                    {
                        **{column: features.get(column, 0.0) for column in FEATURE_COLUMNS},
                        "label": 1 if session.true_label == "bot" else 0,
                        "session_id": session.id,
                        "source": session.source,
                    }
                )

        if not rows:
            return pd.DataFrame(columns=[*FEATURE_COLUMNS, "label", "session_id", "source"])

        frame = pd.DataFrame(rows)
        frame = frame.fillna(0.0)
        return frame

    def group_rows_by_session(self, frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in frame.to_dict(orient="records"):
            grouped[row["session_id"]].append(row)
        return {key: pd.DataFrame(value) for key, value in grouped.items()}
