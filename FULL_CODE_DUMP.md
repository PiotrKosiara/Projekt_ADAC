# FULL CODE DUMP

## .env.example

`$lang
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_DB=behavioral_biometrics
POSTGRES_HOST=db
POSTGRES_PORT=5432

DATABASE_URL=postgresql+psycopg2://app:app@db:5432/behavioral_biometrics

MODEL_ARTIFACT_DIR=/app/models_artifacts
RAW_EVENTS_DIR=/app/data/raw
EXPORT_RAW_EVENTS=true
API_CORS_ORIGINS=http://localhost:5173

VITE_API_BASE_URL=http://localhost:8000/api/v1
BOT_TARGET_URL=http://frontend:5173

```

## .gitignore

`$lang
.env
__pycache__/
*.pyc
.pytest_cache/
backend/models_artifacts/*.joblib
backend/models_artifacts/reports/
backend/data/raw/*.jsonl
frontend/node_modules/
frontend/dist/
bot_runner/.pytest_cache/

```

## docker-compose.yml

`$lang
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    container_name: biometrics_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 8

  backend:
    build:
      context: ./backend
    container_name: biometrics_backend
    restart: unless-stopped
    env_file:
      - .env
    environment:
      DATABASE_URL: ${DATABASE_URL}
      MODEL_ARTIFACT_DIR: ${MODEL_ARTIFACT_DIR}
      RAW_EVENTS_DIR: ${RAW_EVENTS_DIR}
      EXPORT_RAW_EVENTS: ${EXPORT_RAW_EVENTS}
      API_CORS_ORIGINS: ${API_CORS_ORIGINS}
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app:/app/app
      - ./backend/models_artifacts:/app/models_artifacts
      - ./backend/data:/app/data

  frontend:
    build:
      context: ./frontend
    container_name: biometrics_frontend
    restart: unless-stopped
    environment:
      VITE_API_BASE_URL: ${VITE_API_BASE_URL}
    depends_on:
      - backend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules

  bot_runner:
    build:
      context: ./bot_runner
    container_name: biometrics_bot_runner
    env_file:
      - .env
    environment:
      BOT_TARGET_URL: ${BOT_TARGET_URL}
    depends_on:
      - frontend
      - backend
    volumes:
      - ./bot_runner:/app
    command: ["sleep", "infinity"]

volumes:
  pgdata:

```

## README.md

`$lang
# Bot czy człowiek? Behawioralna biometria ruchu myszy - MVP

MVP demonstruje pełny pipeline ochrony aplikacji webowej:

1. Frontend zbiera telemetrykę (mousemove, click, scroll, focus/blur, viewport enter/leave + fingerprint).
2. Backend zapisuje sesję i eventy do PostgreSQL.
3. Feature builder liczy cechy z krótkich okien zachowania.
4. Model ML klasyfikuje `human` vs `bot` i wylicza `risk_score 0-100`.
5. Policy engine zwraca akcję: `allow | observe | throttle | challenge | block`.

## Decyzje technologiczne

- Frontend: **Vite + React + TypeScript**
- Backend API: **FastAPI + SQLAlchemy**
- Baza: **PostgreSQL**
- ML: **pandas + scikit-learn**
- Bot runner: **Playwright (Python)**
- Uruchomienie: **Docker Compose**

## Architektura

- `frontend`: testbed UI + telemetry collector i batch upload.
- `backend/app/api`: endpointy REST do sesji, eventów, predykcji.
- `backend/app/services/feature_engineering.py`: cechy behawioralne z okien czasowych.
- `backend/app/ml/train.py`: trening 2 modeli (baseline + mocniejszy) i wybór najlepszego.
- `backend/app/ml/evaluate.py`: raport metryk + detection delay + unseen bots recall.
- `backend/app/services/policy_engine.py`: mapowanie risk score -> akcja enforcement.
- `bot_runner`: scenariusze botów i replay.

## Schemat danych

Tabele PostgreSQL:

- `sessions`
- `raw_events`
- `predictions`
- `model_versions`
- `enforcement_actions`

## REST API (MVP)

- `POST /api/v1/sessions` - start sesji
- `POST /api/v1/events/batch` - batch eventów
- `POST /api/v1/sessions/{session_id}/label` - etykietowanie `human|bot`
- `POST /api/v1/predict/{session_id}` - predykcja i enforcement
- `GET /api/v1/predictions/{session_id}` - ostatni wynik
- `GET /api/v1/sessions/{session_id}` - status sesji
- `GET /api/v1/health` - healthcheck

## Jak uruchomić

1. Skopiuj konfigurację:

```bash
cp .env.example .env
```

2. Uruchom środowisko:

```bash
docker compose up -d --build
```

3. Otwórz frontend:

- http://localhost:5173

4. (Opcjonalnie) seed danych treningowych:

```bash
docker compose exec backend python -m app.scripts.seed_demo_data --samples-per-class 20
```

5. Trening modelu:

```bash
docker compose exec backend python -m app.ml.train --window-size 120 --stride 80
```

6. Ewaluacja modelu:

```bash
docker compose exec backend python -m app.ml.evaluate --window-size 120 --stride 80
```

7. Bot runner - przykłady:

```bash
# Bot liniowy
docker compose exec bot_runner python main.py --scenario linear --sessions 10

# Bot human-like
docker compose exec bot_runner python main.py --scenario human_like --sessions 10

# Replay
docker compose exec bot_runner python main.py --scenario replay --sessions 5 --replay-file replay_sample.json
```

8. Testy jednostkowe:

```bash
docker compose exec backend pytest
```

## Uproszczenia MVP (świadomie)

- Brak asynchronicznej kolejki przetwarzania (wszystko synchronicznie w API).
- Brak dedykowanego serwisu modelowego (inferencja w backendzie API).
- Brak produkcyjnego anti-evasion i anti-tampering telemetry (demo-level).
- Blokowanie realizowane logiką sesyjną (nie na poziomie WAF / IP firewall).

## Kolejne kroki (roadmap)

1. Dodać model sekwencyjny (np. Transformer/RNN) na surowych trajektoriach.
2. Dodać online learning i automatyczny retraining pipeline.
3. Rozszerzyć polityki o denylistę, reputację IP i device graph.
4. Dodać dashboard operacyjny (analiza sesji, drift cech, alerty).
5. Dodać anti-replay hardening (nonce, dynamic challenge, JS integrity checks).
6. Zastąpić heurystyczne cechy celu kliknięcia instrumentacją DOM bbox.

```

## backend\Dockerfile

`$lang
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY models_artifacts /app/models_artifacts
COPY data /app/data
COPY pytest.ini /app/pytest.ini

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

```

## backend\pytest.ini

`$lang
[pytest]
pythonpath = .
testpaths = app/tests

```

## backend\requirements.txt

`$lang
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.36
psycopg2-binary==2.9.9
pydantic-settings==2.6.1
python-dotenv==1.0.1
pandas==2.2.3
numpy==2.1.1
scikit-learn==1.5.2
joblib==1.4.2
matplotlib==3.9.2
seaborn==0.13.2
pytest==8.3.3

```

## backend\app\main.py

`$lang
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.predictions import router as predictions_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.telemetry import router as telemetry_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title=settings.app_name)

origins = [origin.strip() for origin in settings.api_cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(sessions_router, prefix=settings.api_prefix)
app.include_router(telemetry_router, prefix=settings.api_prefix)
app.include_router(predictions_router, prefix=settings.api_prefix)

```

## backend\app\__init__.py

`$lang


```

## backend\app\api\deps.py

`$lang
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import get_db


def db_dependency() -> Generator[Session, None, None]:
    yield from get_db()

```

## backend\app\api\__init__.py

`$lang


```

## backend\app\api\routes\health.py

`$lang
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

```

## backend\app\api\routes\predictions.py

`$lang
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import PredictionResponse
from app.repositories.prediction_repo import PredictionRepository
from app.repositories.session_repo import SessionRepository
from app.services.model_manager import model_manager
from app.services.policy_engine import PolicyEngine
from app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="", tags=["predictions"])
policy_engine = PolicyEngine()


@router.post("/predict/{session_id}", response_model=PredictionResponse)
def predict_session(session_id: str, db: Session = Depends(get_db)):
    telemetry_service = TelemetryService(db)
    session_repo = SessionRepository(db)
    prediction_repo = PredictionRepository(db)

    session = session_repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        features = telemetry_service.build_features_for_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prediction = model_manager.predict(features)
    decision = policy_engine.decide(prediction.risk_score)

    active_model = prediction_repo.get_active_model()

    prediction_record = prediction_repo.create_prediction(
        session_id=session_id,
        predicted_label=prediction.predicted_label,
        probability_bot=prediction.probability_bot,
        confidence=prediction.confidence,
        risk_score=prediction.risk_score,
        feature_snapshot=features,
        model_version_id=active_model.id if active_model else None,
    )

    action_record = prediction_repo.create_action(
        session_id=session_id,
        action=decision.action,
        reason=decision.reason,
        prediction_id=prediction_record.id,
        action_metadata={"risk_score": prediction.risk_score},
    )

    session.status = "protected"
    db.commit()

    return PredictionResponse(
        session_id=session_id,
        predicted_label=prediction.predicted_label,
        probability_bot=prediction.probability_bot,
        confidence=prediction.confidence,
        risk_score=prediction.risk_score,
        model_version=prediction.model_version,
        enforcement_action=action_record.action,
        enforcement_reason=action_record.reason,
        created_at=prediction_record.created_at,
    )


@router.get("/predictions/{session_id}", response_model=PredictionResponse)
def get_latest_prediction(session_id: str, db: Session = Depends(get_db)):
    prediction_repo = PredictionRepository(db)
    prediction = prediction_repo.get_latest_prediction(session_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail=f"No prediction found for session {session_id}")

    action = prediction_repo.get_latest_action(session_id)

    return PredictionResponse(
        session_id=session_id,
        predicted_label=prediction.predicted_label,
        probability_bot=prediction.probability_bot,
        confidence=prediction.confidence,
        risk_score=prediction.risk_score,
        model_version=prediction.model_version.version if prediction.model_version else None,
        enforcement_action=action.action if action else "observe",
        enforcement_reason=action.reason if action else "Brak decyzji enforcement",
        created_at=prediction.created_at,
    )

```

## backend\app\api\routes\sessions.py

`$lang
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

```

## backend\app\api\routes\telemetry.py

`$lang
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

```

## backend\app\api\routes\__init__.py

`$lang


```

## backend\app\core\config.py

`$lang
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Bot or Human Behavioral Biometrics"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    postgres_user: str = "app"
    postgres_password: str = "app"
    postgres_db: str = "behavioral_biometrics"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    database_url: str = "postgresql+psycopg2://app:app@localhost:5432/behavioral_biometrics"

    model_artifact_dir: str = "./models_artifacts"
    export_raw_events: bool = True
    raw_events_dir: str = "./data/raw"

    api_cors_origins: str = "http://localhost:5173"


settings = Settings()

```

## backend\app\core\database.py

`$lang
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

```

## backend\app\core\logging.py

`$lang
import logging

from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

```

## backend\app\ml\evaluate.py

`$lang
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from sqlalchemy import select

from app.core.database import SessionLocal
from app.ml.metrics import compute_metrics, save_confusion_matrix_plot, save_report, save_roc_plot
from app.models.db_models import RawEvent, SessionRecord
from app.services.feature_engineering import FEATURE_COLUMNS, build_feature_vector
from app.services.model_manager import model_manager
from app.services.training_data_service import TrainingDataService


def evaluate() -> None:
    parser = argparse.ArgumentParser(description="Evaluate active model")
    parser.add_argument("--window-size", type=int, default=120)
    parser.add_argument("--stride", type=int, default=80)
    parser.add_argument("--risk-threshold", type=float, default=70.0)
    args = parser.parse_args()

    if not model_manager.has_active_model():
        raise RuntimeError("No active model. Train model first.")

    db = SessionLocal()
    try:
        training_data_service = TrainingDataService(db)
        frame = training_data_service.build_training_dataframe(
            window_size=args.window_size,
            stride=args.stride,
        )

        if frame.empty:
            raise RuntimeError("No labeled data available for evaluation")

        bundle = model_manager._load_bundle()
        model = bundle["model"]

        X = frame[FEATURE_COLUMNS].astype(float).to_numpy()
        y_true = frame["label"].astype(int).to_numpy()
        y_prob = model.predict_proba(X)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        metrics = compute_metrics(y_true, y_pred, y_prob)
        detection_delay = _compute_detection_delay(
            db,
            model,
            window_size=args.window_size,
            stride=max(5, args.stride // 2),
            risk_threshold=args.risk_threshold,
        )
        unseen_bot_recall = _compute_unseen_bot_recall(db, model, window_size=args.window_size)

        report = {
            "metrics": metrics,
            "detection_delay": detection_delay,
            "unseen_bot_recall": unseen_bot_recall,
            "samples": int(len(frame)),
            "sessions": int(frame["session_id"].nunique()),
        }

        report_dir = Path("./models_artifacts/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        save_confusion_matrix_plot(y_true, y_pred, str(report_dir / "eval_confusion_matrix.png"))
        save_roc_plot(y_true, y_prob, str(report_dir / "eval_roc.png"))
        save_report(report, str(report_dir / "evaluation_report.json"))

        print("Evaluation report saved to models_artifacts/reports/evaluation_report.json")
        print(report)
    finally:
        db.close()


def _compute_detection_delay(db, model, window_size: int, stride: int, risk_threshold: float) -> dict:
    bot_sessions_stmt = select(SessionRecord).where(SessionRecord.true_label == "bot")
    bot_sessions = list(db.execute(bot_sessions_stmt).scalars().all())

    delays = []

    for session in bot_sessions:
        events_stmt = (
            select(RawEvent)
            .where(RawEvent.session_id == session.id)
            .order_by(RawEvent.sequence_no.asc())
        )
        events = list(db.execute(events_stmt).scalars().all())
        if len(events) < 20:
            continue

        merged_env = {**(session.client_fingerprint or {}), **(session.environment or {})}

        detected_at = None
        for end_idx in range(window_size, len(events) + 1, stride):
            window = events[max(0, end_idx - window_size) : end_idx]
            features = build_feature_vector(window, merged_env)
            X = np.array([[features.get(col, 0.0) for col in FEATURE_COLUMNS]], dtype=float)
            probability_bot = float(model.predict_proba(X)[0][1])
            if probability_bot * 100.0 >= risk_threshold:
                detected_at = end_idx
                break

        delays.append(detected_at if detected_at is not None else len(events))

    if not delays:
        return {"avg_events_to_detect": None, "median_events_to_detect": None}

    return {
        "avg_events_to_detect": float(np.mean(delays)),
        "median_events_to_detect": float(np.median(delays)),
        "count": int(len(delays)),
    }


def _compute_unseen_bot_recall(db, model, window_size: int) -> dict:
    metadata = model_manager._load_metadata()
    seen_sources = set(metadata.get("seen_bot_sources", []))

    unseen_stmt = select(SessionRecord).where(SessionRecord.true_label == "bot")
    all_bots = list(db.execute(unseen_stmt).scalars().all())
    unseen_bots = [session for session in all_bots if session.source not in seen_sources]

    if not unseen_bots:
        return {"recall": None, "count": 0}

    hits = 0
    total = 0

    for session in unseen_bots:
        events_stmt = (
            select(RawEvent)
            .where(RawEvent.session_id == session.id)
            .order_by(RawEvent.sequence_no.asc())
        )
        events = list(db.execute(events_stmt).scalars().all())
        if len(events) < 20:
            continue

        merged_env = {**(session.client_fingerprint or {}), **(session.environment or {})}
        window = events[-window_size:]
        features = build_feature_vector(window, merged_env)
        X = np.array([[features.get(col, 0.0) for col in FEATURE_COLUMNS]], dtype=float)
        prob_bot = float(model.predict_proba(X)[0][1])
        prediction = 1 if prob_bot >= 0.5 else 0

        hits += int(prediction == 1)
        total += 1

    recall = hits / total if total else None
    return {"recall": recall, "count": total}


if __name__ == "__main__":
    evaluate()

```

## backend\app\ml\metrics.py

`$lang
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    auc,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def compute_metrics(y_true, y_pred, y_prob) -> dict:
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    y_prob_arr = np.asarray(y_prob)

    tn, fp, fn, tp = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1]).ravel()

    metrics = {
        "precision": float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        "recall": float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        "f1": float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true_arr, y_prob_arr)) if len(np.unique(y_true_arr)) > 1 else 0.0,
        "false_positive_rate_human": float(fp / max(fp + tn, 1)),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }
    return metrics


def save_confusion_matrix_plot(y_true, y_pred, output_path: str) -> None:
    cm = confusion_matrix(np.asarray(y_true), np.asarray(y_pred), labels=[0, 1])
    figure, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax)
    ax.set_xlabel("Predykcja")
    ax.set_ylabel("Rzeczywista etykieta")
    ax.set_xticklabels(["human", "bot"])
    ax.set_yticklabels(["human", "bot"])
    ax.set_title("Confusion matrix")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path)
    plt.close(figure)


def save_roc_plot(y_true, y_prob, output_path: str) -> None:
    y_true_arr = np.asarray(y_true)
    y_prob_arr = np.asarray(y_prob)

    if len(np.unique(y_true_arr)) < 2:
        return

    fpr, tpr, _ = roc_curve(y_true_arr, y_prob_arr)
    roc_auc = auc(fpr, tpr)

    figure, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, label=f"ROC AUC = {roc_auc:.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC curve")
    ax.legend(loc="lower right")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path)
    plt.close(figure)


def save_report(report: dict, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

```

## backend\app\ml\train.py

`$lang
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.core.database import SessionLocal
from app.ml.metrics import compute_metrics, save_confusion_matrix_plot, save_roc_plot
from app.repositories.prediction_repo import PredictionRepository
from app.services.feature_engineering import FEATURE_COLUMNS
from app.services.model_manager import model_manager
from app.services.training_data_service import TrainingDataService


def train() -> None:
    parser = argparse.ArgumentParser(description="Train human-vs-bot model")
    parser.add_argument("--window-size", type=int, default=120)
    parser.add_argument("--stride", type=int, default=80)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        training_data_service = TrainingDataService(db)
        frame = training_data_service.build_training_dataframe(
            window_size=args.window_size,
            stride=args.stride,
        )

        if frame.empty:
            raise RuntimeError("No labeled data available. Add labels and collect events first.")

        X = frame[FEATURE_COLUMNS].astype(float).to_numpy()
        y = frame["label"].astype(int).to_numpy()
        groups = frame["session_id"].astype(str).to_numpy()

        if len(np.unique(y)) < 2:
            raise RuntimeError("Training requires both classes: human and bot")

        splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        train_idx, test_idx = next(splitter.split(X, y, groups=groups))

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        models = {
            "logistic_regression": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
                ]
            ),
            "hist_gradient_boosting": HistGradientBoostingClassifier(max_depth=6, random_state=42),
        }

        best_name = None
        best_model = None
        best_metrics = None
        best_proba = None
        best_pred = None

        for name, model in models.items():
            model.fit(X_train, y_train)
            prob = model.predict_proba(X_test)[:, 1]
            pred = (prob >= 0.5).astype(int)
            metrics = compute_metrics(y_test, pred, prob)
            if best_metrics is None or metrics["f1"] > best_metrics["f1"]:
                best_name = name
                best_model = model
                best_metrics = metrics
                best_proba = prob
                best_pred = pred

        assert best_model is not None and best_metrics is not None and best_name is not None

        report_dir = Path("./models_artifacts/reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        save_confusion_matrix_plot(y_test, best_pred, str(report_dir / f"confusion_matrix_{timestamp}.png"))
        save_roc_plot(y_test, best_proba, str(report_dir / f"roc_{timestamp}.png"))

        seen_bot_sources = sorted(
            set(frame[(frame["label"] == 1) & (frame.index.isin(train_idx))]["source"].astype(str).tolist())
        )

        metadata = {
            "version": f"{best_name}_{timestamp}",
            "algorithm": best_name,
            "feature_set_version": "v1",
            "metrics": best_metrics,
            "window_size": args.window_size,
            "stride": args.stride,
            "seen_bot_sources": seen_bot_sources,
        }
        artifact_name, artifact_path = model_manager.save_bundle(
            bundle={
                "model": best_model,
                "feature_columns": FEATURE_COLUMNS,
            },
            metadata=metadata,
        )

        prediction_repo = PredictionRepository(db)
        prediction_repo.upsert_model_version(
            name="behavioral-biometrics",
            version=metadata["version"],
            algorithm=best_name,
            metrics=best_metrics,
            artifact_path=artifact_path,
            model_metadata={
                "artifact_name": artifact_name,
                "window_size": args.window_size,
                "stride": args.stride,
                "seen_bot_sources": seen_bot_sources,
            },
        )

        print("Training finished")
        print(f"Selected model: {best_name}")
        print(f"Version: {metadata['version']}")
        print(f"Metrics: {best_metrics}")
        print(f"Artifact: {artifact_path}")
    finally:
        db.close()


if __name__ == "__main__":
    train()

```

## backend\app\ml\__init__.py

`$lang


```

## backend\app\models\db_models.py

`$lang
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

```

## backend\app\models\schemas.py

`$lang
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

```

## backend\app\models\__init__.py

`$lang


```

## backend\app\repositories\prediction_repo.py

`$lang
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.db_models import EnforcementAction, ModelVersion, Prediction


class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_prediction(self, session_id: str) -> Prediction | None:
        stmt = (
            select(Prediction)
            .where(Prediction.session_id == session_id)
            .order_by(Prediction.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def create_prediction(
        self,
        session_id: str,
        predicted_label: str,
        probability_bot: float,
        confidence: float,
        risk_score: float,
        feature_snapshot: dict,
        model_version_id: str | None,
    ) -> Prediction:
        prediction = Prediction(
            session_id=session_id,
            predicted_label=predicted_label,
            probability_bot=probability_bot,
            confidence=confidence,
            risk_score=risk_score,
            feature_snapshot=feature_snapshot,
            model_version_id=model_version_id,
        )
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def create_action(
        self,
        session_id: str,
        action: str,
        reason: str,
        prediction_id: str | None,
        action_metadata: dict | None = None,
    ) -> EnforcementAction:
        record = EnforcementAction(
            session_id=session_id,
            action=action,
            reason=reason,
            prediction_id=prediction_id,
            action_metadata=action_metadata or {},
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest_action(self, session_id: str) -> EnforcementAction | None:
        stmt = (
            select(EnforcementAction)
            .where(EnforcementAction.session_id == session_id)
            .order_by(EnforcementAction.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_active_model(self) -> ModelVersion | None:
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.is_active.is_(True))
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def upsert_model_version(
        self,
        name: str,
        version: str,
        algorithm: str,
        metrics: dict,
        artifact_path: str,
        model_metadata: dict,
    ) -> ModelVersion:
        self.db.execute(update(ModelVersion).values(is_active=False))
        model_version = ModelVersion(
            name=name,
            version=version,
            algorithm=algorithm,
            metrics=metrics,
            artifact_path=artifact_path,
            model_metadata=model_metadata,
            is_active=True,
        )
        self.db.add(model_version)
        self.db.commit()
        self.db.refresh(model_version)
        return model_version

```

## backend\app\repositories\session_repo.py

`$lang
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

```

## backend\app\repositories\__init__.py

`$lang


```

## backend\app\scripts\export_replay.py

`$lang
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

```

## backend\app\scripts\seed_demo_data.py

`$lang
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

```

## backend\app\services\feature_engineering.py

`$lang
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

import numpy as np


FEATURE_COLUMNS = [
    "event_count",
    "window_duration_ms",
    "mousemove_count",
    "click_count",
    "scroll_count",
    "focus_blur_transitions",
    "viewport_enter_count",
    "viewport_leave_count",
    "path_length",
    "displacement",
    "path_efficiency",
    "speed_mean",
    "speed_std",
    "speed_max",
    "acc_mean",
    "acc_std",
    "acc_max",
    "jerk_mean",
    "jerk_std",
    "jerk_max",
    "curvature_mean",
    "curvature_std",
    "angle_change_mean",
    "angle_change_std",
    "micro_pause_count",
    "correction_rhythm",
    "click_interval_mean",
    "click_interval_std",
    "hover_before_click_mean",
    "dwell_time_mean",
    "overshoot_count",
    "target_revisit_count",
    "scroll_velocity_mean",
    "scroll_velocity_std",
    "unique_event_types",
    "event_type_entropy",
    "webdriver_flag",
    "headless_flag",
    "viewport_area",
    "screen_area",
    "viewport_screen_ratio",
    "hardware_concurrency",
    "device_memory",
]


@dataclass
class SimpleEvent:
    event_type: str
    ts_ms: int
    x: float | None = None
    y: float | None = None
    scroll_x: float | None = None
    scroll_y: float | None = None
    target_id: str | None = None
    in_viewport: bool | None = None


def _safe_mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _safe_std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _safe_max(values: list[float]) -> float:
    return float(np.max(values)) if values else 0.0


def _vector_angle(dx: float, dy: float) -> float:
    return math.atan2(dy, dx)


def _angle_diff(a1: float, a2: float) -> float:
    diff = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    return abs(diff)


def _entropy(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    probabilities = [count / total for count in counter.values()]
    return float(-sum(p * math.log2(p) for p in probabilities if p > 0))


def _coerce_event(event: object) -> SimpleEvent:
    return SimpleEvent(
        event_type=getattr(event, "event_type"),
        ts_ms=int(getattr(event, "ts_ms")),
        x=getattr(event, "x", None),
        y=getattr(event, "y", None),
        scroll_x=getattr(event, "scroll_x", None),
        scroll_y=getattr(event, "scroll_y", None),
        target_id=getattr(event, "target_id", None),
        in_viewport=getattr(event, "in_viewport", None),
    )


def build_feature_vector(events: Iterable[object], environment: dict | None = None) -> dict[str, float]:
    ordered_events = sorted((_coerce_event(ev) for ev in events), key=lambda e: e.ts_ms)
    environment = environment or {}

    if not ordered_events:
        return {column: 0.0 for column in FEATURE_COLUMNS}

    event_counter = Counter(event.event_type for event in ordered_events)

    speeds: list[float] = []
    accelerations: list[float] = []
    jerks: list[float] = []
    curvatures: list[float] = []
    angle_changes: list[float] = []
    scroll_velocities: list[float] = []

    click_times: list[int] = []
    dwell_durations: list[float] = []
    hover_before_click: list[float] = []

    path_length = 0.0
    displacement = 0.0
    micro_pause_count = 0
    correction_rhythm = 0
    overshoot_count = 0
    target_revisit_count = 0

    last_move = None
    last_speed = None
    last_acc = None
    last_angle = None

    target_click_counter: Counter[str] = Counter()

    for event in ordered_events:
        if event.event_type == "click":
            click_times.append(event.ts_ms)
            if event.target_id:
                target_click_counter[event.target_id] += 1
            if last_move is not None and event.x is not None and event.y is not None:
                dt_hover_ms = max(0, event.ts_ms - int(last_move.ts_ms))
                if (
                    last_move.x is not None
                    and last_move.y is not None
                    and math.dist((event.x, event.y), (last_move.x, last_move.y)) < 35
                ):
                    hover_before_click.append(float(dt_hover_ms))

    if target_click_counter:
        target_revisit_count = sum(1 for count in target_click_counter.values() if count > 1)

    for prev, cur in zip(ordered_events[:-1], ordered_events[1:]):
        dt_ms = max(1, cur.ts_ms - prev.ts_ms)
        dt_s = dt_ms / 1000.0

        if cur.event_type == "scroll" and prev.scroll_y is not None and cur.scroll_y is not None:
            scroll_velocities.append(abs(cur.scroll_y - prev.scroll_y) / dt_s)

        if prev.x is None or prev.y is None or cur.x is None or cur.y is None:
            continue

        dx = cur.x - prev.x
        dy = cur.y - prev.y
        distance = math.hypot(dx, dy)
        path_length += distance

        speed = distance / dt_s
        speeds.append(speed)

        if speed < 40:
            micro_pause_count += 1

        angle = _vector_angle(dx, dy)
        if last_angle is not None:
            angle_diff = _angle_diff(last_angle, angle)
            angle_changes.append(angle_diff)
            curvatures.append(angle_diff / max(distance, 1.0))
            if angle_diff > 1.1:
                correction_rhythm += 1
        last_angle = angle

        if last_speed is not None:
            acc = (speed - last_speed) / dt_s
            accelerations.append(acc)
            if last_acc is not None:
                jerks.append((acc - last_acc) / dt_s)
            last_acc = acc
        last_speed = speed

        if prev.event_type == "mousemove":
            last_move = cur

    first = ordered_events[0]
    last = ordered_events[-1]
    if (
        first.x is not None
        and first.y is not None
        and last.x is not None
        and last.y is not None
    ):
        displacement = math.dist((first.x, first.y), (last.x, last.y))

    if speeds:
        dwell_durations = [1000.0 / max(speed, 1.0) for speed in speeds]

    for click_ts in click_times:
        prior_moves = [
            event for event in ordered_events if event.event_type == "mousemove" and event.ts_ms < click_ts
        ]
        if len(prior_moves) >= 4:
            recent = prior_moves[-4:]
            reversal_count = 0
            previous_sign = None
            for prev, cur in zip(recent[:-1], recent[1:]):
                if prev.x is None or cur.x is None:
                    continue
                sign = 1 if cur.x - prev.x >= 0 else -1
                if previous_sign is not None and sign != previous_sign:
                    reversal_count += 1
                previous_sign = sign
            if reversal_count >= 2:
                overshoot_count += 1

    click_intervals = [
        float(cur - prev) for prev, cur in zip(click_times[:-1], click_times[1:]) if cur - prev > 0
    ]

    window_duration_ms = max(1, ordered_events[-1].ts_ms - ordered_events[0].ts_ms)

    viewport_width = float(environment.get("viewport_width") or 0)
    viewport_height = float(environment.get("viewport_height") or 0)
    screen_width = float(environment.get("screen_width") or 0)
    screen_height = float(environment.get("screen_height") or 0)

    vector = {
        "event_count": float(len(ordered_events)),
        "window_duration_ms": float(window_duration_ms),
        "mousemove_count": float(event_counter.get("mousemove", 0)),
        "click_count": float(event_counter.get("click", 0)),
        "scroll_count": float(event_counter.get("scroll", 0)),
        "focus_blur_transitions": float(event_counter.get("focus", 0) + event_counter.get("blur", 0)),
        "viewport_enter_count": float(event_counter.get("viewport_enter", 0)),
        "viewport_leave_count": float(event_counter.get("viewport_leave", 0)),
        "path_length": float(path_length),
        "displacement": float(displacement),
        "path_efficiency": float(displacement / max(path_length, 1.0)),
        "speed_mean": _safe_mean(speeds),
        "speed_std": _safe_std(speeds),
        "speed_max": _safe_max(speeds),
        "acc_mean": _safe_mean(accelerations),
        "acc_std": _safe_std(accelerations),
        "acc_max": _safe_max(accelerations),
        "jerk_mean": _safe_mean(jerks),
        "jerk_std": _safe_std(jerks),
        "jerk_max": _safe_max(jerks),
        "curvature_mean": _safe_mean(curvatures),
        "curvature_std": _safe_std(curvatures),
        "angle_change_mean": _safe_mean(angle_changes),
        "angle_change_std": _safe_std(angle_changes),
        "micro_pause_count": float(micro_pause_count),
        "correction_rhythm": float(correction_rhythm),
        "click_interval_mean": _safe_mean(click_intervals),
        "click_interval_std": _safe_std(click_intervals),
        "hover_before_click_mean": _safe_mean(hover_before_click),
        "dwell_time_mean": _safe_mean(dwell_durations),
        "overshoot_count": float(overshoot_count),
        "target_revisit_count": float(target_revisit_count),
        "scroll_velocity_mean": _safe_mean(scroll_velocities),
        "scroll_velocity_std": _safe_std(scroll_velocities),
        "unique_event_types": float(len(event_counter)),
        "event_type_entropy": _entropy(event_counter),
        "webdriver_flag": float(bool(environment.get("webdriver"))),
        "headless_flag": float(bool(environment.get("headless_hint"))),
        "viewport_area": viewport_width * viewport_height,
        "screen_area": screen_width * screen_height,
        "viewport_screen_ratio": (viewport_width * viewport_height)
        / max(screen_width * screen_height, 1.0),
        "hardware_concurrency": float(environment.get("hardware_concurrency") or 0),
        "device_memory": float(environment.get("device_memory") or 0),
    }

    for column in FEATURE_COLUMNS:
        vector.setdefault(column, 0.0)

    return vector


def to_feature_array(vector: dict[str, float]) -> list[float]:
    return [float(vector.get(column, 0.0)) for column in FEATURE_COLUMNS]

```

## backend\app\services\model_manager.py

`$lang
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np

from app.core.config import settings
from app.services.feature_engineering import FEATURE_COLUMNS, to_feature_array


@dataclass
class ModelPrediction:
    predicted_label: str
    probability_bot: float
    confidence: float
    risk_score: float
    model_version: str | None


class ModelManager:
    def __init__(self, artifact_dir: str | None = None) -> None:
        self.artifact_dir = Path(artifact_dir or settings.model_artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.active_artifact_path = self.artifact_dir / "active_model.joblib"
        self.active_metadata_path = self.artifact_dir / "active_model_metadata.json"

    def has_active_model(self) -> bool:
        return self.active_artifact_path.exists()

    def save_bundle(self, bundle: dict, metadata: dict) -> tuple[str, str]:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        artifact_name = f"model_{timestamp}.joblib"
        artifact_path = self.artifact_dir / artifact_name

        joblib.dump(bundle, artifact_path)
        joblib.dump(bundle, self.active_artifact_path)

        metadata = {**metadata, "artifact_name": artifact_name, "saved_at": datetime.utcnow().isoformat()}
        self.active_metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return artifact_name, str(artifact_path)

    def _load_bundle(self) -> dict:
        if not self.active_artifact_path.exists():
            raise FileNotFoundError("No active model artifact found")
        return joblib.load(self.active_artifact_path)

    def _load_metadata(self) -> dict:
        if not self.active_metadata_path.exists():
            return {}
        return json.loads(self.active_metadata_path.read_text(encoding="utf-8"))

    def predict(self, features: dict[str, float]) -> ModelPrediction:
        if self.has_active_model():
            bundle = self._load_bundle()
            model = bundle["model"]
            columns = bundle.get("feature_columns", FEATURE_COLUMNS)
            payload = np.array([[float(features.get(col, 0.0)) for col in columns]], dtype=float)
            probability_bot = float(model.predict_proba(payload)[0][1])
            predicted_label = "bot" if probability_bot >= 0.5 else "human"
            confidence = float(max(probability_bot, 1.0 - probability_bot))
            risk_score = float(np.clip(probability_bot * 100.0, 0.0, 100.0))
            metadata = self._load_metadata()
            return ModelPrediction(
                predicted_label=predicted_label,
                probability_bot=probability_bot,
                confidence=confidence,
                risk_score=risk_score,
                model_version=metadata.get("version"),
            )

        heuristic_probability = self._heuristic_bot_probability(features)
        return ModelPrediction(
            predicted_label="bot" if heuristic_probability >= 0.5 else "human",
            probability_bot=heuristic_probability,
            confidence=max(heuristic_probability, 1.0 - heuristic_probability),
            risk_score=float(np.clip(heuristic_probability * 100.0, 0.0, 100.0)),
            model_version=None,
        )

    def _heuristic_bot_probability(self, features: dict[str, float]) -> float:
        speed_std = float(features.get("speed_std", 0.0))
        angle_std = float(features.get("angle_change_std", 0.0))
        entropy = float(features.get("event_type_entropy", 0.0))
        webdriver = float(features.get("webdriver_flag", 0.0))
        headless = float(features.get("headless_flag", 0.0))

        score = 0.15
        if speed_std < 25:
            score += 0.25
        if angle_std < 0.12:
            score += 0.2
        if entropy < 1.2:
            score += 0.15
        score += webdriver * 0.2 + headless * 0.15
        return float(np.clip(score, 0.01, 0.99))


model_manager = ModelManager()

```

## backend\app\services\policy_engine.py

`$lang
from dataclasses import dataclass


@dataclass
class PolicyDecision:
    action: str
    reason: str


class PolicyEngine:
    def __init__(
        self,
        low_risk_threshold: float = 25.0,
        moderate_risk_threshold: float = 50.0,
        high_risk_threshold: float = 75.0,
        critical_risk_threshold: float = 90.0,
    ) -> None:
        self.low_risk_threshold = low_risk_threshold
        self.moderate_risk_threshold = moderate_risk_threshold
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold

    def decide(self, risk_score: float) -> PolicyDecision:
        if risk_score < self.low_risk_threshold:
            return PolicyDecision(action="allow", reason="Niskie ryzyko zachowania botowego")
        if risk_score < self.moderate_risk_threshold:
            return PolicyDecision(action="observe", reason="Umiarkowane ryzyko, zwiększamy monitoring")
        if risk_score < self.high_risk_threshold:
            return PolicyDecision(action="throttle", reason="Wysokie ryzyko, ograniczamy tempo żądań")
        if risk_score < self.critical_risk_threshold:
            return PolicyDecision(action="challenge", reason="Bardzo wysokie ryzyko, wymagamy dodatkowej weryfikacji")
        return PolicyDecision(action="block", reason="Krytyczne ryzyko, sesja została zablokowana")

```

## backend\app\services\telemetry_service.py

`$lang
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

```

## backend\app\services\training_data_service.py

`$lang
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

```

## backend\app\services\__init__.py

`$lang


```

## backend\app\tests\test_feature_engineering.py

`$lang
from types import SimpleNamespace

from app.services.feature_engineering import FEATURE_COLUMNS, build_feature_vector


def test_feature_vector_contains_required_columns():
    events = [
        SimpleNamespace(event_type="mousemove", ts_ms=1000, x=10.0, y=20.0, scroll_x=0.0, scroll_y=0.0, target_id=None, in_viewport=True),
        SimpleNamespace(event_type="mousemove", ts_ms=1020, x=30.0, y=40.0, scroll_x=0.0, scroll_y=0.0, target_id=None, in_viewport=True),
        SimpleNamespace(event_type="click", ts_ms=1200, x=30.0, y=40.0, scroll_x=0.0, scroll_y=0.0, target_id="cta-buy", in_viewport=True),
        SimpleNamespace(event_type="scroll", ts_ms=1300, x=None, y=None, scroll_x=0.0, scroll_y=240.0, target_id=None, in_viewport=True),
        SimpleNamespace(event_type="blur", ts_ms=1400, x=None, y=None, scroll_x=0.0, scroll_y=240.0, target_id=None, in_viewport=False),
    ]

    env = {
        "viewport_width": 1200,
        "viewport_height": 700,
        "screen_width": 1920,
        "screen_height": 1080,
        "webdriver": False,
        "headless_hint": False,
    }

    vector = build_feature_vector(events, env)

    for column in FEATURE_COLUMNS:
        assert column in vector

    assert vector["event_count"] == 5
    assert vector["click_count"] >= 1
    assert vector["path_length"] > 0
    assert vector["speed_mean"] >= 0

```

## backend\app\tests\test_policy_engine.py

`$lang
from app.services.policy_engine import PolicyEngine


def test_policy_thresholds():
    engine = PolicyEngine()

    assert engine.decide(10).action == "allow"
    assert engine.decide(35).action == "observe"
    assert engine.decide(65).action == "throttle"
    assert engine.decide(85).action == "challenge"
    assert engine.decide(95).action == "block"

```

## backend\data\raw\.gitkeep

`$lang


```

## backend\models_artifacts\.gitkeep

`$lang


```

## bot_runner\Dockerfile

`$lang
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN playwright install --with-deps chromium

COPY . /app

CMD ["sleep", "infinity"]

```

## bot_runner\main.py

`$lang
from __future__ import annotations

import argparse
import os

from playwright.sync_api import sync_playwright

from scenarios import run_named_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot runner for behavioral biometrics MVP")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=["human_manual", "linear", "human_like", "replay"],
        help="Behavior scenario to execute",
    )
    parser.add_argument("--sessions", type=int, default=1)
    parser.add_argument("--target-url", default=os.getenv("BOT_TARGET_URL", "http://localhost:5173"))
    parser.add_argument("--replay-file", default="replay_sample.json")
    parser.add_argument("--manual-seconds", type=int, default=25)
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        try:
            for idx in range(args.sessions):
                context = browser.new_context(viewport={"width": 1366, "height": 768})
                page = context.new_page()
                print(f"Running scenario={args.scenario} session={idx + 1}/{args.sessions}")
                run_named_scenario(
                    page=page,
                    scenario=args.scenario,
                    target_url=args.target_url,
                    replay_file=args.replay_file,
                    manual_seconds=args.manual_seconds,
                )
                context.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()

```

## bot_runner\replay_sample.json

`$lang
[
  { "x": 112, "y": 146, "delay_ms": 18, "click": false },
  { "x": 141, "y": 169, "delay_ms": 22, "click": false },
  { "x": 170, "y": 191, "delay_ms": 24, "click": false },
  { "x": 204, "y": 212, "delay_ms": 21, "click": false },
  { "x": 238, "y": 226, "delay_ms": 27, "click": false },
  { "x": 275, "y": 243, "delay_ms": 18, "click": true },
  { "x": 311, "y": 259, "delay_ms": 26, "click": false },
  { "x": 356, "y": 284, "delay_ms": 19, "click": false },
  { "x": 397, "y": 302, "delay_ms": 17, "click": false },
  { "x": 443, "y": 318, "delay_ms": 20, "click": true }
]

```

## bot_runner\requirements.txt

`$lang
playwright==1.49.1

```

## bot_runner\scenarios.py

`$lang
from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

from playwright.sync_api import Page


def open_testbed(page: Page, target_url: str) -> None:
    page.goto(target_url, wait_until="networkidle")
    page.wait_for_timeout(1000)


def scenario_human_manual(page: Page, target_url: str, duration_seconds: int = 25) -> None:
    open_testbed(page, target_url)
    print(
        "Manual baseline: wykonuj interakcje myszką ręcznie w otwartym oknie przeglądarki "
        f"przez {duration_seconds} sekund."
    )
    page.wait_for_timeout(duration_seconds * 1000)


def scenario_linear(page: Page, target_url: str) -> None:
    open_testbed(page, target_url)
    start_points = [(80, 120), (280, 140), (520, 170), (780, 190), (980, 220)]

    for x, y in start_points:
        page.mouse.move(x, y, steps=12)
        time.sleep(0.02)

    selectors = [
        "#menu-products",
        "#filter-network",
        "#product-3-cart",
        "#newsletter-toggle",
        "#agree-toggle",
        "#cta-buy",
    ]

    for selector in selectors:
        locator = page.locator(selector)
        box = locator.bounding_box()
        if not box:
            continue
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        page.mouse.move(target_x, target_y, steps=18)
        page.mouse.click(target_x, target_y)
        time.sleep(0.03)

    for y in [120, 260, 420, 580, 320, 140]:
        page.mouse.wheel(0, y)
        time.sleep(0.025)


def _bezier(p0, p1, p2, p3, t):
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t**2 * p2
        + t**3 * p3
    )


def _move_bezier(page: Page, start: tuple[float, float], end: tuple[float, float], steps: int = 40):
    x0, y0 = start
    x3, y3 = end

    cp1 = (x0 + (x3 - x0) * 0.3 + random.uniform(-80, 80), y0 + random.uniform(-90, 90))
    cp2 = (x0 + (x3 - x0) * 0.7 + random.uniform(-80, 80), y3 + random.uniform(-90, 90))

    for i in range(1, steps + 1):
        t = i / steps
        x = _bezier(x0, cp1[0], cp2[0], x3, t) + random.uniform(-1.1, 1.1)
        y = _bezier(y0, cp1[1], cp2[1], y3, t) + random.uniform(-1.1, 1.1)
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.004, 0.02))


def scenario_human_like(page: Page, target_url: str) -> None:
    open_testbed(page, target_url)

    selectors = [
        "#menu-home",
        "#search-input",
        "#filter-software",
        "#product-4-details",
        "#product-4-cart",
        "#newsletter-toggle",
        "#agree-toggle",
        "#cta-buy",
    ]

    current = (130.0, 120.0)
    for selector in selectors:
        box = page.locator(selector).bounding_box()
        if not box:
            continue

        target = (
            box["x"] + box["width"] * random.uniform(0.35, 0.65),
            box["y"] + box["height"] * random.uniform(0.35, 0.65),
        )
        _move_bezier(page, current, target, steps=random.randint(20, 50))

        if random.random() < 0.75:
            page.mouse.click(target[0], target[1])
            time.sleep(random.uniform(0.02, 0.18))

        if selector == "#search-input":
            page.keyboard.type("router secure", delay=random.randint(40, 120))

        if random.random() < 0.3:
            page.mouse.wheel(0, random.randint(-250, 420))

        current = target


def scenario_replay(page: Page, target_url: str, replay_file: str) -> None:
    open_testbed(page, target_url)

    replay_path = Path(replay_file)
    data = json.loads(replay_path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise RuntimeError("Replay file must contain a list of points")

    for point in data:
        x = float(point.get("x", 0))
        y = float(point.get("y", 0))
        delay_ms = max(1, int(point.get("delay_ms", 20)))
        page.mouse.move(x, y)
        if point.get("click"):
            page.mouse.click(x, y)
        page.wait_for_timeout(delay_ms)

    page.wait_for_timeout(700)


def run_named_scenario(page: Page, scenario: str, target_url: str, replay_file: str, manual_seconds: int) -> None:
    if scenario == "human_manual":
        scenario_human_manual(page, target_url, duration_seconds=manual_seconds)
        return
    if scenario == "linear":
        scenario_linear(page, target_url)
        return
    if scenario == "human_like":
        scenario_human_like(page, target_url)
        return
    if scenario == "replay":
        scenario_replay(page, target_url, replay_file)
        return
    raise ValueError(f"Unknown scenario: {scenario}")

```

## frontend\Dockerfile

`$lang
FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
RUN npm install

COPY . /app

EXPOSE 5173

CMD ["npm", "run", "dev"]

```

## frontend\index.html

`$lang
<!doctype html>
<html lang="pl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Bot czy człowiek - Testbed</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>

```

## frontend\package.json

`$lang
{
  "name": "behavioral-biometrics-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 5173",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 0.0.0.0 --port 4173"
  },
  "dependencies": {
    "axios": "1.7.7",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/react": "18.3.10",
    "@types/react-dom": "18.3.0",
    "@vitejs/plugin-react": "4.3.2",
    "typescript": "5.6.2",
    "vite": "5.4.8"
  }
}

```

## frontend\tsconfig.json

`$lang
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "types": ["vite/client"]
  },
  "include": ["src"]
}

```

## frontend\vite.config.ts

`$lang
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
});

```

## frontend\src\App.tsx

`$lang
import { useEffect, useRef, useState } from "react";

import {
  createSession,
  labelSession,
  PredictionResponse,
  requestPrediction,
  sendEventsBatch,
} from "./api/client";
import { InteractionPanel } from "./components/InteractionPanel";
import { PredictionPanel } from "./components/PredictionPanel";
import { TelemetryCollector } from "./telemetry/collector";
import { collectFingerprint } from "./telemetry/fingerprint";

function App() {
  const collectorRef = useRef<TelemetryCollector | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [bufferedCount, setBufferedCount] = useState(0);
  const [acceptedCount, setAcceptedCount] = useState(0);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Inicjalizacja...");

  useEffect(() => {
    let active = true;

    const bootstrap = async () => {
      try {
        const fingerprint = collectFingerprint();
        const session = await createSession({
          source: "frontend_manual",
          client_fingerprint: fingerprint,
          environment: {
            ...fingerprint,
            page: window.location.pathname,
            referrer: document.referrer,
            started_at: new Date().toISOString(),
          },
        });

        if (!active) {
          return;
        }

        setSessionId(session.session_id);
        setStatusMessage("Sesja telemetryczna aktywna");

        const collector = new TelemetryCollector({
          batchSize: 35,
          flushIntervalMs: 2000,
          onBatch: async (events) => {
            await sendEventsBatch(session.session_id, events);
          },
          onBufferedCount: setBufferedCount,
          onAcceptedCount: (count) => setAcceptedCount((prev) => prev + count),
          onError: () => {
            setStatusMessage("Błąd wysyłki batcha - ponawianie");
          },
        });

        collector.start();
        collectorRef.current = collector;
      } catch (error) {
        setStatusMessage(`Błąd inicjalizacji: ${String(error)}`);
      }
    };

    void bootstrap();

    return () => {
      active = false;
      collectorRef.current?.stop();
      collectorRef.current = null;
    };
  }, []);

  const handlePredict = async () => {
    if (!sessionId) {
      return;
    }

    try {
      setLoadingPrediction(true);
      await collectorRef.current?.flush();
      const response = await requestPrediction(sessionId);
      setPrediction(response);
      setStatusMessage(`Decyzja: ${response.enforcement_action}`);
    } catch (error) {
      setStatusMessage(`Błąd predykcji: ${String(error)}`);
    } finally {
      setLoadingPrediction(false);
    }
  };

  const handleLabel = async (label: "human" | "bot") => {
    if (!sessionId) {
      return;
    }

    try {
      await collectorRef.current?.flush();
      await labelSession(sessionId, label);
      setStatusMessage(`Sesja oznaczona jako ${label}`);
    } catch (error) {
      setStatusMessage(`Błąd etykietowania: ${String(error)}`);
    }
  };

  return (
    <div className="layout">
      <header className="hero surface">
        <div>
          <h1>Bot czy człowiek? Behavioral Biometrics MVP</h1>
          <p>
            Demo collecting mouse dynamics + policy enforcement. Interact naturally,
            then trigger inference and action.
          </p>
        </div>

        <div className="status-grid">
          <div>
            <span>Session ID</span>
            <strong>{sessionId ?? "-"}</strong>
          </div>
          <div>
            <span>Zbuforowane eventy</span>
            <strong>{bufferedCount}</strong>
          </div>
          <div>
            <span>Wysłane eventy</span>
            <strong>{acceptedCount}</strong>
          </div>
          <div>
            <span>Status</span>
            <strong>{statusMessage}</strong>
          </div>
        </div>
      </header>

      <main className="content-grid">
        <InteractionPanel />
        <PredictionPanel
          prediction={prediction}
          loading={loadingPrediction}
          onPredict={handlePredict}
          onLabel={handleLabel}
        />
      </main>
    </div>
  );
}

export default App;

```

## frontend\src\main.tsx

`$lang
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

```

## frontend\src\styles.css

`$lang
:root {
  --bg: #f4f6f8;
  --surface: #ffffff;
  --surface-strong: #0d1b2a;
  --text: #0f1f2e;
  --muted: #5f7388;
  --accent: #0ea5a3;
  --accent-dark: #0d9488;
  --accent-soft: #9be7e2;
  --danger: #b91c1c;
  --ring: rgba(14, 165, 163, 0.28);
  --shadow: 0 16px 40px rgba(13, 27, 42, 0.12);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Segoe UI", "Calibri", "Trebuchet MS", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at 0% 0%, #d8f4f1 0%, transparent 45%),
    radial-gradient(circle at 100% 20%, #fddab8 0%, transparent 35%),
    var(--bg);
  min-height: 100vh;
}

.layout {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 20px 40px;
}

.surface {
  background: var(--surface);
  border-radius: 18px;
  box-shadow: var(--shadow);
}

.hero {
  padding: 24px;
  display: grid;
  gap: 18px;
  border: 1px solid rgba(13, 148, 136, 0.15);
}

.hero h1 {
  margin: 0 0 8px;
  font-size: clamp(1.45rem, 2.2vw, 2.2rem);
}

.hero p {
  margin: 0;
  color: var(--muted);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
  gap: 12px;
}

.status-grid > div {
  border-radius: 12px;
  padding: 12px;
  background: linear-gradient(140deg, #f6fbfb, #f2f7fa);
  border: 1px solid #dde7ef;
}

.status-grid span {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
  margin-bottom: 6px;
}

.status-grid strong {
  font-size: 0.9rem;
  word-break: break-word;
}

.content-grid {
  margin-top: 22px;
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(290px, 1fr);
  gap: 20px;
  align-items: start;
}

.panel {
  padding: 20px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.3rem;
}

.panel-header p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 0.95rem;
}

.menu-row {
  margin: 16px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.menu-btn,
.primary-btn,
.secondary-btn,
.cta-btn,
.chip {
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.menu-btn {
  background: #edf5f9;
  color: var(--text);
  padding: 9px 14px;
}

.primary-btn {
  background: linear-gradient(135deg, var(--accent), var(--accent-dark));
  color: #fff;
  padding: 10px 14px;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  background: #f2f7fa;
  color: #21465b;
  padding: 10px 14px;
}

.cta-btn {
  background: #163b58;
  color: #fff;
  padding: 12px 16px;
  font-weight: 600;
}

.cta-btn:disabled {
  background: #93a7b8;
  cursor: not-allowed;
}

button:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(13, 27, 42, 0.14);
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.control-card {
  border: 1px solid #dde7ef;
  border-radius: 12px;
  padding: 12px;
  background: #f9fbfc;
}

.control-card label,
.control-card span {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
}

input[type="text"],
input[type="email"] {
  width: 100%;
  border-radius: 10px;
  border: 1px solid #cbd7e1;
  padding: 10px 12px;
  outline: none;
}

input[type="text"]:focus,
input[type="email"]:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--ring);
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 8px 11px;
  background: #eaf2f7;
  color: #21465b;
}

.chip-active {
  background: #163b58;
  color: #fff;
}

.product-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
}

.product-card {
  border: 1px solid #dde7ef;
  border-radius: 12px;
  padding: 12px;
  background: linear-gradient(170deg, #ffffff, #f5fafb);
}

.product-card h3 {
  margin: 0;
}

.price {
  font-weight: 700;
  margin: 8px 0;
}

.rating {
  margin: 0;
  color: #25526a;
}

.product-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.form-grid {
  margin-top: 18px;
  display: grid;
  gap: 10px;
}

.toggle-row {
  display: grid;
  gap: 7px;
}

.toggle-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #304a5e;
}

.sticky {
  position: sticky;
  top: 20px;
}

.prediction-actions {
  display: grid;
  gap: 8px;
  margin: 14px 0;
}

.risk-card {
  margin-top: 8px;
  border: 1px solid #dde7ef;
  border-radius: 12px;
  padding: 12px;
  background: #f8fbfd;
}

.risk-card p {
  margin: 0;
  color: var(--muted);
}

.risk-card strong {
  display: block;
  margin-top: 5px;
  font-size: 1.3rem;
}

.risk-bar {
  margin-top: 10px;
  width: 100%;
  height: 11px;
  border-radius: 999px;
  background: #d6e5ee;
  overflow: hidden;
}

.risk-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #0ea5a3, #f59e0b, #dc2626);
}

.prediction-grid {
  margin: 14px 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.prediction-grid div {
  padding: 8px;
  border-radius: 10px;
  background: #f2f7fa;
}

.prediction-grid dt {
  color: var(--muted);
  font-size: 0.78rem;
}

.prediction-grid dd {
  margin: 4px 0 0;
  font-weight: 700;
}

.muted {
  color: var(--muted);
}

@media (max-width: 980px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .sticky {
    position: static;
  }
}

```

## frontend\src\api\client.ts

`$lang
import axios from "axios";
import { FingerprintPayload, TelemetryEvent } from "../telemetry/types";

export type PredictionResponse = {
  session_id: string;
  predicted_label: "human" | "bot";
  probability_bot: number;
  confidence: number;
  risk_score: number;
  model_version: string | null;
  enforcement_action: "allow" | "observe" | "throttle" | "challenge" | "block";
  enforcement_reason: string;
  created_at: string;
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  timeout: 15000,
});

export async function createSession(payload: {
  source: string;
  client_fingerprint: FingerprintPayload;
  environment: Record<string, unknown>;
}) {
  const response = await api.post<{ session_id: string; created_at: string }>("/sessions", payload);
  return response.data;
}

export async function sendEventsBatch(sessionId: string, events: TelemetryEvent[]) {
  const response = await api.post<{ accepted: number; session_id: string }>("/events/batch", {
    session_id: sessionId,
    events,
  });
  return response.data;
}

export async function requestPrediction(sessionId: string) {
  const response = await api.post<PredictionResponse>(`/predict/${sessionId}`);
  return response.data;
}

export async function labelSession(sessionId: string, label: "human" | "bot") {
  const response = await api.post(`/sessions/${sessionId}/label`, { true_label: label });
  return response.data;
}

export async function getSessionStatus(sessionId: string) {
  const response = await api.get(`/sessions/${sessionId}`);
  return response.data;
}

```

## frontend\src\components\InteractionPanel.tsx

`$lang
import { useMemo, useState } from "react";

type Product = {
  id: string;
  title: string;
  category: string;
  price: string;
  rating: number;
};

const products: Product[] = [
  { id: "product-1", title: "Kamera IP Sentinel", category: "Monitoring", price: "899 PLN", rating: 4.7 },
  { id: "product-2", title: "Klucz FIDO2 Titan", category: "Identity", price: "289 PLN", rating: 4.9 },
  { id: "product-3", title: "Router SecureMesh", category: "Network", price: "649 PLN", rating: 4.4 },
  { id: "product-4", title: "Vault Password Suite", category: "Software", price: "79 PLN/mies", rating: 4.6 },
];

export function InteractionPanel() {
  const [selectedCategory, setSelectedCategory] = useState<string>("Wszystkie");
  const [search, setSearch] = useState("");
  const [newsletter, setNewsletter] = useState(false);
  const [agreed, setAgreed] = useState(false);

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const byCategory = selectedCategory === "Wszystkie" || product.category === selectedCategory;
      const bySearch = product.title.toLowerCase().includes(search.toLowerCase());
      return byCategory && bySearch;
    });
  }, [selectedCategory, search]);

  return (
    <section className="panel surface">
      <header className="panel-header">
        <h2>Interaktywny Testbed Ruchu</h2>
        <p>Eksploruj elementy jak w e-commerce, aby wygenerować naturalną trajektorię kursora.</p>
      </header>

      <nav className="menu-row" aria-label="Główne menu">
        <button id="menu-home" className="menu-btn">Start</button>
        <button id="menu-products" className="menu-btn">Produkty</button>
        <button id="menu-about" className="menu-btn">O projekcie</button>
        <button id="menu-contact" className="menu-btn">Kontakt</button>
      </nav>

      <div className="control-grid">
        <div className="control-card">
          <label htmlFor="search-input">Wyszukiwarka produktów</label>
          <input
            id="search-input"
            type="text"
            value={search}
            placeholder="np. router"
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <div className="control-card">
          <span>Filtr kategorii</span>
          <div className="chip-row">
            {["Wszystkie", "Monitoring", "Identity", "Network", "Software"].map((option) => (
              <button
                key={option}
                id={`filter-${option.toLowerCase()}`}
                className={selectedCategory === option ? "chip chip-active" : "chip"}
                onClick={() => setSelectedCategory(option)}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="product-grid">
        {filteredProducts.map((product) => (
          <article key={product.id} id={product.id} className="product-card">
            <h3>{product.title}</h3>
            <p className="muted">{product.category}</p>
            <p className="price">{product.price}</p>
            <p className="rating">Ocena: {product.rating}</p>
            <div className="product-actions">
              <button id={`${product.id}-details`} className="secondary-btn">
                Szczegóły
              </button>
              <button id={`${product.id}-cart`} className="primary-btn">
                Dodaj do koszyka
              </button>
            </div>
          </article>
        ))}
      </div>

      <form className="form-grid" onSubmit={(event) => event.preventDefault()}>
        <label htmlFor="email-input">Newsletter bezpieczeństwa</label>
        <input id="email-input" type="email" placeholder="email@domena.pl" />

        <div className="toggle-row">
          <label className="toggle-item" htmlFor="newsletter-toggle">
            <input
              id="newsletter-toggle"
              type="checkbox"
              checked={newsletter}
              onChange={(event) => setNewsletter(event.target.checked)}
            />
            Otrzymuj alerty o podatnościach
          </label>

          <label className="toggle-item" htmlFor="agree-toggle">
            <input
              id="agree-toggle"
              type="checkbox"
              checked={agreed}
              onChange={(event) => setAgreed(event.target.checked)}
            />
            Akceptuję regulamin testbedu
          </label>
        </div>

        <button id="cta-buy" className="cta-btn" disabled={!agreed}>
          Finalizuj próbny zakup
        </button>
      </form>
    </section>
  );
}

```

## frontend\src\components\PredictionPanel.tsx

`$lang
import { PredictionResponse } from "../api/client";

type PredictionPanelProps = {
  prediction: PredictionResponse | null;
  loading: boolean;
  onPredict: () => void;
  onLabel: (label: "human" | "bot") => void;
};

export function PredictionPanel({ prediction, loading, onPredict, onLabel }: PredictionPanelProps) {
  const risk = prediction?.risk_score ?? 0;

  return (
    <aside className="panel surface sticky">
      <header className="panel-header">
        <h2>Silnik Ochrony</h2>
        <p>Uruchom klasyfikację i decyzję policy engine dla bieżącej sesji.</p>
      </header>

      <div className="prediction-actions">
        <button id="run-prediction" className="primary-btn" onClick={onPredict} disabled={loading}>
          {loading ? "Analiza..." : "Analizuj sesję"}
        </button>
        <button id="label-human" className="secondary-btn" onClick={() => onLabel("human")}>
          Oznacz jako human
        </button>
        <button id="label-bot" className="secondary-btn" onClick={() => onLabel("bot")}>
          Oznacz jako bot
        </button>
      </div>

      <div className="risk-card">
        <p>Risk score</p>
        <strong>{risk.toFixed(1)} / 100</strong>
        <div className="risk-bar">
          <div className="risk-bar-fill" style={{ width: `${Math.min(100, risk)}%` }} />
        </div>
      </div>

      <dl className="prediction-grid">
        <div>
          <dt>Predykcja</dt>
          <dd>{prediction?.predicted_label ?? "-"}</dd>
        </div>
        <div>
          <dt>Prawd. bot</dt>
          <dd>{prediction ? prediction.probability_bot.toFixed(3) : "-"}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{prediction ? prediction.confidence.toFixed(3) : "-"}</dd>
        </div>
        <div>
          <dt>Decyzja</dt>
          <dd>{prediction?.enforcement_action ?? "-"}</dd>
        </div>
      </dl>

      <p className="muted">{prediction?.enforcement_reason ?? "Brak predykcji dla tej sesji"}</p>
    </aside>
  );
}

```

## frontend\src\telemetry\collector.ts

`$lang
import { TelemetryEvent } from "./types";

type CollectorOptions = {
  batchSize?: number;
  flushIntervalMs?: number;
  onBatch: (events: TelemetryEvent[]) => Promise<void>;
  onBufferedCount?: (count: number) => void;
  onAcceptedCount?: (count: number) => void;
  onError?: (error: unknown) => void;
};

export class TelemetryCollector {
  private readonly batchSize: number;
  private readonly flushIntervalMs: number;
  private readonly onBatch: (events: TelemetryEvent[]) => Promise<void>;
  private readonly onBufferedCount?: (count: number) => void;
  private readonly onAcceptedCount?: (count: number) => void;
  private readonly onError?: (error: unknown) => void;

  private sequenceNo = 0;
  private bufferedEvents: TelemetryEvent[] = [];
  private flushTimer: number | null = null;
  private isFlushing = false;
  private lastScrollY = window.scrollY;

  private listeners: Array<() => void> = [];

  constructor(options: CollectorOptions) {
    this.batchSize = options.batchSize ?? 35;
    this.flushIntervalMs = options.flushIntervalMs ?? 2000;
    this.onBatch = options.onBatch;
    this.onBufferedCount = options.onBufferedCount;
    this.onAcceptedCount = options.onAcceptedCount;
    this.onError = options.onError;
  }

  start() {
    this.attachListeners();
    this.flushTimer = window.setInterval(() => {
      void this.flush();
    }, this.flushIntervalMs);
  }

  stop() {
    this.listeners.forEach((removeListener) => removeListener());
    this.listeners = [];
    if (this.flushTimer !== null) {
      window.clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    void this.flush();
  }

  private attachListeners() {
    const onMouseMove = (event: MouseEvent) => {
      this.record({
        event_type: "mousemove",
        x: event.clientX,
        y: event.clientY,
        pointer_type: "mouse",
        in_viewport: !document.hidden,
        payload: {},
      });
    };

    const onClick = (event: MouseEvent) => {
      const target = this.extractTargetInfo(event.target);
      this.record({
        event_type: "click",
        x: event.clientX,
        y: event.clientY,
        target_id: target.target_id,
        target_tag: target.target_tag,
        target_class: target.target_class,
        pointer_type: "mouse",
        in_viewport: !document.hidden,
        payload: { button: event.button },
      });
    };

    const onScroll = () => {
      const deltaY = window.scrollY - this.lastScrollY;
      this.lastScrollY = window.scrollY;
      this.record({
        event_type: "scroll",
        scroll_x: window.scrollX,
        scroll_y: window.scrollY,
        pointer_type: "mouse",
        in_viewport: !document.hidden,
        payload: { deltaY },
      });
    };

    const onFocus = () => {
      this.record({
        event_type: "focus",
        in_viewport: true,
        payload: {},
      });
    };

    const onBlur = () => {
      this.record({
        event_type: "blur",
        in_viewport: false,
        payload: {},
      });
    };

    const onVisibility = () => {
      this.record({
        event_type: document.hidden ? "viewport_leave" : "viewport_enter",
        in_viewport: !document.hidden,
        payload: { visibilityState: document.visibilityState },
      });
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("click", onClick, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("focus", onFocus);
    window.addEventListener("blur", onBlur);
    document.addEventListener("visibilitychange", onVisibility);

    this.listeners.push(() => window.removeEventListener("mousemove", onMouseMove));
    this.listeners.push(() => window.removeEventListener("click", onClick));
    this.listeners.push(() => window.removeEventListener("scroll", onScroll));
    this.listeners.push(() => window.removeEventListener("focus", onFocus));
    this.listeners.push(() => window.removeEventListener("blur", onBlur));
    this.listeners.push(() => document.removeEventListener("visibilitychange", onVisibility));
  }

  private extractTargetInfo(target: EventTarget | null): {
    target_id?: string;
    target_tag?: string;
    target_class?: string;
  } {
    const element = target as HTMLElement | null;
    if (!element) {
      return {};
    }
    return {
      target_id: element.id || undefined,
      target_tag: element.tagName?.toLowerCase() || undefined,
      target_class: element.className || undefined,
    };
  }

  private record(event: Omit<TelemetryEvent, "sequence_no" | "ts_ms">) {
    this.sequenceNo += 1;
    this.bufferedEvents.push({
      sequence_no: this.sequenceNo,
      ts_ms: Date.now(),
      ...event,
    });

    this.onBufferedCount?.(this.bufferedEvents.length);

    if (this.bufferedEvents.length >= this.batchSize) {
      void this.flush();
    }
  }

  async flush() {
    if (this.isFlushing || this.bufferedEvents.length === 0) {
      return;
    }

    this.isFlushing = true;
    const batch = [...this.bufferedEvents];
    this.bufferedEvents = [];
    this.onBufferedCount?.(0);

    try {
      await this.onBatch(batch);
      this.onAcceptedCount?.(batch.length);
    } catch (error) {
      this.bufferedEvents = [...batch, ...this.bufferedEvents].slice(0, 300);
      this.onBufferedCount?.(this.bufferedEvents.length);
      this.onError?.(error);
    } finally {
      this.isFlushing = false;
    }
  }
}

```

## frontend\src\telemetry\fingerprint.ts

`$lang
import { FingerprintPayload } from "./types";

export function collectFingerprint(): FingerprintPayload {
  const nav = window.navigator as Navigator & {
    webdriver?: boolean;
    deviceMemory?: number;
  };

  const webdriver = Boolean(nav.webdriver);
  const userAgent = nav.userAgent || "unknown";
  const headlessHint = /Headless|PhantomJS|bot/i.test(userAgent);

  return {
    user_agent: userAgent,
    language: nav.language || "unknown",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "unknown",
    screen_width: window.screen.width,
    screen_height: window.screen.height,
    viewport_width: window.innerWidth,
    viewport_height: window.innerHeight,
    platform: nav.platform || "unknown",
    pointer_type: window.matchMedia("(pointer:fine)").matches ? "mouse" : "coarse",
    webdriver,
    headless_hint: headlessHint,
    hardware_concurrency: nav.hardwareConcurrency || 0,
    device_memory: nav.deviceMemory || 0,
  };
}

```

## frontend\src\telemetry\types.ts

`$lang
export type EventType =
  | "mousemove"
  | "click"
  | "scroll"
  | "focus"
  | "blur"
  | "viewport_enter"
  | "viewport_leave";

export type TelemetryEvent = {
  sequence_no: number;
  event_type: EventType;
  ts_ms: number;
  x?: number;
  y?: number;
  scroll_x?: number;
  scroll_y?: number;
  target_id?: string;
  target_tag?: string;
  target_class?: string;
  pointer_type?: string;
  in_viewport?: boolean;
  payload: Record<string, unknown>;
};

export type FingerprintPayload = {
  user_agent: string;
  language: string;
  timezone: string;
  screen_width: number;
  screen_height: number;
  viewport_width: number;
  viewport_height: number;
  platform: string;
  pointer_type: string;
  webdriver: boolean;
  headless_hint: boolean;
  hardware_concurrency: number;
  device_memory: number;
};

```


