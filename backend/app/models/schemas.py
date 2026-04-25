from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


EventType = Literal[
    "mousemove",
    "click",
    "scroll",
    "focus",
    "blur",
    "viewport_enter",
    "viewport_leave",
]


class ClientFingerprint(BaseModel):
    user_agent: str
    language: str
    timezone: str
    screen_width: int
    screen_height: int
    viewport_width: int
    viewport_height: int
    platform: str | None = None
    pointer_type: str | None = None
    webdriver: bool | None = None
    headless_hint: bool | None = None
    hardware_concurrency: int | None = None
    device_memory: float | None = None


class SessionCreateRequest(BaseModel):
    source: str = "unknown"
    client_fingerprint: ClientFingerprint
    environment: dict[str, Any] = Field(default_factory=dict)


class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: datetime


class EventPayload(BaseModel):
    sequence_no: int | None = None
    event_type: EventType
    ts_ms: int

    x: float | None = None
    y: float | None = None
    scroll_x: float | None = None
    scroll_y: float | None = None

    target_id: str | None = None
    target_tag: str | None = None
    target_class: str | None = None

    pointer_type: str | None = None
    in_viewport: bool | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventsBatchRequest(BaseModel):
    session_id: str
    events: list[EventPayload]


class EventsBatchResponse(BaseModel):
    accepted: int
    session_id: str


class LabelSessionRequest(BaseModel):
    true_label: Literal["human", "bot"]


class SessionStatusResponse(BaseModel):
    session_id: str
    source: str
    true_label: str | None
    status: str
    event_count: int
    last_action: str | None
    created_at: datetime


class PredictionResponse(BaseModel):
    session_id: str
    predicted_label: Literal["human", "bot"]
    probability_bot: float
    confidence: float
    risk_score: float
    model_version: str | None
    enforcement_action: Literal["allow", "observe", "throttle", "challenge", "block"]
    enforcement_reason: str
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
