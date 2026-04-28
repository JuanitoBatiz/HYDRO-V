from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):

    # ── Aplicación ────────────────────────────────────────────────
    APP_NAME:        str  = "Hydro-V Backend"
    APP_VERSION:     str  = "1.0.0"
    DEBUG:           bool = False
    ENVIRONMENT:     str  = "development"  # development | staging | production

    # ── PostgreSQL ────────────────────────────────────────────────
    POSTGRES_HOST:     str = "localhost"
    POSTGRES_PORT:     int = 5432
    POSTGRES_USER:     str = "hydrov"
    POSTGRES_PASSWORD: str
    POSTGRES_DB:       str = "hydrov"

    @property
    def POSTGRES_DSN(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def POSTGRES_DSN_SYNC(self) -> str:
        # Para Alembic, que no es async
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── InfluxDB ──────────────────────────────────────────────────
    INFLUX_URL:             str = "http://localhost:8086"
    INFLUX_TOKEN:           str
    INFLUX_ORG:             str = "hydrov"
    INFLUX_BUCKET_TELEMETRY: str = "sensor_telemetry"
    INFLUX_BUCKET_NASA:      str = "nasa_weather_cache"

    # ── Redis ─────────────────────────────────────────────────────
    REDIS_HOST:     str = "localhost"
    REDIS_PORT:     int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB:       int = 0

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── MQTT / HiveMQ Cloud ───────────────────────────────────────
    MQTT_HOST:     str
    MQTT_PORT:     int  = 8883
    MQTT_USER:     str
    MQTT_PASSWORD: str
    MQTT_TOPIC_TELEMETRY: str = "hydrov/+/telemetry"
    MQTT_TOPIC_COMMANDS:  str = "hydrov/{node_id}/commands"
    MQTT_CLIENT_ID:       str = "hydrov-backend"

    # ── NASA POWER ────────────────────────────────────────────────
    NASA_POWER_BASE_URL:  str   = "https://power.larc.nasa.gov"
    NASA_COMMUNITY:       str   = "SB"
    NASA_TIME_STANDARD:   str   = "LST"
    NASA_DEFAULT_LAT:     float = 19.4136   # Nezahualcóyotl
    NASA_DEFAULT_LON:     float = -99.0151
    NASA_REQUEST_TIMEOUT: int   = 60        # segundos

    # ── Schedulers NASA POWER ─────────────────────────────────────
    NASA_SCHEDULER_HOURLY_INTERVAL:  int = 1    # cada N horas
    NASA_SCHEDULER_DAILY_CRON_HOUR:  int = 6    # 06:00 LST
    NASA_CACHE_TTL_SECONDS:          int = 7200  # 2 horas en Redis

    # ── Seguridad / JWT ───────────────────────────────────────────
    SECRET_KEY:             str
    ALGORITHM:              str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── API Key para servicios internos (Grafana → Backend) ───────
    # Permite acceso server-to-server sin JWT interactivo.
    # Enviar como header: X-API-Key: <valor>
    GRAFANA_API_KEY: str = "hydrov_grafana_secret_2026"

    # ── CORS ──────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",   # React dev
        "http://localhost:5173",   # Vite dev
        "http://192.168.68.67",    # Local network testing
        "http://192.168.68.67:5173", # Local network testing (Vite)
    ]

    # ── WebSockets ────────────────────────────────────────────────
    WS_ALERT_CHANNEL: str = "alerts:{node_id}"  # canal Redis pub/sub

    class Config:
        env_file          = ".env"
        env_file_encoding = "utf-8"
        case_sensitive    = True
        extra             = "ignore"   # Ignora vars del .env no declaradas (ej. REDIS_URL calculada como @property)


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()