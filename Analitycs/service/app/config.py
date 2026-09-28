"""
Configuración centralizada (config/). Nunca hardcodear credenciales:
todo se lee de variables de entorno (ver Analitycs/.env.example).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "anti_procrastinacion"
    postgres_user: str = "analytics_user"
    postgres_password: str = "changeme"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # TTLs de cache (segundos) — PostgreSQL nunca lleva TTL, Redis sí.
    cache_ttl_default: int = 600   # 10 min: métricas agregadas normales
    cache_ttl_realtime: int = 300  # 5 min: usuarios activos por día
    cache_ttl_slow: int = 900      # 15 min: distribuciones que cambian poco (género, país)

    # Firebase (ETL)
    firebase_credentials_path: str = "./firebase-service-account.json"

    # Entorno / Swagger (FR-032, T005) — controla si /docs, /redoc y /openapi.json
    # se exponen. Seguro-por-defecto: solo "development"/"qa" habilitan Swagger.
    environment: str = "development"

    # Autenticacion de administrador definitivo (FR-020, FR-002). Un unico admin
    # con credenciales fijas leidas de variables de entorno, sin tabla en PostgreSQL.
    admin_username: str
    admin_password_hash: str

    # Login de prueba EXCLUSIVO para Swagger (FR-031) — separado del admin real,
    # comparacion directa sin hash (relajacion explicita permitida solo aqui).
    test_admin_user: str
    test_admin_password: str

    # Zona horaria por defecto si el cliente no envia X-Client-Timezone (research.md §2).
    default_client_timezone: str = "UTC"

    # Secreto compartido para el endpoint interno de invalidacion de cache,
    # llamado por el ETL tras cada corrida (FR-022, research.md §3).
    etl_cache_invalidation_secret: str

    @property
    def postgres_dsn(self) -> str:
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password}"
        )


settings = Settings()
