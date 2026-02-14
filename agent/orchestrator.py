"""
Orchestrator — Punto de entrada principal del agente conversacional.

Flujo:
1. Normalizar teléfono
2. Buscar cliente por phone
3. Cargar estado de conversación
4. Si hay flujo activo → continuar handler
5. Si no → clasificar intent con LLM router → despachar
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional

from agent.conversation import ConversationManager, IDLE
from agent.db_service import DBService
from agent.handlers import (
    format_account_response,
    format_plans_response,
    format_tickets_response,
    handle_contract_plan,
    handle_create_ticket,
    handle_registration,
    start_contract_plan,
    start_create_ticket,
    start_registration,
)
from agent.router import AgentIntent, IntentRouter

logger = logging.getLogger(__name__)


# Phone normalization

_PHONE_CLEAN_RE = re.compile(r"[^\d]")


def normalize_phone(raw: str) -> str:
    """
    Normaliza un teléfono a formato E.164 numérico (sin '+').

    Ejemplos:
        '+54 9 3794 28-5297' → '5493794285297'
        '5493794285297'      → '5493794285297'
    """
    return _PHONE_CLEAN_RE.sub("", raw)


class AgentOrchestrator:
    """Orquestador principal del agente conversacional."""

    def __init__(
        self,
        db_path: Path,
        groq_api_key: str,
        llm_model: str = "llama-3.3-70b-versatile",
        rag_pipeline=None,
    ):
        self._db = DBService(db_path)
        self._conv = ConversationManager(self._db)
        self._router = IntentRouter(api_key=groq_api_key, model=llm_model)
        self._rag = rag_pipeline  # se inyecta desde main.py

        logger.info("AgentOrchestrator inicializado")

    def set_rag_pipeline(self, pipeline) -> None:
        """Inyecta el RAG pipeline (se llama después de init para evitar circular)."""
        self._rag = pipeline

    # Entry point

    def process_message(self, raw_phone: str, message: str) -> str:
        """
        Procesa un mensaje entrante y devuelve la respuesta como texto.

        Args:
            raw_phone: Número tal cual viene de WhatsApp (ej: '5493794285297')
            message: Texto del mensaje
        """
        phone = normalize_phone(raw_phone)
        message = message.strip()

        if not message:
            return "No recibí un mensaje. ¿En qué puedo ayudarle?"

        logger.info(f"[{phone}] Mensaje: {message[:60]}")

        # 1. Buscar cliente
        client = self._db.find_client_by_phone(phone)

        # 2. Cargar estado de conversación
        state, context = self._conv.get_full(phone)

        # 3. Si hay flujo activo, intentar continuar
        if state != IDLE:
            # Permitir cancelación global
            if message.lower() in ("cancelar", "salir", "cancel"):
                self._conv.reset(phone)
                return "Operación cancelada. ¿En qué puedo ayudarle?"

            return self._continue_flow(phone, message, client, state, context)

        # 4. Intercept "registrar" keyword before LLM routing
        lower_msg = message.lower().strip()
        if lower_msg in ("registrar", "registro", "registrarme", "darme de alta"):
            if client:
                return (
                    f"Ya se encuentra registrado como cliente, {client['contact_name']}. "
                    f"¿En qué puedo ayudarle?"
                )
            return start_registration(phone, self._conv)

        # 5. Clasificar intención con LLM
        result = self._router.classify(message)
        intent = result["intent"]

        # 6. Despachar según intención
        return self._dispatch(phone, message, client, intent)

    # Flow continuation

    def _continue_flow(
        self,
        phone: str,
        message: str,
        client: Optional[Dict],
        state: str,
        context: Dict,
    ) -> str:
        """Continúa un flujo multi-turn en curso."""

        # Flujo de registro (no requiere client)
        if state.startswith("REG_"):
            return handle_registration(
                phone, message, state, context, self._conv, self._db
            )

        # Los demás flujos requieren client
        if not client:
            self._conv.reset(phone)
            return (
                "Parece que su sesión expiró. "
                "No lo encontré como cliente registrado. "
                "Escriba *registrar* para darse de alta."
            )

        if state.startswith("TICKET_"):
            return handle_create_ticket(
                phone, message, state, context, self._conv, self._db
            )

        if state.startswith("CONTRACT_"):
            return handle_contract_plan(
                phone, message, state, context, self._conv, self._db
            )

        # Estado desconocido → resetear
        logger.warning(f"[{phone}] Estado desconocido: {state}. Reseteando.")
        self._conv.reset(phone)
        return "Ha ocurrido un error. ¿En qué puedo ayudarle?"

    # Intent dispatch

    def _dispatch(
        self,
        phone: str,
        message: str,
        client: Optional[Dict],
        intent: AgentIntent,
    ) -> str:
        """Despacha según la intención clasificada."""

        # Intenciones que NO requieren estar registrado

        if intent == AgentIntent.SALUDO:
            return self._handle_saludo(client)

        if intent == AgentIntent.DESPEDIDA:
            name = client["contact_name"] if client else ""
            farewell = f"¡Hasta luego{', ' + name if name else ''}!"
            return f"{farewell} Si necesita algo más, no dude en escribirnos."

        if intent == AgentIntent.FUERA_DE_TEMA:
            return (
                "Disculpe, solo puedo asistirle con temas relacionados a los "
                "servicios de soporte IT de KnowLigo. ¿Puedo ayudarle con algo "
                "sobre nuestros planes, tickets o servicios?"
            )

        if intent == AgentIntent.CONSULTA_RAG:
            return self._handle_rag_query(phone, message, client)

        if intent == AgentIntent.VER_PLANES:
            plans = self._db.get_plans()
            return format_plans_response(plans)

        # Intenciones que requieren estar registrado

        if not client:
            return self._prompt_registration(intent)

        if intent == AgentIntent.VER_TICKETS:
            tickets = self._db.get_open_tickets(client["id"])
            return format_tickets_response(tickets)

        if intent == AgentIntent.CREAR_TICKET:
            return start_create_ticket(phone, client, self._conv)

        if intent == AgentIntent.CONTRATAR_PLAN:
            plans = self._db.get_plans()
            return start_contract_plan(phone, client, plans, self._conv)

        if intent == AgentIntent.CONSULTA_CUENTA:
            contracts = self._db.get_active_contracts(client["id"])
            return format_account_response(client, contracts)

        if intent == AgentIntent.CANCELAR:
            return "No hay ninguna operación en curso para cancelar."

        # Fallback → RAG
        return self._handle_rag_query(phone, message, client)

    # Handlers internos

    def _handle_saludo(self, client: Optional[Dict]) -> str:
        if client:
            name = client["contact_name"]
            return (
                f"¡Hola, {name}! Bienvenido/a de vuelta a KnowLigo.\n\n"
                "¿En qué puedo ayudarle hoy?\n"
                "• Consultar *tickets* de soporte\n"
                "• Ver *planes* disponibles\n"
                "• *Contratar* un plan\n"
                "• Crear un *ticket* nuevo\n"
                "• Consultar su *cuenta*\n"
                "• Hacer una *pregunta* sobre nuestros servicios"
            )
        else:
            return (
                "¡Hola! Bienvenido/a a KnowLigo, su aliado en soporte IT.\n\n"
                "No lo tengo registrado aún. Puede:\n"
                "• Escribir *registrar* para darse de alta como cliente\n"
                "• Hacer una *pregunta* sobre nuestros servicios y planes\n"
                "• Ver los *planes* disponibles"
            )

    def _handle_rag_query(
        self, phone: str, message: str, client: Optional[Dict]
    ) -> str:
        """Delega la consulta informativa al pipeline RAG."""
        if self._rag is None:
            return (
                "El sistema de consultas no está disponible en este momento. "
                "Por favor, intente nuevamente más tarde."
            )

        try:
            result = self._rag.process_query(
                user_query=message,
                user_id=phone,
            )
            if result["success"]:
                return result["response"]
            else:
                # Podría ser rate limit o query inválida
                return result.get(
                    "response",
                    "No pude procesar su consulta. Intente reformularla.",
                )
        except Exception as e:
            logger.error(f"[{phone}] Error en RAG: {e}", exc_info=True)
            return (
                "Disculpe, ocurrió un error procesando su consulta. Intente nuevamente."
            )

    def _prompt_registration(self, intent: AgentIntent) -> str:
        """Mensaje cuando el usuario no está registrado e intenta una acción que lo requiere."""
        action_map = {
            AgentIntent.VER_TICKETS: "ver sus tickets",
            AgentIntent.CREAR_TICKET: "crear un ticket",
            AgentIntent.CONTRATAR_PLAN: "contratar un plan",
            AgentIntent.CONSULTA_CUENTA: "ver su cuenta",
        }
        action = action_map.get(intent, "realizar esa acción")
        return (
            f"Para {action} necesita estar registrado como cliente.\n\n"
            "Escriba *registrar* para darse de alta. Es rápido, solo necesito "
            "su nombre, empresa y email."
        )
