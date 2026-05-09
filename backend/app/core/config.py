from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

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
