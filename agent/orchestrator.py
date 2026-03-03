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
import time
from datetime import datetime
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
from agent.messages import (
    AgentResponse,
    ButtonMessage,
    ListMessage,
    ListRow,
    ListSection,
    ReplyButton,
    to_text,
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
        self._groq_api_key = groq_api_key
        self._llm_model = llm_model

        logger.info("AgentOrchestrator inicializado")

    def set_rag_pipeline(self, pipeline) -> None:
        """Inyecta el RAG pipeline (se llama después de init para evitar circular)."""
        self._rag = pipeline

    # Entry point

    def process_message(self, raw_phone: str, message: str) -> AgentResponse:
        """
        Procesa un mensaje entrante y devuelve la respuesta.

        Retorna str para la mayoría de respuestas, o un objeto
        ListMessage/ButtonMessage para respuestas interactivas de WhatsApp.

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
            # Permitir cancelación global — búsqueda por substring
            # (longest-first para evitar falsos positivos)
            _cancel_phrases = [
                "no quiero crear",
                "cancela el ticket",
                "no, gracias",
                "no lo haga",
                "no gracias",
                "no quiero",
                "mejor no",
                "cancelar",
                "olvidate",
                "olvídate",
                "dejálo",
                "dejalo",
                "cancela",
                "anular",
                "anulá",
                "dejá",
                "salir",
                "cancel",
                "atrás",
                "atras",
            ]
            lower_msg = message.lower().strip()
            if any(phrase in lower_msg for phrase in _cancel_phrases):
                self._conv.reset(phone)
                return "Operación cancelada. ¿En qué puedo ayudarte?"

            return self._continue_flow(phone, message, client, state, context)

        # 4. Intercept casual expressions (emoticons, jaja, etc.)
        lower_msg = message.lower().strip()
        if self._is_casual_expression(lower_msg):
            resp = "😊 ¿Necesitás algo más?"
            self._log_interaction(phone, message, "CASUAL", resp)
            return resp

        # 4a. Map interactive button/list IDs to keywords
        #     (when user taps an option in WhatsApp, the webhook sends the row id)
        _INTERACTIVE_ID_MAP = {
            "ver_planes": "ver planes",
            "crear_ticket": "crear ticket",
            "ver_tickets": "ver mis tickets",
            "contratar_plan": "contratar plan",
            "mi_cuenta": "mi cuenta",
            "consultar": "consultar",
            "registrarme": "registrarme",
        }
        if lower_msg in _INTERACTIVE_ID_MAP:
            message = _INTERACTIVE_ID_MAP[lower_msg]
            lower_msg = message.lower()

        # 4b. Intercept menu keyword
        if lower_msg in ("menú", "menu", "opciones", "ayuda", "help"):
            resp = self._build_menu(client)
            self._log_interaction(phone, message, "MENU", to_text(resp))
            return resp

        # 5. Intercept "registrar" keyword before LLM routing
        if lower_msg in ("registrar", "registro", "registrarme", "darme de alta"):
            if client:
                resp = (
                    f"Ya se encuentra registrado como cliente, {client['contact_name']}. "
                    f"¿En qué puedo ayudarle?"
                )
                self._log_interaction(phone, message, "REGISTRAR", resp)
                return resp
            resp = start_registration(phone, self._conv)
            self._log_interaction(phone, message, "REGISTRAR", resp)
            return resp

        # 5b. Intercept gibberish / noise inputs (after known keywords)
        if self._is_gibberish(lower_msg):
            resp = (
                "No entendí tu mensaje. ¿Podrías reformularlo?\n\n"
                "Escribí *menú* para ver las opciones disponibles."
            )
            self._log_interaction(phone, message, "GIBBERISH", resp)
            return resp

        # 6. Clasificar intención con LLM (con contexto conversacional)
        recent = self._db.get_recent_messages(phone, limit=8)
        result = self._router.classify(message, conversation_history=recent)
        intent = result["intent"]

        # 7. Despachar según intención
        resp = self._dispatch(phone, message, client, intent, recent)
        # Log the interaction (RAG queries are also logged by the pipeline,
        # but we log here for ALL intents uniformly)
        self._log_interaction(
            phone,
            message,
            intent.value if hasattr(intent, "value") else str(intent),
            to_text(resp),
        )
        return resp

    # Flow continuation

    def _continue_flow(
        self,
        phone: str,
        message: str,
        client: Optional[Dict],
        state: str,
        context: Dict,
    ) -> AgentResponse:
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
        conversation_history: list[dict] | None = None,
    ) -> AgentResponse:
        """Despacha según la intención clasificada."""

        # Intenciones que NO requieren estar registrado

        if intent == AgentIntent.SALUDO:
            return self._handle_saludo(client, phone)

        if intent == AgentIntent.DESPEDIDA:
            name = client["contact_name"] if client else None
            return self._llm_short_response(
                f"Generá UNA SOLA despedida breve y cálida (1-2 oraciones, español argentino, vos) "
                f"para un usuario de un chatbot de soporte IT (KnowLigo)."
                f"{' El cliente se llama ' + name + '.' if name else ''} "
                f"Invitá a volver cuando necesite algo. Variá el estilo. "
                f"IMPORTANTE: Respondé con UNA ÚNICA despedida. NO generes opciones, alternativas ni variantes separadas por 'O', 'O también:', 'También:', etc.",
            )

        if intent == AgentIntent.FUERA_DE_TEMA:
            return (
                "Disculpe, solo puedo asistirle con temas relacionados a los "
                "servicios de soporte IT de KnowLigo. ¿Puedo ayudarle con algo "
                "sobre nuestros planes, tickets o servicios?"
            )

        if intent == AgentIntent.CONSULTA_RAG:
            return self._handle_rag_query(phone, message, client, conversation_history)

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
            # Verificar plan activo — solo se permite uno por cliente
            active = self._db.get_active_contracts(client["id"])
            if active:
                plan_name = active[0]["plan_name"]
                return (
                    f"Ya tenés un plan activo: *Plan {plan_name}*. "
                    f"Solo se permite un plan por cliente. "
                    f"Si querés modificar o cancelar tu plan, podés hacerlo desde la interfaz web.\n\n"
                    f"¿Puedo ayudarte con algo más?"
                )
            plans = self._db.get_plans()
            return start_contract_plan(phone, client, plans, self._conv)

        if intent == AgentIntent.CONSULTA_CUENTA:
            contracts = self._db.get_active_contracts(client["id"])
            return format_account_response(client, contracts)

        if intent == AgentIntent.CANCELAR:
            return "No hay ninguna operación en curso para cancelar."

        # Fallback → RAG
        return self._handle_rag_query(phone, message, client, conversation_history)

    # Handlers internos

    _CASUAL_EXPRESSIONS = {
        ":)",
        ":(",
        ":D",
        ":d",
        ":P",
        ":p",
        "xD",
        "xd",
        "jaja",
        "jajaja",
        "jajaj",
        "jajajaja",
        "jeje",
        "jejeje",
        "haha",
        "hahaha",
        "lol",
        "lmao",
        "😂",
        "😄",
        "👍",
        "👏",
        "🤣",
        "😊",
        "🙌",
        "💪",
        "🤗",
        "ok",
        "okey",
        "dale",
        "genial",
        "perfecto",
    }

    def _is_casual_expression(self, text: str) -> bool:
        """Detecta expresiones casuales cortas (emoticones, risas, emojis)."""
        if text in self._CASUAL_EXPRESSIONS:
            return True
        # Pure emoji-only messages (1-3 emojis sin texto)
        import re

        if re.fullmatch(
            r"[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0000FE00-\U0000FEFF\s]{1,10}",
            text,
        ):
            return True
        return False

    def _handle_saludo(self, client: Optional[Dict], phone: str) -> AgentResponse:
        """Genera un saludo variado usando el LLM + menú adaptativo.

        Si el usuario interactuó hace menos de 30 minutos, omite el saludo
        largo y devuelve un mensaje breve con menú.

        Retorna un ListMessage con el menú interactivo de WhatsApp.
        """
        # Smart greeting recency
        last_time = self._db.get_last_interaction_time(phone)
        if last_time:
            minutes_ago = (datetime.now() - last_time).total_seconds() / 60
            if minutes_ago < 30:
                menu = self._build_menu(client)
                menu = ListMessage(
                    body="¡De vuelta! ¿En qué puedo ayudarte?",
                    button_text=menu.button_text,
                    sections=menu.sections,
                    header=menu.header,
                    footer=menu.footer,
                )
                return menu

        if client:
            name = client["contact_name"]
            greeting = self._llm_short_response(
                f"Generá un saludo breve (1 oración, español argentino, vos) "
                f"para un usuario de un chatbot de soporte IT llamado KnowLigo. "
                f"El cliente YA está registrado y se llama {name}. "
                f"NO sugieras registro. Variá el estilo. "
                f"IMPORTANTE: NO enumeres opciones ni menú — solo saludá.",
            )
        else:
            greeting = self._llm_short_response(
                f"Generá un saludo breve (1 oración, español argentino, vos) "
                f"para un usuario de un chatbot de soporte IT llamado KnowLigo. "
                f"El usuario NO está registrado como cliente aún. "
                f"Variá el estilo. "
                f"IMPORTANTE: NO enumeres opciones ni menú — solo saludá.",
            )

        menu = self._build_menu(client)
        menu = ListMessage(
            body=greeting,
            button_text=menu.button_text,
            sections=menu.sections,
            header=menu.header,
            footer=menu.footer,
        )
        return menu

    def _build_menu(self, client: Optional[Dict]) -> ListMessage:
        """Construye un menú interactivo adaptativo según si el usuario es cliente o no.

        Retorna un ListMessage que:
        - En WhatsApp → se envía como Interactive List nativa (tap to select)
        - En /query o tests → se serializa a texto plano con .to_text()
        """
        if client:
            name = client["contact_name"]
            return ListMessage(
                body="¿En qué puedo ayudarte?",
                button_text="Ver opciones",
                header=f"Menú de opciones — {name}",
                footer="Escribí la opción o tu consulta directamente.",
                sections=[
                    ListSection(
                        title="Servicios",
                        rows=[
                            ListRow(
                                "ver_planes", "Ver planes", "Conocé nuestros planes"
                            ),
                            ListRow(
                                "consultar", "Consultar", "Preguntame lo que necesites"
                            ),
                        ],
                    ),
                    ListSection(
                        title="Soporte",
                        rows=[
                            ListRow(
                                "crear_ticket", "Crear ticket", "Reportá un problema"
                            ),
                            ListRow(
                                "ver_tickets",
                                "Ver mis tickets",
                                "Consultá tus incidencias",
                            ),
                        ],
                    ),
                    ListSection(
                        title="Cuenta",
                        rows=[
                            ListRow(
                                "mi_cuenta", "Mi cuenta", "Consultá tu información"
                            ),
                            ListRow(
                                "contratar_plan",
                                "Contratar plan",
                                "Suscribite a un plan",
                            ),
                        ],
                    ),
                ],
            )
        else:
            return ListMessage(
                body="¿En qué puedo ayudarte?",
                button_text="Ver opciones",
                header="Menú de opciones",
                footer="Escribí la opción o tu consulta directamente.",
                sections=[
                    ListSection(
                        title="Opciones",
                        rows=[
                            ListRow(
                                "registrarme",
                                "Registrarme",
                                "Darme de alta como cliente",
                            ),
                            ListRow(
                                "ver_planes", "Ver planes", "Conocé nuestros planes"
                            ),
                            ListRow(
                                "consultar",
                                "Consultar",
                                "Preguntame sobre nuestros servicios",
                            ),
                        ],
                    ),
                ],
            )

    def _is_gibberish(self, text: str) -> bool:
        """Detecta entradas de ruido / gibberish.

        Heuristics:
        - Single punctuation or repeated punctuation only
        - Very short non-word (≤2 chars, not a known expression)
        - No vowels in a 4+ char word
        - High consonant ratio (>0.8) in 4+ char word
        - Mixed digits + chars looking random
        """
        import re as _re

        # Pure punctuation / symbols (???, ..., !!!)
        if _re.fullmatch(r"[^\w\s]+", text):
            return True

        # Single character that's not a meaningful word
        if len(text) == 1 and text not in ("y", "o", "a", "e", "u"):
            return True

        # Very short (2 chars) — only if not a known word/expression
        _short_valid = {
            "si",
            "sí",
            "no",
            "ok",
            "va",
            "ya",
            "eh",
            "ah",
            "ey",
            "uy",
            "ay",
            "oh",
            "je",
            "ja",
            "xd",
        }
        if len(text) <= 2 and text not in _short_valid:
            return True

        # For 4+ char tokens: check for no vowels at all
        clean = _re.sub(r"[^a-záéíóúüñ]", "", text)
        if len(clean) >= 4:
            vowels = set("aeiouáéíóúü")
            vowel_count = sum(1 for c in clean if c in vowels)
            if vowel_count == 0:
                return True
            # High consonant ratio (>0.85)
            consonant_ratio = 1 - (vowel_count / len(clean))
            if consonant_ratio > 0.85:
                return True
            # Single word with 3+ consecutive consonants AND high ratio
            # (e.g. "dafasdf" has "sdf"; real words like "construir" have lower ratio)
            if " " not in text and len(clean) >= 5 and consonant_ratio > 0.6:
                consonant_chars = set("bcdfghjklmnñpqrstvwxyz")
                run = 0
                for c in clean:
                    if c in consonant_chars:
                        run += 1
                        if run >= 3:
                            return True
                    else:
                        run = 0

        # Mixed digits + letters looking random (like "23129fdagf")
        if _re.fullmatch(r"(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{5,}", text):
            # But skip things that look like ticket IDs or phone numbers
            if not _re.fullmatch(r"[A-Z]{2,4}-?\d{3,}", text, _re.IGNORECASE):
                return True

        return False

    def _log_interaction(
        self,
        phone: str,
        query: str,
        intent: str,
        response: str,
    ) -> None:
        """Registra la interacción en query_logs para historial y analytics."""
        try:
            self._db.log_interaction(
                phone=phone,
                query=query,
                intent=intent,
                response=response,
                success=True,
            )
        except Exception as e:
            logger.warning(f"[{phone}] Error logging interaction: {e}")

    def _handle_rag_query(
        self,
        phone: str,
        message: str,
        client: Optional[Dict],
        conversation_history: list[dict] | None = None,
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
                conversation_history=conversation_history,
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
            "Escribá *registrar* para darse de alta. Es rápido, solo necesito "
            "tu nombre, empresa y email."
        )

    # LLM helper para respuestas cortas variadas (saludos, despedidas)

    def _llm_short_response(self, instruction: str) -> str:
        """Genera una respuesta corta con el LLM — para saludos/despedidas variados."""
        try:
            from groq import Groq

            client = Groq(api_key=self._groq_api_key)
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": "generá el mensaje"},
                ],
                model=self._llm_model,
                temperature=0.9,  # Alta variedad
                max_tokens=150,
            )
            text = completion.choices[0].message.content.strip()
            # Limpiar comillas envolventes que el LLM a veces agrega
            text = text.strip('"\u201c\u201d\u00ab\u00bb')
            # Truncar si el LLM generó múltiples alternativas
            for sep in ("\nO también", "\nO \n", "\n\nO ", "\nTambién:", "\n\nO:"):
                idx = text.find(sep)
                if idx > 0:
                    text = text[:idx].rstrip()
                    break
            return text
        except Exception as e:
            logger.warning(f"LLM short response falló: {e}")
            return "¡Hola! Soy el asistente de KnowLigo. ¿En qué puedo ayudarte?"
