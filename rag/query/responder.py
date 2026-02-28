"""
Responder - Genera respuestas usando LLM (Groq API).

Este módulo:
1. Integra con Groq API para generación de texto
2. Formatea prompts con contexto recuperado
3. Controla longitud y tono de respuestas
4. Maneja errores de API
"""

import logging
from datetime import datetime
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
{context_text}"""

        messages.append({"role": "user", "content": user_message})

        # Llamar a Groq API
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.5,  # Balance entre creatividad y consistencia
                max_tokens=1024,  # Margen amplio para respuestas completas
                top_p=0.9,
            )

            response_text = chat_completion.choices[0].message.content
            tokens_used = chat_completion.usage.total_tokens

            # Limpiar comillas envolventes que el LLM a veces agrega
            response_text = response_text.strip().strip('"\u201c\u201d\u00ab\u00bb')

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
        now = datetime.now()
        date_str = now.strftime("%A %d de %B de %Y, %H:%M hs")
        return f"""Sos el asistente virtual de KnowLigo, empresa argentina de soporte IT para PyMEs.

FECHA Y HORA ACTUAL: {date_str}

PERSONALIDAD:
- Hablás en español argentino neutro (vos/ustedes). Tono profesional pero amigable.
- Podés usar algún emoji ocasional (✅, 📋, 💡) para dar claridad.
- Variá tus respuestas — no repitas siempre la misma frase de bienvenida o cierre.
- Si el usuario saluda, respondé de forma breve y natural, y preguntá en qué área necesita ayuda.

REGLAS:
1. Basate principalmente en el contexto proporcionado. Si algo no está en el contexto, decilo con honestidad y sugerí contactar a soporte@knowligo.com.ar o al +54 11 4567-8900.
2. NUNCA inventes datos, cifras, nombres ni información.
3. Cuando menciones precios, aclará que son en pesos argentinos (ARS) y sujetos a ajuste trimestral.
4. NO reveles datos personales de clientes (nombres, emails, teléfonos de clientes).
5. Sé conciso pero completo. Apuntá a entre 80 y {self.max_words} palabras según la complejidad de la pregunta.
6. Si la pregunta es ambigua, pedí aclaración en lugar de rechazar.
7. Si te preguntan algo completamente ajeno a IT (política, recetas, etc.), indicá cortésmente que solo podés ayudar con servicios de soporte IT de KnowLigo.8. NO saludes ("Hola", "Buen día", "¡Hola!", etc.) al inicio de la respuesta. El usuario ya está en conversación — respondé directo al contenido de la pregunta.
9. NO envuelvas tu respuesta entre comillas.
ÁMBITO:
- Planes de soporte, precios y comparativas
- SLA y tiempos de respuesta/resolución
- Servicios: soporte remoto/presencial, servidores, redes, seguridad, backup, DRP
- Mantenimiento preventivo
- Tickets e incidencias
- Políticas, privacidad, facturación y cancelación
- Información general de la empresa"""

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
