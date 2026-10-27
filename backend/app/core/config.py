import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "MineGuard-AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    DATABASE_URL: str = "sqlite:///./data/mineguard.db"

    # MQTT
    MQTT_ENABLED: bool = False
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_TOPIC_PREFIX: str = "mineguard"
    MQTT_TLS_ENABLED: bool = False
    MQTT_KEEPALIVE: int = 60

    # Geotechnical Demonstration Thresholds (SI Units)
    TILT_WARNING_DEG: float = 2.0
    TILT_CRITICAL_DEG: float = 5.0
    DISPLACEMENT_WARNING_MM: float = 15.0
    DISPLACEMENT_CRITICAL_MM: float = 30.0
    RATE_WARNING_MM_HR: float = 2.0
    RATE_CRITICAL_MM_HR: float = 5.0
    ACCEL_WARNING_MM_HR2: float = 0.5
    VIBRATION_WARNING_MS2: float = 3.0
    VIBRATION_CRITICAL_MS2: float = 8.0
    BATTERY_LOW_PCT: float = 20.0
    STALE_DATA_TIMEOUT_SEC: int = 120

    # Machine Learning / Anomaly Detection
    ML_ANOMALY_ENABLED: bool = True
    ML_CONTAMINATION: float = 0.05
    ML_MIN_SAMPLES_TRAIN: int = 30

    # Simulator
    SIMULATOR_AUTOSTART: bool = False
    SIMULATOR_DEFAULT_INTERVAL_SEC: float = 3.0
    SIMULATOR_DEFAULT_NODES: int = 6
    SIMULATOR_RANDOM_SEED: int = 42

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                return ["http://localhost:5173", "http://127.0.0.1:5173"]
        return v


settings = Settings()
