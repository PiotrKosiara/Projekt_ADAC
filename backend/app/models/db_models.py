import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(64), default="unknown")
    true_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="collecting")

    client_fingerprint: Mapped[dict] = mapped_column(JSON, default=dict)
    environment: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    raw_events: Mapped[list["RawEvent"]] = relationship(
        "RawEvent", back_populates="session", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction", back_populates="session", cascade="all, delete-orphan"
    )
    enforcement_actions: Mapped[list["EnforcementAction"]] = relationship(
        "EnforcementAction", back_populates="session", cascade="all, delete-orphan"
    )


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, index=True)

    event_type: Mapped[str] = mapped_column(String(64), index=True)
    ts_ms: Mapped[int] = mapped_column(BigInteger, index=True)

    x: Mapped[float | None] = mapped_column(Float, nullable=True)
    y: Mapped[float | None] = mapped_column(Float, nullable=True)
    scroll_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    scroll_y: Mapped[float | None] = mapped_column(Float, nullable=True)

    target_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    target_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_class: Mapped[str | None] = mapped_column(String(256), nullable=True)

    pointer_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    in_viewport: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="raw_events")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    algorithm: Mapped[str] = mapped_column(String(128))
    feature_set_version: Mapped[str] = mapped_column(String(64), default="v1")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_path: Mapped[str] = mapped_column(Text)
    model_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    predictions: Mapped[list["Prediction"]] = relationship("Prediction", back_populates="model_version")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    model_version_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("model_versions.id"), nullable=True
    )

    predicted_label: Mapped[str] = mapped_column(String(16), index=True)
    probability_bot: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    feature_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="predictions")
    model_version: Mapped[ModelVersion | None] = relationship("ModelVersion", back_populates="predictions")
    actions: Mapped[list["EnforcementAction"]] = relationship(
        "EnforcementAction", back_populates="prediction", cascade="all, delete-orphan"
    )


class EnforcementAction(Base):
    __tablename__ = "enforcement_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    prediction_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("predictions.id"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(Text)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    action_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="enforcement_actions")
    prediction: Mapped[Prediction | None] = relationship("Prediction", back_populates="actions")
