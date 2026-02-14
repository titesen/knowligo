"""
Configuración compartida de fixtures para los tests de KnowLigo.

Provee:
- Settings de prueba (sin necesidad de .env real)
- Mock del pipeline RAG
- TestClient de FastAPI con dependency overrides
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Agregar raíz del proyecto al path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from api.config import Settings, get_settings
from api.main import app, get_pipeline


# Settings de prueba


@pytest.fixture
def test_settings() -> Settings:
    """Settings con valores seguros para testing (no necesita .env)."""
    return Settings(
        GROQ_API_KEY="test-key-fake-12345",
        LLM_MODEL="llama-3.3-70b-versatile",
        EMBEDDING_MODEL="paraphrase-multilingual-MiniLM-L12-v2",
        RERANK_ENABLED=False,  # Desactivar para tests rápidos
        CACHE_ENABLED=False,
        MAX_QUERIES_PER_HOUR=100,
        DATABASE_PATH="database/sqlite/knowligo.db",
        WHATSAPP_VERIFY_TOKEN="test_token_123",
    )


# Mock Pipeline


def _make_mock_pipeline():
    """Crea un mock del pipeline que retorna respuestas predecibles."""
    mock = MagicMock()

    # Simular process_query exitoso
    mock.process_query.return_value = {
        "success": True,
        "response": "KnowLigo ofrece planes Basic, Professional y Enterprise.",
        "intent": "planes",
        "intent_confidence": 0.95,
        "sources": [{"file": "plans.md", "section": "Planes", "score": 0.23}],
        "tokens_used": 120,
        "processing_time": 1.5,
    }

    # Simular componentes de health check
    mock.db_path = project_root / "database" / "sqlite" / "knowligo.db"
    mock.retriever = MagicMock()
    mock.retriever.index.ntotal = 122
    mock.responder = MagicMock()
    mock.responder.client.api_key = "test-key"

    return mock


@pytest.fixture
def mock_pipeline():
    """Fixture que provee un mock del pipeline."""
    return _make_mock_pipeline()


# TestClient con DI overrides


@pytest.fixture
def client(test_settings, mock_pipeline) -> TestClient:
    """
    TestClient de FastAPI con dependency overrides.

    Reemplaza las dependencias reales por mocks:
    - get_settings → test_settings (sin .env)
    - get_pipeline → mock_pipeline (sin cargar modelos)
    """
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    # Limpiar overrides después del test
    app.dependency_overrides.clear()
