"""
Tests para agent/orchestrator.py — Orquestador principal.

Usa mocks para el router LLM y el pipeline RAG,
pero DB real en memoria para conversaciones y datos.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agent.orchestrator import AgentOrchestrator, normalize_phone
from agent.router import AgentIntent

_SCHEMA_PATH = project_root / "database" / "schema" / "schema.sql"
_SEED_PATH = project_root / "database" / "seeds" / "seed.sql"


# Fixtures


@pytest.fixture
def seeded_db(tmp_path):
    """DB temporal con schema + seeds. Retorna path."""
    db_file = tmp_path / "test.db"
    import sqlite3

    conn = sqlite3.connect(db_file)
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    with open(_SEED_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()
    return db_file


@pytest.fixture
def orchestrator(seeded_db):
    """Orchestrator con DB real pero router y RAG mockeados."""
    with patch("agent.orchestrator.IntentRouter") as MockRouter:
        mock_router_instance = MagicMock()
        mock_router_instance.classify.return_value = {
            "intent": AgentIntent.SALUDO,
            "confidence": 0.95,
        }
        MockRouter.return_value = mock_router_instance

        orch = AgentOrchestrator(
            db_path=seeded_db,
            groq_api_key="test-key-fake",
            llm_model="llama-3.3-70b-versatile",
            rag_pipeline=None,
        )
        # Expose mock for test control
        orch._mock_router = mock_router_instance

        # Inject a mock RAG pipeline
        mock_rag = MagicMock()
        mock_rag.process_query.return_value = {
            "success": True,
            "response": "Respuesta RAG de prueba.",
        }
        orch.set_rag_pipeline(mock_rag)

        yield orch


# Phone normalization


class TestNormalizePhone:
    def test_already_clean(self):
        assert normalize_phone("5493794285297") == "5493794285297"

    def test_with_plus_and_spaces(self):
        assert normalize_phone("+54 9 3794 28-5297") == "5493794285297"

    def test_with_dashes(self):
        assert normalize_phone("549-3794-285297") == "5493794285297"


# Orchestrator Flow


class TestOrchestratorSaludo:
    def test_saludo_registered_client(self, orchestrator):
        """Saludo de cliente registrado incluye su nombre."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.SALUDO,
            "confidence": 0.95,
        }
        resp = orchestrator.process_message("5493794285297", "Hola")
        assert "Facundo" in resp
        assert "KnowLigo" in resp

    def test_saludo_unregistered_client(self, orchestrator):
        """Saludo de número desconocido sugiere registro."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.SALUDO,
            "confidence": 0.95,
        }
        resp = orchestrator.process_message("5491199990000", "Hola")
        assert "registrar" in resp.lower()


class TestOrchestratorRegistration:
    def test_registrar_keyword_starts_flow(self, orchestrator):
        """Escribir 'registrar' inicia el flujo de registro."""
        resp = orchestrator.process_message("5491199990000", "registrar")
        assert "nombre" in resp.lower()

    def test_registrar_existing_client(self, orchestrator):
        """Cliente existente que escribe 'registrar' recibe aviso."""
        resp = orchestrator.process_message("5493794285297", "registrar")
        assert "registrado" in resp.lower()

    def test_full_registration_flow(self, orchestrator):
        """Flujo completo de registro en 3 pasos."""
        phone = "5491199990000"

        # Paso 1: iniciar
        resp = orchestrator.process_message(phone, "registrar")
        assert "nombre" in resp.lower()

        # Paso 2: nombre
        resp = orchestrator.process_message(phone, "Juan Pérez")
        assert "empresa" in resp.lower()

        # Paso 3: empresa
        resp = orchestrator.process_message(phone, "Mi Empresa SA")
        assert "email" in resp.lower() or "correo" in resp.lower()

        # Paso 4: email
        resp = orchestrator.process_message(phone, "juan@miempresa.com")
        assert "completado" in resp.lower() or "registro" in resp.lower()

        # Verificar que ahora está registrado
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.SALUDO,
            "confidence": 0.95,
        }
        resp = orchestrator.process_message(phone, "Hola")
        assert "Juan" in resp


class TestOrchestratorTickets:
    def test_ver_tickets(self, orchestrator):
        """Ver tickets de cliente registrado."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.VER_TICKETS,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("5493794285297", "Mis tickets")
        assert "ticket" in resp.lower()

    def test_ver_tickets_unregistered(self, orchestrator):
        """Número no registrado recibe prompt de registro."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.VER_TICKETS,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("5491199990000", "Mis tickets")
        assert "registrado" in resp.lower()

    def test_create_ticket_flow(self, orchestrator):
        """Flujo completo de creación de ticket."""
        phone = "5493794285297"

        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CREAR_TICKET,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message(phone, "Quiero crear un ticket")
        assert "asunto" in resp.lower()

        resp = orchestrator.process_message(phone, "VPN no funciona")
        assert "detalle" in resp.lower() or "describa" in resp.lower()

        resp = orchestrator.process_message(
            phone,
            "La VPN corporativa no conecta desde hoy a la mañana, da error de timeout",
        )
        assert "prioridad" in resp.lower()

        resp = orchestrator.process_message(phone, "Alta")
        assert "ticket" in resp.lower()
        assert "#" in resp


class TestOrchestratorPlanes:
    def test_ver_planes(self, orchestrator):
        """Ver planes no requiere registro."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.VER_PLANES,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("5491199990000", "Planes")
        assert "Básico" in resp
        assert "Profesional" in resp
        assert "Empresarial" in resp


class TestOrchestratorRAG:
    def test_consulta_rag_delegates(self, orchestrator):
        """Consulta informativa se delega al RAG pipeline."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CONSULTA_RAG,
            "confidence": 0.8,
        }
        resp = orchestrator.process_message(
            "5493794285297", "¿Cuál es el horario de soporte?"
        )
        assert resp == "Respuesta RAG de prueba."


class TestOrchestratorCancelacion:
    def test_cancelar_during_flow(self, orchestrator):
        """Cancelar durante un flujo activo lo resetea."""
        phone = "5491199990000"
        orchestrator.process_message(phone, "registrar")
        resp = orchestrator.process_message(phone, "cancelar")
        assert "cancelada" in resp.lower()

    def test_cancelar_no_flow(self, orchestrator):
        """Cancelar sin flujo activo da mensaje apropiado."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CANCELAR,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("5493794285297", "cancelar")
        assert "ninguna operación" in resp.lower()


class TestOrchestratorFueraDeTema:
    def test_fuera_de_tema(self, orchestrator):
        """Tema fuera de ámbito da respuesta de rechazo cortés."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.FUERA_DE_TEMA,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("5493794285297", "¿Quién ganó el mundial?")
        assert "soporte IT" in resp.lower() or "knowligo" in resp.lower()
