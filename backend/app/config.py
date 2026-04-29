"""
Configuración central de la aplicación mediante variables de entorno.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://sgs_user:sgs_pass@localhost:5432/sgs_dev"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Seguridad JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # IA externa (research/deep research)
    IA_RESEARCH_PROVIDER: str = "anthropic"
    IA_RESEARCH_MODEL: str = "claude-sonnet-4-20250514"
    IA_RESEARCH_MODEL_ANTHROPIC: str = "claude-sonnet-4-20250514"
    IA_RESEARCH_MODEL_OPENAI: str = "gpt-4.1"
    IA_RESEARCH_MODEL_GEMINI: str = "gemini-2.5-pro"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # IA local/privada (operación diaria)
    OLLAMA_URL: str = "http://76.13.9.183:32768"
    OLLAMA_MODEL_DEFAULT: str = "qwen2.5-coder:1.5b"

    # Transcripción de audio (faster-whisper: tiny | base | small | medium)
    WHISPER_MODELO: str = "tiny"

    # Almacenamiento de ficheros (MinIO / S3-compatible)
    MINIO_URL: str = "http://localhost:9000"
    # URL pública para presigned URLs (la que ve el navegador).
    # En producción debe ser la IP/dominio público del servidor.
    # Si no se define, se usa MINIO_URL (válido solo en desarrollo).
    MINIO_PUBLIC_URL: str = ""
    MINIO_ACCESS_KEY: str = "sgs_minio"
    MINIO_SECRET_KEY: str = "sgs_minio_pass"
    MINIO_BUCKET: str = "sgs-documentos"

    # App
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3033",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3033",
        "http://localhost:5173",
        "http://frontend:3000",
    ]
    LOG_LEVEL: str = "INFO"


configuracion = Configuracion()
