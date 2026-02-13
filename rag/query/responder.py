"""
Responder - Genera respuestas usando LLM (Groq API).

Este módulo:
1. Integra con Groq API para generación de texto
2. Formatea prompts con contexto recuperado
3. Controla longitud y tono de respuestas
4. Maneja errores de API
"""

import os
from typing import List, Dict, Optional
from pathlib import Path

try:
    from groq import Groq
    from dotenv import load_dotenv
except ImportError:
    print("⚠️  Dependencias no instaladas. Ejecuta: pip install groq python-dotenv")
    exit(1)


class GroqResponder:
    """Genera respuestas usando Groq LLM API"""

    def __init__(self, api_key: str = None, model: str = None, max_words: int = None):
        """
        Inicializa el responder con Groq client.

        Args:
            api_key: API key de Groq (si None, lee de .env)
            model: Modelo a usar (default: mixtral-8x7b-32768)
            max_words: Máximo de palabras en respuesta (default: 120)
        """
        # Cargar variables de entorno
        project_root = Path(__file__).resolve().parent.parent.parent
        env_path = project_root / ".env"

        if env_path.exists():
            load_dotenv(env_path)

        # Configurar API key
        if api_key is None:
            api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY no encontrada. "
                "Crea un archivo .env con tu API key de https://console.groq.com/keys"
            )

        self.client = Groq(api_key=api_key)

        # Configurar modelo
        self.model = model or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

        # Configurar límite de palabras
        self.max_words = max_words or int(os.getenv("MAX_MESSAGE_LENGTH", "120"))

        print(f"✅ Groq Responder inicializado (modelo: {self.model})")

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
                max_tokens=300,  # Suficiente para 120 palabras (~200 tokens)
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
            print(f"❌ {error_msg}")

            return {
                "response": "Disculpe, tengo problemas técnicos en este momento. Por favor, intente nuevamente en unos momentos.",
                "model": self.model,
                "tokens_used": 0,
                "truncated": False,
                "error": str(e),
            }

    def _build_system_prompt(self) -> str:
        """Construye el system prompt para el LLM"""
        return f"""Eres el asistente virtual de KnowLigo, una empresa de soporte IT para PyMEs.

INSTRUCCIONES IMPORTANTES:
1. Responde ÚNICAMENTE basándote en el contexto proporcionado
2. Si la información no está en el contexto, di: "No tengo esa información disponible"
3. Sé profesional, conciso y directo
4. Máximo {self.max_words} palabras por respuesta
5. No inventes información ni des opiniones
6. No respondas sobre temas fuera del ámbito de soporte IT
7. Usa un tono profesional pero amigable

TU ESPECIALIDAD:
- Planes de soporte (Basic, Professional, Enterprise)
- SLA y tiempos de respuesta
- Servicios de mantenimiento preventivo
- Gestión de tickets de soporte
- Políticas y procedimientos de KnowLigo

Si te preguntan algo fuera de estos temas, indica cortésmente que solo puedes ayudar con temas de soporte IT."""

    def _format_context(self, chunks: List[Dict]) -> str:
        """Formatea chunks para incluir en el prompt"""
        if not chunks:
            return "No hay contexto disponible."

        context_parts = []
        for i, chunk in enumerate(chunks[:3], 1):  # Máximo 3 chunks
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


# Instancia singleton
_responder_instance = None


def get_responder() -> GroqResponder:
    """Obtiene una instancia singleton del responder"""
    global _responder_instance
    if _responder_instance is None:
        _responder_instance = GroqResponder()
    return _responder_instance


def generate_response(query: str, context_chunks: List[Dict]) -> Dict[str, any]:
    """
    Función de conveniencia para generar respuestas.

    Args:
        query: Pregunta del usuario
        context_chunks: Chunks de contexto

    Returns:
        Dict con response, model, tokens_used, etc.
    """
    responder = get_responder()
    return responder.generate_response(query, context_chunks)


# Script de prueba
if __name__ == "__main__":
    print("🤖 Testing Groq Responder\n")

    # Chunks de ejemplo simulados
    mock_chunks = [
        {
            "text": "KnowLigo ofrece tres planes: Basic ($199/mes, soporte 9-18h), Professional ($499/mes, soporte 24/7) y Enterprise (precio personalizado).",
            "metadata": {"source": "plans.md", "section": "Planes"},
        },
        {
            "text": "El SLA para tickets High es de 4 horas, Medium 8 horas y Low 24 horas.",
            "metadata": {"source": "sla.md", "section": "Tiempos de Respuesta"},
        },
    ]

    test_queries = [
        "¿Qué planes ofrecen?",
        "¿Cuál es el SLA para tickets urgentes?",
        "¿Cuánto cuesta el plan básico?",
    ]

    try:
        responder = GroqResponder()

        for query in test_queries:
            print(f"\n{'=' * 60}")
            print(f"Query: {query}")
            print("=" * 60)

            result = responder.generate_response(query, mock_chunks)

            print(f"\n📝 Respuesta:")
            print(result["response"])
            print(
                f"\n📊 Tokens: {result['tokens_used']} | Truncated: {result['truncated']}"
            )

    except ValueError as e:
        print(f"❌ {e}")
        print("\n💡 Crea un archivo .env con tu GROQ_API_KEY")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
