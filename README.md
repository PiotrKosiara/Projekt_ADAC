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

7a. Wizualizacja ruchu botów:

```bash
# Nagrywanie MP4 każdej sesji (działa w Dockerze)
docker compose exec bot_runner python main.py --scenario human_like --sessions 3 --record-video

# Pliki video pojawią się lokalnie w:
bot_runner/artifacts/videos

# W nagraniach kursor jest automatycznie wizualizowany (overlay).
# Możesz też wymusić overlay bez nagrywania:
# docker compose exec bot_runner python main.py --scenario linear --sessions 1 --show-cursor

# Tryb live (okno przeglądarki) - uruchom lokalnie poza kontenerem:
# python bot_runner/main.py --scenario human_like --sessions 1 --headed --slow-mo-ms 60 --target-url http://localhost:5173
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
