"""
Conversation Manager — Máquina de estados por teléfono.

Abstrae el acceso a la tabla `conversations` y expone
helpers de alto nivel para el orquestador.
"""

import logging
from typing import Any, Dict, Optional

from agent.db_service import DBService

logger = logging.getLogger(__name__)


# Estados válidos
IDLE = "IDLE"

# Registro
REG_AWAIT_NAME = "REG_AWAIT_NAME"
REG_AWAIT_COMPANY = "REG_AWAIT_COMPANY"
REG_AWAIT_EMAIL = "REG_AWAIT_EMAIL"

# Crear ticket
TICKET_AWAIT_SUBJECT = "TICKET_AWAIT_SUBJECT"
TICKET_AWAIT_DESCRIPTION = "TICKET_AWAIT_DESCRIPTION"
TICKET_AWAIT_PRIORITY = "TICKET_AWAIT_PRIORITY"

# Contratar plan
CONTRACT_AWAIT_PLAN = "CONTRACT_AWAIT_PLAN"
CONTRACT_AWAIT_CONFIRM = "CONTRACT_AWAIT_CONFIRM"
CONTRACT_AWAIT_PAYMENT = "CONTRACT_AWAIT_PAYMENT"


ALL_STATES = {
    IDLE,
    REG_AWAIT_NAME,
    REG_AWAIT_COMPANY,
    REG_AWAIT_EMAIL,
    TICKET_AWAIT_SUBJECT,
    TICKET_AWAIT_DESCRIPTION,
    TICKET_AWAIT_PRIORITY,
    CONTRACT_AWAIT_PLAN,
    CONTRACT_AWAIT_CONFIRM,
    CONTRACT_AWAIT_PAYMENT,
}


class ConversationManager:
    """Gestiona el estado de conversación por teléfono."""

    def __init__(self, db: DBService):
        self._db = db

    def get_state(self, phone: str) -> str:
        """Devuelve el estado actual (IDLE si no existe)."""
        conv = self._db.get_conversation(phone)
        if conv is None:
            return IDLE
        return conv["state"]

    def get_context(self, phone: str) -> Dict[str, Any]:
        """Devuelve el contexto JSON de la conversación (dict vacío si no existe)."""
        conv = self._db.get_conversation(phone)
        if conv is None:
            return {}
        return conv["context"]

    def get_full(self, phone: str) -> tuple[str, Dict[str, Any]]:
        """Devuelve (state, context) en una sola lectura."""
        conv = self._db.get_conversation(phone)
        if conv is None:
            return IDLE, {}
        return conv["state"], conv["context"]

    def set_state(
        self, phone: str, state: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Actualiza estado y opcionalmente contexto."""
        if state not in ALL_STATES:
            raise ValueError(f"Estado inválido: {state}")
        if context is None:
            # Mantener contexto previo
            context = self.get_context(phone)
        self._db.upsert_conversation(phone, state, context)
        logger.debug(f"[{phone}] state → {state}")

    def update_context(self, phone: str, **kwargs: Any) -> None:
        """Merge de campos al contexto actual sin cambiar estado."""
        state, ctx = self.get_full(phone)
        ctx.update(kwargs)
        self._db.upsert_conversation(phone, state, ctx)

    def reset(self, phone: str) -> None:
        """Vuelve a IDLE y limpia contexto."""
        self._db.clear_conversation(phone)
        logger.debug(f"[{phone}] conversación reseteada a IDLE")

    def is_active_flow(self, phone: str) -> bool:
        """True si hay un flujo multi-turn en curso (no IDLE)."""
        return self.get_state(phone) != IDLE
