"""
Configuración centralizada de KnowLigo.

Usa Pydantic BaseSettings para:
- Validar TODAS las variables de entorno al startup
- Proveer tipos seguros y defaults documentados
- Fallar rápido si falta config crítica (GROQ_API_KEY)
- Eliminar load_dotenv() disperso en múltiples módulos

Referencia: FastAPI Best Practices 2026 §2.1 - Pydantic BaseSettings
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# Raíz del proyecto (donde vive .env)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuración tipada y validada del proyecto KnowLigo."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",  # Ignorar env vars no declaradas
    )

    # LLM / Groq
    GROQ_API_KEY: str  # Requerida — falla al startup si falta
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # Embeddings
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # Reranking
    RERANK_ENABLED: bool = True
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANK_TOP_N: int = 5

    # Semantic Cache
    CACHE_ENABLED: bool = True
    CACHE_THRESHOLD: float = 0.92
    CACHE_TTL_SECONDS: int = 3600
    CACHE_MAX_SIZE: int = 100

    # Retrieval
    TOP_K_RETRIEVAL: int = 15
    MAX_QUERIES_PER_HOUR: int = 30
    MAX_MESSAGE_LENGTH: int = 300
    QUERY_REWRITE_ENABLED: bool = True

    # WhatsApp
    WHATSAPP_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: str = "knowligo_webhook_2026"

    # Database
    DATABASE_PATH: str = "database/sqlite/knowligo.db"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    @property
    def db_full_path(self) -> Path:
        """Ruta absoluta a la base de datos."""
        db = Path(self.DATABASE_PATH)
        if db.is_absolute():
            return db
        return PROJECT_ROOT / db


@lru_cache
def get_settings() -> Settings:
    """
    Singleton de configuración (cacheado).

    Falla inmediatamente si faltan variables requeridas (GROQ_API_KEY),
    dando un error claro al startup en lugar de fallar en runtime.
    """
    return Settings()
