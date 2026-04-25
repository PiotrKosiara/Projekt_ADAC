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
