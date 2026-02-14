"""
Tests para los modelos Pydantic de la API.

Cubre:
- Validación de QueryRequest (campos requeridos, max_length)
- ErrorResponse (formato RFC 7807)
- HealthResponse / QueryResponse (validación de estructura)
"""

import pytest
from pydantic import ValidationError
from api.models import (
    QueryRequest,
    QueryResponse,
    ErrorResponse,
    HealthResponse,
    SourceInfo,
)


class TestQueryRequest:
    """Validación de request entrante."""

    def test_request_valido(self):
        req = QueryRequest(user_id="+5491112345678", message="¿Qué planes ofrecen?")
        assert req.user_id == "+5491112345678"
        assert req.message == "¿Qué planes ofrecen?"

    def test_request_sin_user_id(self):
        with pytest.raises(ValidationError):
            QueryRequest(message="Hola")

    def test_request_sin_message(self):
        with pytest.raises(ValidationError):
            QueryRequest(user_id="user123")

    def test_request_message_muy_largo(self):
        with pytest.raises(ValidationError):
            QueryRequest(user_id="user123", message="x" * 501)

    def test_request_message_vacio(self):
        with pytest.raises(ValidationError):
            QueryRequest(user_id="user123", message="")

    def test_request_con_historial(self):
        req = QueryRequest(
            user_id="user123",
            message="Hola",
            conversation_history=[{"role": "user", "content": "Anterior"}],
        )
        assert req.conversation_history is not None
        assert len(req.conversation_history) == 1


class TestErrorResponse:
    """Modelo de error RFC 7807."""

    def test_error_response_completo(self):
        err = ErrorResponse(
            type="rate_limit",
            title="Rate Limit Exceeded",
            status=429,
            detail="Has excedido el límite.",
        )
        assert err.status == 429
        assert err.type == "rate_limit"

    def test_error_response_serializa_correctamente(self):
        err = ErrorResponse(
            type="validation_error",
            title="Bad Request",
            status=400,
            detail="Campo requerido faltante.",
        )
        data = err.model_dump()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data


class TestHealthResponse:
    """Modelo de health check."""

    def test_health_response_healthy(self):
        resp = HealthResponse(
            status="healthy",
            version="1.0.0",
            components={"database": "ok", "faiss_index": "ok (122 vectors)"},
        )
        assert resp.status == "healthy"
        assert "database" in resp.components
