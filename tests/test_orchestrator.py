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
        """Saludo de cliente registrado devuelve saludo + menú adaptativo."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.SALUDO,
            "confidence": 0.95,
        }
        resp = orchestrator.process_message("5493794285297", "Hola")
        # Debe incluir menú con opciones de cliente registrado
        assert "Menú de opciones" in resp
        assert "Ver planes" in resp
        assert "Crear ticket" in resp
        assert "Mi cuenta" in resp

    def test_saludo_unregistered_client(self, orchestrator):
        """Saludo de número desconocido devuelve saludo + menú reducido."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.SALUDO,
            "confidence": 0.95,
        }
        resp = orchestrator.process_message("5491199990000", "Hola")
        # Debe incluir menú con opciones de no-registrado
        assert "Menú de opciones" in resp
        assert "Registrarme" in resp
        assert "Ver planes" in resp
        # NO debe incluir opciones de registrado
        assert "Mi cuenta" not in resp
        assert "Crear ticket" not in resp


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
        # Con LLM real mencionaría Juan; menú incluye opciones de registrado
        assert "Menú de opciones" in resp


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

    def test_cancelar_no_quiero(self, orchestrator):
        """'No quiero' cancela un flujo activo."""
        phone = "5491199990000"
        orchestrator.process_message(phone, "registrar")
        resp = orchestrator.process_message(phone, "no quiero")
        assert "cancelada" in resp.lower()

    def test_cancelar_mejor_no(self, orchestrator):
        """'Mejor no' cancela un flujo activo."""
        phone = "5491199990000"
        orchestrator.process_message(phone, "registrar")
        resp = orchestrator.process_message(phone, "mejor no")
        assert "cancelada" in resp.lower()

    def test_cancelar_substring_cancela_el_ticket(self, orchestrator):
        """'Cancela el ticket' cancela un flujo activo (substring match)."""
        phone = "5493794285297"
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CREAR_TICKET,
            "confidence": 0.9,
        }
        orchestrator.process_message(phone, "Quiero crear un ticket")
        resp = orchestrator.process_message(phone, "cancela el ticket")
        assert "cancelada" in resp.lower()

    def test_cancelar_substring_no_dejalo(self, orchestrator):
        """'No, dejalo' cancela un flujo activo (substring match)."""
        phone = "5491199990000"
        orchestrator.process_message(phone, "registrar")
        resp = orchestrator.process_message(phone, "No, dejalo")
        assert "cancelada" in resp.lower()

    def test_cancelar_substring_no_quiero_crear(self, orchestrator):
        """'No quiero crear el ticket cancela' cancela (substring match)."""
        phone = "5493794285297"
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CREAR_TICKET,
            "confidence": 0.9,
        }
        orchestrator.process_message(phone, "Quiero crear un ticket")
        resp = orchestrator.process_message(phone, "No quiero crear el ticket cancela")
        assert "cancelada" in resp.lower()


class TestCancelHintInFlows:
    """Verifica que los prompts de flujo incluyan el hint de cancelación."""

    def test_registration_shows_cancel_hint(self, orchestrator):
        phone = "5491199990000"
        resp = orchestrator.process_message(phone, "registrar")
        assert "cancelar" in resp.lower()

    def test_ticket_shows_cancel_hint(self, orchestrator):
        phone = "5493794285297"
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CREAR_TICKET,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message(phone, "Quiero crear un ticket")
        assert "cancelar" in resp.lower()


class TestCasualExpressions:
    """Expresiones casuales (emoticones, risas) dan respuesta breve."""

    def test_smiley(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", ":)")
        assert "necesitás" in resp.lower() or "😊" in resp

    def test_jajaja(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "jajaja")
        assert "necesitás" in resp.lower() or "😊" in resp

    def test_xd(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "xD")
        assert "necesitás" in resp.lower() or "😊" in resp


class TestSinglePlanEnforcement:
    """Cada cliente solo puede tener un plan activo."""

    def test_client_with_active_plan_blocked(self, orchestrator):
        """Cliente con plan activo NO puede contratar otro."""
        # Acme Corp (client 1) tiene Plan Profesional activo
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CONTRATAR_PLAN,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("541143210001", "Quiero contratar un plan")
        assert "ya tenés" in resp.lower() or "plan activo" in resp.lower()
        assert "interfaz web" in resp.lower()

    def test_client_without_plan_can_contract(self, orchestrator):
        """Cliente sin plan activo SÍ puede iniciar contratación (Demo Facundo)."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CONTRATAR_PLAN,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("5493794285297", "Quiero contratar")
        # Debe mostrar los planes disponibles
        assert "Básico" in resp or "plan" in resp.lower()


class TestOrchestratorFueraDeTema:
    def test_fuera_de_tema(self, orchestrator):
        """Tema fuera de ámbito da respuesta de rechazo cortés."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.FUERA_DE_TEMA,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("5493794285297", "¿Quién ganó el mundial?")
        assert "soporte IT" in resp.lower() or "knowligo" in resp.lower()


# Fuzzy priority parsing


class TestFuzzyPriority:
    """Tests para _parse_priority con lenguaje natural."""

    def test_exact_match(self):
        from agent.handlers import _parse_priority

        assert _parse_priority("baja") == "Baja"
        assert _parse_priority("Alta") == "Alta"
        assert _parse_priority("crítica") == "Crítica"
        assert _parse_priority("critica") == "Crítica"

    def test_fuzzy_urgent(self):
        from agent.handlers import _parse_priority

        assert _parse_priority("es urgente") == "Crítica"
        assert _parse_priority("muy urgente") == "Crítica"
        assert _parse_priority("emergencia") == "Crítica"
        assert _parse_priority("urgente") == "Alta"

    def test_fuzzy_low(self):
        from agent.handlers import _parse_priority

        assert _parse_priority("puede esperar") == "Baja"
        assert _parse_priority("no es grave") == "Baja"

    def test_fuzzy_high(self):
        from agent.handlers import _parse_priority

        assert _parse_priority("bastante importante") == "Alta"

    def test_unrecognized(self):
        from agent.handlers import _parse_priority

        assert _parse_priority("azul") is None


# Plan selection parsing


class TestPlanSelection:
    """Tests para _parse_plan_selection con texto libre."""

    def test_by_number(self, orchestrator):
        from agent.handlers import _parse_plan_selection

        plan = _parse_plan_selection("1", orchestrator._db)
        assert plan is not None
        assert plan["name"] == "Básico"

    def test_by_name(self, orchestrator):
        from agent.handlers import _parse_plan_selection

        plan = _parse_plan_selection("el profesional", orchestrator._db)
        assert plan is not None
        assert plan["name"] == "Profesional"

    def test_by_name_empresarial(self, orchestrator):
        from agent.handlers import _parse_plan_selection

        plan = _parse_plan_selection("empresarial", orchestrator._db)
        assert plan is not None
        assert plan["name"] == "Empresarial"

    def test_invalid(self, orchestrator):
        from agent.handlers import _parse_plan_selection

        plan = _parse_plan_selection("el mejor", orchestrator._db)
        assert plan is None


# Adaptive Menu


class TestAdaptiveMenu:
    """Verifica que el menú se adapte según el tipo de usuario."""

    def test_menu_keyword_registered(self, orchestrator):
        """Escribir 'menú' devuelve menú sin pasar por el router."""
        resp = orchestrator.process_message("5493794285297", "menú")
        assert "Menú de opciones" in resp
        assert "Crear ticket" in resp
        assert "Mi cuenta" in resp
        # Router no debe haber sido llamado
        orchestrator._mock_router.classify.assert_not_called()

    def test_menu_keyword_unregistered(self, orchestrator):
        """Escribir 'menú' sin estar registrado muestra menú reducido."""
        resp = orchestrator.process_message("5491199990000", "menú")
        assert "Menú de opciones" in resp
        assert "Registrarme" in resp
        assert "Crear ticket" not in resp

    def test_menu_keyword_opciones(self, orchestrator):
        """'opciones' también activa el menú."""
        resp = orchestrator.process_message("5493794285297", "opciones")
        assert "Menú de opciones" in resp

    def test_menu_keyword_ayuda(self, orchestrator):
        """'ayuda' también activa el menú."""
        resp = orchestrator.process_message("5493794285297", "ayuda")
        assert "Menú de opciones" in resp


# Gibberish Detection


class TestGibberishDetection:
    """Verifica que entradas sin sentido reciban respuesta amable."""

    def test_single_dot(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", ".")
        assert "no entendí" in resp.lower()
        assert "menú" in resp.lower()

    def test_random_chars(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "dafasdf")
        assert "no entendí" in resp.lower()

    def test_mixed_digits_chars(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "23129fdagf")
        assert "no entendí" in resp.lower()

    def test_question_marks_only(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "???")
        assert "no entendí" in resp.lower()

    def test_exclamation_only(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "!!!")
        assert "no entendí" in resp.lower()

    def test_consonant_soup(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "bcdfghjk")
        assert "no entendí" in resp.lower()

    def test_valid_short_words_pass_through(self, orchestrator):
        """Words like 'si', 'no', 'ok' should NOT be gibberish."""
        from agent.orchestrator import AgentOrchestrator

        orch = orchestrator
        assert not orch._is_gibberish("si")
        assert not orch._is_gibberish("no")
        assert not orch._is_gibberish("ok")
        assert not orch._is_gibberish("hola")

    def test_normal_text_not_gibberish(self, orchestrator):
        """Normal Spanish text should not be gibberish."""
        assert not orchestrator._is_gibberish("quiero un plan")
        assert not orchestrator._is_gibberish("ver tickets")
        assert not orchestrator._is_gibberish("buenos días")


# Interaction Logging


class TestInteractionLogging:
    """Verifica que TODAS las interacciones se registren en query_logs."""

    def test_greeting_logged(self, orchestrator, seeded_db):
        """Un saludo debe quedar registrado en query_logs."""
        import sqlite3

        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.SALUDO,
            "confidence": 0.95,
        }
        orchestrator.process_message("5493794285297", "Hola")

        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM query_logs WHERE user_id = '5493794285297'"
        ).fetchall()
        conn.close()

        assert len(rows) >= 1
        last = dict(rows[-1])
        assert last["query"] == "Hola"
        assert last["intent"] == "SALUDO"

    def test_menu_keyword_logged(self, orchestrator, seeded_db):
        """Escribir 'menú' debe quedar registrado."""
        import sqlite3

        orchestrator.process_message("5493794285297", "menú")

        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM query_logs WHERE user_id = '5493794285297' AND intent = 'MENU'"
        ).fetchall()
        conn.close()

        assert len(rows) >= 1

    def test_gibberish_logged(self, orchestrator, seeded_db):
        """Gibberish debe quedar registrado con intent GIBBERISH."""
        import sqlite3

        orchestrator.process_message("5493794285297", "dafasdf")

        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM query_logs WHERE user_id = '5493794285297' AND intent = 'GIBBERISH'"
        ).fetchall()
        conn.close()

        assert len(rows) >= 1


# Smart Greeting Recency


class TestGreetingRecency:
    """Verifica que un segundo saludo reciente omita el saludo largo."""

    def test_recent_greeting_shows_short(self, orchestrator):
        """Segundo saludo dentro de 30 min muestra mensaje breve."""
        phone = "5493794285297"
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.SALUDO,
            "confidence": 0.95,
        }
        # Primer saludo: full menu
        resp1 = orchestrator.process_message(phone, "Hola")
        assert "Menú de opciones" in resp1

        # Segundo saludo inmediato: should be short + menu
        resp2 = orchestrator.process_message(phone, "Hola")
        assert "De vuelta" in resp2 or "menú" in resp2.lower()
