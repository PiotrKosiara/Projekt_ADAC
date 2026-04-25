from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.db_models import RawEvent


def export_replay(session_id: str, output_path: str) -> None:
    db = SessionLocal()
    try:
        stmt = (
            select(RawEvent)
            .where(RawEvent.session_id == session_id)
            .order_by(RawEvent.sequence_no.asc())
        )
        events = list(db.execute(stmt).scalars().all())
        if not events:
            raise RuntimeError(f"No events found for session {session_id}")

        replay = []
        prev_ts = None
        for event in events:
            if event.x is None or event.y is None:
                continue
            delay_ms = 20 if prev_ts is None else max(1, event.ts_ms - prev_ts)
            prev_ts = event.ts_ms
            replay.append(
                {
                    "x": event.x,
                    "y": event.y,
                    "delay_ms": delay_ms,
                    "click": event.event_type == "click",
                }
            )

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(replay, indent=2), encoding="utf-8")
        print(f"Replay exported to {output_path}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export session to replay JSON")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--output", default="../bot_runner/replay_sample.json")
    args = parser.parse_args()

    export_replay(args.session_id, args.output)


if __name__ == "__main__":
    main()
