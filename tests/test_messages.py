"""
Tests para agent/messages.py — Modelos de mensajes interactivos de WhatsApp.

Cubre:
- TextMessage, ListMessage, ButtonMessage: serialización a texto y a payload
- to_text() helper con str, TextMessage, ListMessage, ButtonMessage
- Validación de límites de WhatsApp (títulos, filas, botones)
- Integración con orchestrator y handlers (retornan tipos correctos)
"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agent.messages import (
    AgentResponse,
    ButtonMessage,
    ListMessage,
    ListRow,
    ListSection,
    ReplyButton,
    TextMessage,
    to_text,
)
from agent.router import AgentIntent


# to_text helper


class TestToText:
    """Verificar que to_text() serialice correctamente cualquier AgentResponse."""

    def test_str_passthrough(self):
        assert to_text("Hola mundo") == "Hola mundo"

    def test_text_message(self):
        msg = TextMessage(body="Respuesta simple")
        assert to_text(msg) == "Respuesta simple"

    def test_list_message_basic(self):
        msg = ListMessage(
            body="¿En qué puedo ayudarte?",
            button_text="Ver opciones",
            header="Menú",
            sections=[
                ListSection(
                    title="Opciones",
                    rows=[
                        ListRow("opt1", "Opción 1", "Desc 1"),
                        ListRow("opt2", "Opción 2"),
                    ],
                ),
            ],
        )
        text = to_text(msg)
        assert "Menú" in text
        assert "Opción 1" in text
        assert "Desc 1" in text
        assert "Opción 2" in text

    def test_button_message_basic(self):
        msg = ButtonMessage(
            body="¿Confirmar?",
            buttons=[
                ReplyButton("yes", "Sí"),
                ReplyButton("no", "No"),
            ],
        )
        text = to_text(msg)
        assert "¿Confirmar?" in text
        assert "Sí" in text
        assert "No" in text


# WhatsApp payload generation


class TestListMessagePayload:
    """Verificar payload de Interactive List para la API de WhatsApp."""

    def test_payload_structure(self):
        msg = ListMessage(
            body="Seleccione una opción:",
            button_text="Ver opciones",
            header="Menú principal",
            footer="Escribí cancelar para salir",
            sections=[
                ListSection(
                    title="Servicios",
                    rows=[
                        ListRow("ver_planes", "Ver planes", "Conocé nuestros planes"),
                        ListRow("consultar", "Consultar", "Preguntame"),
                    ],
                ),
            ],
        )
        payload = msg.to_whatsapp_payload()
        assert payload["type"] == "list"
        assert payload["body"]["text"] == "Seleccione una opción:"
        assert payload["action"]["button"] == "Ver opciones"
        assert payload["header"]["text"] == "Menú principal"
        assert payload["footer"]["text"] == "Escribí cancelar para salir"

        sections = payload["action"]["sections"]
        assert len(sections) == 1
        assert sections[0]["title"] == "Servicios"
        assert len(sections[0]["rows"]) == 2
        assert sections[0]["rows"][0]["id"] == "ver_planes"
        assert sections[0]["rows"][0]["title"] == "Ver planes"
        assert sections[0]["rows"][0]["description"] == "Conocé nuestros planes"

    def test_title_truncation(self):
        """WhatsApp limita títulos a 24 chars — deben truncarse."""
        msg = ListMessage(
            body="Body",
            button_text="Este botón tiene más de veinte chars",
            sections=[
                ListSection(
                    title="Sección con título muy largo extra",
                    rows=[
                        ListRow("id", "Título que excede veinticuatro caracteres largo"),
                    ],
                ),
            ],
        )
        payload = msg.to_whatsapp_payload()
        assert len(payload["action"]["button"]) <= 20
        assert len(payload["action"]["sections"][0]["title"]) <= 24
        assert len(payload["action"]["sections"][0]["rows"][0]["title"]) <= 24


class TestButtonMessagePayload:
    """Verificar payload de Reply Buttons para la API de WhatsApp."""

    def test_payload_structure(self):
        msg = ButtonMessage(
            body="¿Confirma la contratación?",
            buttons=[
                ReplyButton("confirmar_si", "✅ Sí, confirmo"),
                ReplyButton("confirmar_no", "❌ No, cancelar"),
            ],
            footer="Cancelá con cancelar",
        )
        payload = msg.to_whatsapp_payload()
        assert payload["type"] == "button"
        assert payload["body"]["text"] == "¿Confirma la contratación?"
        assert len(payload["action"]["buttons"]) == 2
        assert payload["action"]["buttons"][0]["type"] == "reply"
        assert payload["action"]["buttons"][0]["reply"]["id"] == "confirmar_si"
        assert payload["footer"]["text"] == "Cancelá con cancelar"

    def test_max_three_buttons(self):
        """WhatsApp limita a 3 botones — los extras se descartan."""
        msg = ButtonMessage(
            body="Muchas opciones",
            buttons=[
                ReplyButton(f"btn_{i}", f"Botón {i}")
                for i in range(5)
            ],
        )
        payload = msg.to_whatsapp_payload()
        assert len(payload["action"]["buttons"]) == 3


# Integration: Orchestrator returns correct types


class TestOrchestratorInteractiveTypes:
    """Verificar que el orchestrator retorna ListMessage/ButtonMessage donde corresponde."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Orchestrator con DB real pero router y RAG mockeados."""
        from unittest.mock import MagicMock, patch
        from agent.orchestrator import AgentOrchestrator

        _SCHEMA_PATH = project_root / "database" / "schema" / "schema.sql"
        _SEED_PATH = project_root / "database" / "seeds" / "seed.sql"

        db_file = tmp_path / "test.db"
        import sqlite3

        conn = sqlite3.connect(db_file)
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        with open(_SEED_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        with patch("agent.orchestrator.IntentRouter") as MockRouter:
            mock_router_instance = MagicMock()
            mock_router_instance.classify.return_value = {
                "intent": AgentIntent.SALUDO,
                "confidence": 0.95,
            }
            MockRouter.return_value = mock_router_instance

            orch = AgentOrchestrator(
                db_path=db_file,
                groq_api_key="test-key-fake",
                llm_model="llama-3.3-70b-versatile",
                rag_pipeline=None,
            )
            orch._mock_router = mock_router_instance

            mock_rag = MagicMock()
            mock_rag.process_query.return_value = {
                "success": True,
                "response": "Respuesta RAG.",
            }
            orch.set_rag_pipeline(mock_rag)

            yield orch

    def test_menu_returns_list_message(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "menú")
        assert isinstance(resp, ListMessage)
        assert len(resp.sections) > 0

    def test_menu_registered_has_sections(self, orchestrator):
        resp = orchestrator.process_message("5493794285297", "menú")
        assert isinstance(resp, ListMessage)
        # Registered client: 3 sections (Servicios, Soporte, Cuenta)
        assert len(resp.sections) == 3
        all_row_ids = [r.id for s in resp.sections for r in s.rows]
        assert "crear_ticket" in all_row_ids
        assert "mi_cuenta" in all_row_ids
        assert "ver_planes" in all_row_ids

    def test_menu_unregistered_has_single_section(self, orchestrator):
        resp = orchestrator.process_message("5491199990000", "menú")
        assert isinstance(resp, ListMessage)
        assert len(resp.sections) == 1
        all_row_ids = [r.id for s in resp.sections for r in s.rows]
        assert "registrarme" in all_row_ids
        assert "crear_ticket" not in all_row_ids

    def test_ticket_priority_returns_list_message(self, orchestrator):
        """Al pedir prioridad de ticket, retorna ListMessage."""
        phone = "5493794285297"
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CREAR_TICKET,
            "confidence": 0.9,
        }
        orchestrator.process_message(phone, "Quiero crear un ticket")
        orchestrator.process_message(phone, "VPN no funciona")
        resp = orchestrator.process_message(
            phone, "La VPN no conecta, error de timeout continuo"
        )
        assert isinstance(resp, ListMessage)
        row_ids = [r.id for s in resp.sections for r in s.rows]
        assert "prioridad_baja" in row_ids
        assert "prioridad_critica" in row_ids

    def test_contract_start_returns_list_message(self, orchestrator):
        """Al iniciar contratación, retorna ListMessage con planes."""
        phone = "5493794285297"
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CONTRATAR_PLAN,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message(phone, "Quiero contratar un plan")
        assert isinstance(resp, ListMessage)
        row_ids = [r.id for s in resp.sections for r in s.rows]
        assert "plan_1" in row_ids
        assert "plan_2" in row_ids
        assert "plan_3" in row_ids

    def test_contract_confirm_returns_button_message(self, orchestrator):
        """Al confirmar plan, retorna ButtonMessage con Sí/No."""
        phone = "5493794285297"
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CONTRATAR_PLAN,
            "confidence": 0.9,
        }
        orchestrator.process_message(phone, "Quiero contratar un plan")
        # Seleccionar plan 1
        resp = orchestrator.process_message(phone, "1")
        assert isinstance(resp, ButtonMessage)
        btn_ids = [b.id for b in resp.buttons]
        assert "confirmar_si" in btn_ids
        assert "confirmar_no" in btn_ids

    def test_contract_payment_returns_button_message(self, orchestrator):
        """Al elegir método de pago, retorna ButtonMessage."""
        phone = "5493794285297"
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CONTRATAR_PLAN,
            "confidence": 0.9,
        }
        orchestrator.process_message(phone, "Quiero contratar un plan")
        orchestrator.process_message(phone, "1")  # Plan Básico
        resp = orchestrator.process_message(phone, "sí")  # Confirmar
        assert isinstance(resp, ButtonMessage)
        btn_ids = [b.id for b in resp.buttons]
        assert "pago_transferencia" in btn_ids
        assert "pago_tarjeta" in btn_ids
        assert "pago_mercadopago" in btn_ids

    def test_interactive_id_triggers_intent(self, orchestrator):
        """Un ID de interactive list (ej: 'ver_planes') se mapea correctamente."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.VER_PLANES,
            "confidence": 0.9,
        }
        # Simular que el usuario tocó "ver_planes" en la lista interactiva
        resp = orchestrator.process_message("5493794285297", "ver_planes")
        text = to_text(resp)
        assert "Básico" in text or "planes" in text.lower()

    def test_rag_returns_plain_string(self, orchestrator):
        """Consulta RAG sigue retornando str (no interactivo)."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.CONSULTA_RAG,
            "confidence": 0.8,
        }
        resp = orchestrator.process_message(
            "5493794285297", "¿Cuál es el horario de soporte?"
        )
        assert isinstance(resp, str)

    def test_fuera_de_tema_returns_string(self, orchestrator):
        """Fuera de tema retorna str."""
        orchestrator._mock_router.classify.return_value = {
            "intent": AgentIntent.FUERA_DE_TEMA,
            "confidence": 0.9,
        }
        resp = orchestrator.process_message("5493794285297", "¿Quién ganó el mundial?")
        assert isinstance(resp, str)


# Interactive button IDs in priority parsing


class TestInteractivePriorityIds:
    """Verificar que los IDs de botones interactivos se parseen como prioridad."""

    def test_prioridad_baja_id(self):
        from agent.handlers import _parse_priority
        assert _parse_priority("prioridad_baja") == "Baja"

    def test_prioridad_media_id(self):
        from agent.handlers import _parse_priority
        assert _parse_priority("prioridad_media") == "Media"

    def test_prioridad_alta_id(self):
        from agent.handlers import _parse_priority
        assert _parse_priority("prioridad_alta") == "Alta"

    def test_prioridad_critica_id(self):
        from agent.handlers import _parse_priority
        assert _parse_priority("prioridad_critica") == "Crítica"


# Plan selection with interactive IDs


class TestInteractivePlanIds:
    """Verificar que los IDs de lista interactiva se parseen como planes."""

    @pytest.fixture
    def db(self, tmp_path):
        from agent.db_service import DBService
        _SCHEMA_PATH = project_root / "database" / "schema" / "schema.sql"
        _SEED_PATH = project_root / "database" / "seeds" / "seed.sql"

        db_file = tmp_path / "test.db"
        import sqlite3
        conn = sqlite3.connect(db_file)
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        with open(_SEED_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()
        return DBService(db_file)

    def test_plan_1_id(self, db):
        from agent.handlers import _parse_plan_selection
        plan = _parse_plan_selection("plan_1", db)
        assert plan is not None
        assert plan["name"] == "Básico"

    def test_plan_2_id(self, db):
        from agent.handlers import _parse_plan_selection
        plan = _parse_plan_selection("plan_2", db)
        assert plan is not None
        assert plan["name"] == "Profesional"

    def test_plan_3_id(self, db):
        from agent.handlers import _parse_plan_selection
        plan = _parse_plan_selection("plan_3", db)
        assert plan is not None
        assert plan["name"] == "Empresarial"
