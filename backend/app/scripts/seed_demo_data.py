from __future__ import annotations

import argparse
import random
import uuid

from app.core.database import SessionLocal
from app.models.schemas import ClientFingerprint, EventPayload, EventsBatchRequest, SessionCreateRequest
from app.services.telemetry_service import TelemetryService


def random_fingerprint(headless: bool = False, webdriver: bool = False) -> ClientFingerprint:
    return ClientFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        language="pl-PL",
        timezone="Europe/Warsaw",
        screen_width=1920,
        screen_height=1080,
        viewport_width=1366,
        viewport_height=768,
        platform="Win32",
        pointer_type="mouse",
        webdriver=webdriver,
        headless_hint=headless,
        hardware_concurrency=8,
        device_memory=8,
    )


def generate_human_events(count: int, base_ts: int) -> list[EventPayload]:
    events: list[EventPayload] = []
    x, y = random.randint(100, 600), random.randint(100, 500)
    ts = base_ts

    for i in range(count):
        ts += random.randint(12, 48)
        x += random.randint(-30, 30)
        y += random.randint(-22, 22)
        x = max(10, min(1300, x))
        y = max(10, min(760, y))

        events.append(
            EventPayload(
                sequence_no=i + 1,
                event_type="mousemove",
                ts_ms=ts,
                x=float(x),
                y=float(y),
                pointer_type="mouse",
                in_viewport=True,
                payload={},
            )
        )

        if random.random() < 0.09:
            ts += random.randint(40, 220)
            events.append(
                EventPayload(
                    sequence_no=len(events) + 1,
                    event_type="click",
                    ts_ms=ts,
                    x=float(x),
                    y=float(y),
                    target_id=f"card-{random.randint(1, 5)}",
                    target_tag="button",
                    pointer_type="mouse",
                    in_viewport=True,
                    payload={"button": 0},
                )
            )

        if random.random() < 0.12:
            ts += random.randint(25, 90)
            events.append(
                EventPayload(
                    sequence_no=len(events) + 1,
                    event_type="scroll",
                    ts_ms=ts,
                    scroll_x=0,
                    scroll_y=float(random.randint(100, 600)),
                    pointer_type="mouse",
                    in_viewport=True,
                    payload={"deltaY": random.randint(-240, 240)},
                )
            )

    return events


def generate_bot_linear_events(count: int, base_ts: int) -> list[EventPayload]:
    events: list[EventPayload] = []
    ts = base_ts
    x, y = 100.0, 100.0

    for i in range(count):
        ts += 18
        x += 7.0
        y += 4.0
        events.append(
            EventPayload(
                sequence_no=i + 1,
                event_type="mousemove",
                ts_ms=ts,
                x=x,
                y=y,
                pointer_type="mouse",
                in_viewport=True,
            )
        )

        if i % 25 == 0:
            ts += 18
            events.append(
                EventPayload(
                    sequence_no=len(events) + 1,
                    event_type="click",
                    ts_ms=ts,
                    x=x,
                    y=y,
                    target_id="cta-buy",
                    target_tag="button",
                    pointer_type="mouse",
                    in_viewport=True,
                )
            )

    return events


def generate_bot_human_like_events(count: int, base_ts: int) -> list[EventPayload]:
    events: list[EventPayload] = []
    ts = base_ts
    x, y = 200.0, 250.0

    for i in range(count):
        ts += random.randint(8, 26)
        x += random.uniform(-12.0, 22.0)
        y += random.uniform(-9.0, 17.0)
        jitter_x = random.uniform(-1.5, 1.5)
        jitter_y = random.uniform(-1.5, 1.5)

        events.append(
            EventPayload(
                sequence_no=i + 1,
                event_type="mousemove",
                ts_ms=ts,
                x=x + jitter_x,
                y=y + jitter_y,
                pointer_type="mouse",
                in_viewport=True,
                payload={"synthetic": "bezier_jitter"},
            )
        )

        if random.random() < 0.07:
            ts += random.randint(15, 85)
            events.append(
                EventPayload(
                    sequence_no=len(events) + 1,
                    event_type="click",
                    ts_ms=ts,
                    x=x,
                    y=y,
                    target_id=f"menu-{random.randint(1, 3)}",
                    target_tag="a",
                    pointer_type="mouse",
                    in_viewport=True,
                )
            )

    return events


def seed(samples_per_class: int) -> None:
    db = SessionLocal()
    try:
        telemetry = TelemetryService(db)

        for _ in range(samples_per_class):
            session_payload = SessionCreateRequest(
                source="human_manual",
                client_fingerprint=random_fingerprint(headless=False, webdriver=False),
                environment={"scenario": "human_manual", "seed_id": str(uuid.uuid4())},
            )
            session = telemetry.create_session(session_payload)
            events = generate_human_events(count=220, base_ts=1000)
            telemetry.ingest_events(EventsBatchRequest(session_id=session.id, events=events))
            telemetry.label_session(session.id, "human")

        for _ in range(samples_per_class):
            session_payload = SessionCreateRequest(
                source="bot_linear",
                client_fingerprint=random_fingerprint(headless=True, webdriver=True),
                environment={"scenario": "bot_linear", "seed_id": str(uuid.uuid4())},
            )
            session = telemetry.create_session(session_payload)
            events = generate_bot_linear_events(count=220, base_ts=1000)
            telemetry.ingest_events(EventsBatchRequest(session_id=session.id, events=events))
            telemetry.label_session(session.id, "bot")

        for _ in range(samples_per_class):
            session_payload = SessionCreateRequest(
                source="bot_human_like",
                client_fingerprint=random_fingerprint(headless=True, webdriver=True),
                environment={"scenario": "bot_human_like", "seed_id": str(uuid.uuid4())},
            )
            session = telemetry.create_session(session_payload)
            events = generate_bot_human_like_events(count=220, base_ts=1000)
            telemetry.ingest_events(EventsBatchRequest(session_id=session.id, events=events))
            telemetry.label_session(session.id, "bot")

        print(f"Seed completed. Added {samples_per_class} human and {samples_per_class * 2} bot sessions")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo sessions and events")
    parser.add_argument("--samples-per-class", type=int, default=15)
    args = parser.parse_args()
    seed(args.samples_per_class)


if __name__ == "__main__":
    main()
