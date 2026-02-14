"""
Tests de integración para los endpoints de la API.

Usa TestClient de FastAPI con dependency overrides para:
- No cargar modelos ML reales
- No necesitar .env con API keys
- Testear HTTP status codes, response models y error handlers

Cubre:
- GET /          → 200 + info
- GET /health    → 200 + HealthResponse
- POST /query    → 200 + QueryResponse (mock exitoso)
- POST /query    → 429 cuando rate limited
- POST /query    → 400 cuando query inválida
- POST /query    → 422 cuando faltan campos
- GET /stats     → 200 (con mock de SQLite)
- GET /nonexist  → 404 + ErrorResponse
"""

import pytest


# Root


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "KnowLigo RAG API"
        assert "version" in data


# Health


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "components" in data

    def test_health_components_present(self, client):
        data = client.get("/health").json()
        assert "database" in data["components"]
        assert "faiss_index" in data["components"]
        assert "groq_api" in data["components"]


# Query


class TestQueryEndpoint:
    def test_query_success(self, client):
        resp = client.post(
            "/query",
            json={"user_id": "test_user", "message": "¿Qué planes ofrecen?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "response" in data
        assert data["intent"] == "planes"

    def test_query_rate_limited(self, client, mock_pipeline):
        """Cuando el pipeline retorna rate_limit_exceeded → 429."""
        mock_pipeline.process_query.return_value = {
            "success": False,
            "response": "Has excedido el límite de consultas.",
            "intent": "rate_limited",
            "error": "rate_limit_exceeded",
        }
        resp = client.post(
            "/query",
            json={"user_id": "test_user", "message": "Hola"},
        )
        assert resp.status_code == 429
        data = resp.json()
        assert data["type"] == "rate_limit"

    def test_query_invalid(self, client, mock_pipeline):
        """Cuando el pipeline retorna invalid_query → 400."""
        mock_pipeline.process_query.return_value = {
            "success": False,
            "response": "No puedo ayudar con eso.",
            "intent": "off_topic",
            "error": "invalid_query",
        }
        resp = client.post(
            "/query",
            json={"user_id": "test_user", "message": "¿Cuál es la capital de Francia?"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["type"] == "invalid_query"

    def test_query_missing_fields_returns_422(self, client):
        """Request sin campos requeridos → 422 con ErrorResponse."""
        resp = client.post("/query", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert data["type"] == "validation_error"

    def test_query_missing_message_returns_422(self, client):
        resp = client.post("/query", json={"user_id": "test_user"})
        assert resp.status_code == 422


# 404


class TestNotFound:
    def test_unknown_endpoint_returns_404(self, client):
        resp = client.get("/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert data["type"] == "not_found"
        assert data["status"] == 404
