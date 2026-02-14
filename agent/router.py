"""
Router — Clasificación de intención con LLM (Groq).

Usa el mismo modelo Llama 3.3 para determinar la intención del mensaje,
complementando el clasificador basado en keywords del RAG.
"""

import json
import logging
from enum import Enum
from typing import Dict

try:
    from groq import Groq
except ImportError:
    raise ImportError("Dependencia faltante: pip install groq")

logger = logging.getLogger(__name__)


class AgentIntent(str, Enum):
    """Intenciones que el agente puede manejar."""

    SALUDO = "SALUDO"
    CONSULTA_RAG = "CONSULTA_RAG"
    VER_TICKETS = "VER_TICKETS"
    CREAR_TICKET = "CREAR_TICKET"
    VER_PLANES = "VER_PLANES"
    CONTRATAR_PLAN = "CONTRATAR_PLAN"
    CONSULTA_CUENTA = "CONSULTA_CUENTA"
    DESPEDIDA = "DESPEDIDA"
    FUERA_DE_TEMA = "FUERA_DE_TEMA"
    CANCELAR = "CANCELAR"


# Prompt del sistema para clasificación
_ROUTER_SYSTEM_PROMPT = """\
Eres un clasificador de intenciones para KnowLigo, empresa de soporte IT.
Dado el mensaje del usuario, responde ÚNICAMENTE con un JSON:
{"intent": "<INTENT>", "confidence": <0.0-1.0>}

Intenciones válidas:
- SALUDO: saludos, hola, buen día, etc.
- CONSULTA_RAG: preguntas sobre servicios, SLA, horarios, info general de la empresa.
- VER_TICKETS: quiere ver sus tickets, consultar estado de incidencias.
- CREAR_TICKET: quiere reportar un problema, abrir un ticket, tiene una incidencia.
- VER_PLANES: pregunta por precios, planes disponibles, comparar planes.
- CONTRATAR_PLAN: quiere contratar, suscribirse, comprar un plan.
- CONSULTA_CUENTA: pregunta por su cuenta, datos, contrato actual.
- DESPEDIDA: chau, gracias, adiós, hasta luego.
- FUERA_DE_TEMA: temas ajenos a KnowLigo (política, deportes, etc.).
- CANCELAR: quiere cancelar la operación en curso.

Reglas:
1. Si el usuario pide "cancelar" en contexto de un flujo activo, es CANCELAR.
2. Si pregunta "qué planes tienen" es VER_PLANES; si dice "quiero contratar" es CONTRATAR_PLAN.
3. Responde SOLO el JSON, sin explicaciones.
"""


class IntentRouter:
    """Clasifica intenciones usando Groq LLM."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self._client = Groq(api_key=api_key)
        self._model = model

    def classify(self, message: str) -> Dict:
        """
        Clasifica un mensaje en una AgentIntent.

        Returns:
            {"intent": AgentIntent, "confidence": float}
        """
        try:
            completion = self._client.chat.completions.create(
                messages=[
                    {"role": "system", "content": _ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                model=self._model,
                temperature=0.0,
                max_tokens=60,
            )

            raw = completion.choices[0].message.content.strip()
            parsed = self._parse_response(raw)
            logger.info(
                f"Router: '{message[:40]}…' → {parsed['intent'].value} "
                f"({parsed['confidence']:.2f})"
            )
            return parsed

        except Exception as e:
            logger.error(f"Error en router LLM: {e}")
            # Fallback seguro: derivar al RAG
            return {"intent": AgentIntent.CONSULTA_RAG, "confidence": 0.3}

    def _parse_response(self, raw: str) -> Dict:
        """Parsea la respuesta JSON del LLM."""
        try:
            # Limpiar posible markdown
            clean = raw.strip().strip("`").strip()
            if clean.startswith("json"):
                clean = clean[4:].strip()

            data = json.loads(clean)
            intent_str = data.get("intent", "CONSULTA_RAG").upper()
            confidence = float(data.get("confidence", 0.5))

            try:
                intent = AgentIntent(intent_str)
            except ValueError:
                logger.warning(f"Intent desconocido del LLM: {intent_str}")
                intent = AgentIntent.CONSULTA_RAG
                confidence = 0.3

            return {"intent": intent, "confidence": confidence}

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"No se pudo parsear respuesta del router: {raw} ({e})")
            return {"intent": AgentIntent.CONSULTA_RAG, "confidence": 0.3}
