"""
Responder - Genera respuestas usando LLM (Groq API).

Este módulo:
1. Integra con Groq API para generación de texto
2. Formatea prompts con contexto recuperado
3. Controla longitud y tono de respuestas
4. Maneja errores de API
"""

import logging
from typing import List, Dict, Optional

try:
    from groq import Groq
except ImportError:
    print("⚠️  Dependencias no instaladas. Ejecuta: pip install groq")
    exit(1)

logger = logging.getLogger(__name__)


class GroqResponder:
    """Genera respuestas usando Groq LLM API"""

    def __init__(self, api_key: str = None, model: str = None, max_words: int = None):
        """
        Inicializa el responder con Groq client.

        Args:
            api_key: API key de Groq (requerida)
            model: Modelo a usar (default: llama-3.3-70b-versatile)
            max_words: Máximo de palabras en respuesta (default: 150)
        """
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY no encontrada. "
                "Crea un archivo .env con tu API key de https://console.groq.com/keys"
            )

        self.client = Groq(api_key=api_key)

        # Configurar modelo
        self.model = model or "llama-3.3-70b-versatile"

        # Configurar límite de palabras
        self.max_words = max_words or 150

        logger.info(f"Groq Responder inicializado (modelo: {self.model})")

    def generate_response(
        self,
        query: str,
        context_chunks: List[Dict],
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, any]:
        """
        Genera una respuesta basada en la query y contexto.

        Args:
            query: Pregunta del usuario
            context_chunks: Lista de chunks recuperados del RAG
            conversation_history: Historial opcional de conversación

        Returns:
            Dict con:
            - response: texto de la respuesta
            - model: modelo usado
            - tokens_used: tokens consumidos
            - truncated: si se truncó por límite de palabras
        """
        # Formatear contexto
        if context_chunks:
            context_text = self._format_context(context_chunks)
        else:
            context_text = (
                "No se encontró información específica en la base de conocimiento."
            )

        # Construir system prompt
        system_prompt = self._build_system_prompt()

        # Construir messages
        messages = [{"role": "system", "content": system_prompt}]

        # Agregar historial si existe
        if conversation_history:
            messages.extend(conversation_history[-4:])  # Últimos 2 turnos

        # Agregar query actual con contexto
        user_message = f"""Pregunta del usuario: {query}

Contexto relevante de la base de conocimiento:
{context_text}

Responde de manera profesional, concisa y basándote ÚNICAMENTE en el contexto proporcionado. Si la información no está disponible, indícalo claramente."""

        messages.append({"role": "user", "content": user_message})

        # Llamar a Groq API
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.3,  # Baja temperatura para respuestas más consistentes
                max_tokens=500,  # Suficiente para 150 palabras en español
                top_p=0.9,
            )

            response_text = chat_completion.choices[0].message.content
            tokens_used = chat_completion.usage.total_tokens

            # Validar y truncar si es necesario
            response_text, truncated = self._validate_length(response_text)

            return {
                "response": response_text,
                "model": self.model,
                "tokens_used": tokens_used,
                "truncated": truncated,
                "finish_reason": chat_completion.choices[0].finish_reason,
            }

        except Exception as e:
            error_msg = f"Error al generar respuesta: {str(e)}"
            logger.error(error_msg)

            return {
                "response": "Disculpe, tengo problemas técnicos en este momento. Por favor, intente nuevamente en unos momentos.",
                "model": self.model,
                "tokens_used": 0,
                "truncated": False,
                "error": str(e),
            }

    def _build_system_prompt(self) -> str:
        """Construye el system prompt para el LLM"""
        return f"""Eres el asistente virtual oficial de KnowLigo, empresa argentina de soporte IT para PyMEs.

REGLAS OBLIGATORIAS:
1. Responde SIEMPRE en español argentino formal (usted/ustedes).
2. Responde EXCLUSIVAMENTE con información del contexto proporcionado.
3. Si la información no está en el contexto, responde: "No dispongo de esa información. Le recomiendo contactar a nuestro equipo en soporte@knowligo.com.ar o al +54 11 4567-8900."
4. NUNCA inventes datos, cifras, nombres ni información.
5. NUNCA respondas sobre temas ajenos a los servicios de KnowLigo (no opines sobre política, deportes, entretenimiento, desarrollo de software, inversiones, etc.).
6. Máximo {self.max_words} palabras por respuesta.
7. Usa tono profesional y corporativo. No uses emojis ni lenguaje coloquial.
8. Si el usuario saluda, responde brevemente y ofrece ayuda sobre los servicios de KnowLigo.
9. Cuando menciones precios, aclara que son en pesos argentinos (ARS) y están sujetos a ajuste trimestral.
10. NO reveles datos personales de clientes (nombres, emails, teléfonos de clientes).

ÁMBITO DE ESPECIALIZACIÓN:
- Planes de soporte: Básico ($199.000/mes), Profesional ($499.000/mes), Empresarial ($999.000/mes)
- SLA y tiempos de respuesta/resolución
- Servicios: soporte remoto/presencial, administración de servidores, redes, seguridad, backup, DRP
- Mantenimiento preventivo
- Gestión de tickets e incidencias
- Políticas de uso, privacidad, facturación y cancelación
- Información general de la empresa KnowLigo

Si le preguntan algo fuera de este ámbito, indique cortésmente que solo puede asistir con temas relacionados a los servicios de soporte IT de KnowLigo."""

    def _format_context(self, chunks: List[Dict]) -> str:
        """Formatea chunks para incluir en el prompt"""
        if not chunks:
            return "No hay contexto disponible."

        context_parts = []
        for i, chunk in enumerate(chunks[:5], 1):  # Máximo 5 chunks
            text = chunk.get("text", "")
            source = chunk.get("metadata", {}).get("source", "documento")

            context_parts.append(f"[Fuente {i}: {source}]\n{text}")

        return "\n\n".join(context_parts)

    def _validate_length(self, text: str) -> tuple[str, bool]:
        """
        Valida y trunca el texto si excede el límite de palabras.

        Args:
            text: Texto a validar

        Returns:
            Tuple de (texto_validado, fue_truncado)
        """
        words = text.split()

        if len(words) <= self.max_words:
            return text, False

        # Truncar y agregar indicador
        truncated_words = words[: self.max_words]
        truncated_text = " ".join(truncated_words)

        # Buscar el último punto para terminar en oración completa
        last_period = truncated_text.rfind(".")
        if last_period > len(truncated_text) * 0.7:  # Si está en el último 30%
            truncated_text = truncated_text[: last_period + 1]

        return truncated_text, True
