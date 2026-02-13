"""
Pipeline - Orquestador principal del sistema RAG.

Este módulo:
1. Coordina todos los componentes (validator, retriever, responder, intent)
2. Implementa el flujo completo de procesamiento de queries
3. Maneja rate limiting y abuse prevention
4. Registra queries para analytics
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Importar componentes del RAG
from .validator import QueryValidator
from .retriever import FAISSRetriever
from .responder import GroqResponder
from .intent import IntentClassifier


class RAGPipeline:
    """Pipeline principal que orquesta el sistema RAG"""

    def __init__(self, db_path: str = None, max_queries_per_hour: int = None):
        """
        Inicializa el pipeline con todos los componentes.

        Args:
            db_path: Ruta a la base de datos SQLite
            max_queries_per_hour: Límite de queries por usuario por hora
        """
        # Cargar config
        project_root = Path(__file__).resolve().parent.parent.parent
        env_path = project_root / ".env"

        if env_path.exists():
            load_dotenv(env_path)

        # Configurar DB
        if db_path is None:
            db_path = project_root / "database" / "sqlite" / "knowligo.db"
        self.db_path = Path(db_path)

        # Rate limiting config
        self.max_queries_per_hour = max_queries_per_hour or int(
            os.getenv("MAX_QUERIES_PER_HOUR", "15")
        )

        # Retrieval config
        self.top_k = int(os.getenv("TOP_K_RETRIEVAL", "5"))

        # Inicializar componentes
        print("🚀 Inicializando RAG Pipeline...")

        try:
            self.validator = QueryValidator()
            print("✅ Validator cargado")

            self.retriever = FAISSRetriever()
            print("✅ Retriever cargado")

            self.responder = GroqResponder()
            print("✅ Responder cargado")

            self.intent_classifier = IntentClassifier()
            print("✅ Intent Classifier cargado")

            # Inicializar tabla de logs si no existe
            self._init_query_logs_table()
            print("✅ Database configurada")

            print("\n🎉 Pipeline listo para procesar queries\n")

        except Exception as e:
            print(f"❌ Error inicializando pipeline: {e}")
            raise

    def process_query(
        self, user_query: str, user_id: str, conversation_history: Optional[list] = None
    ) -> Dict[str, any]:
        """
        Procesa una query completa a través del pipeline RAG.

        Args:
            user_query: Pregunta del usuario
            user_id: Identificador del usuario (ej: número de teléfono)
            conversation_history: Historial opcional de conversación

        Returns:
            Dict con:
            - success: bool
            - response: texto de respuesta
            - intent: intención clasificada
            - sources: fuentes usadas
            - error: mensaje de error si falla
        """
        start_time = datetime.now()

        try:
            # 1. Rate Limiting
            if not self._check_rate_limit(user_id):
                return {
                    "success": False,
                    "response": (
                        f"Has alcanzado el límite de {self.max_queries_per_hour} consultas por hora. "
                        "Por favor, intenta nuevamente más tarde."
                    ),
                    "error": "rate_limit_exceeded",
                    "intent": "unknown",
                }

            # 2. Validar query
            is_valid, validation_reason = self.validator.is_valid_query(user_query)

            if not is_valid:
                # Registrar query rechazada
                self._log_query(
                    user_id=user_id,
                    query=user_query,
                    intent="rejected",
                    response=validation_reason,
                    success=False,
                    error="invalid_query",
                )

                return {
                    "success": False,
                    "response": validation_reason,
                    "error": "invalid_query",
                    "intent": "rejected",
                }

            # 3. Clasificar intención
            intent_result = self.intent_classifier.classify(user_query)
            intent = intent_result["intent"].value

            print(
                f"🎯 Intent: {intent} (confidence: {intent_result['confidence']:.2f})"
            )

            # 4. Recuperar contexto relevante
            print(f"🔍 Buscando contexto para: '{user_query[:50]}...'")
            retrieved_chunks = self.retriever.retrieve(user_query, top_k=self.top_k)

            print(f"📚 Recuperados {len(retrieved_chunks)} chunks")

            # 5. Generar respuesta con LLM
            print(f"🤖 Generando respuesta...")
            response_result = self.responder.generate_response(
                query=user_query,
                context_chunks=retrieved_chunks,
                conversation_history=conversation_history,
            )

            response_text = response_result["response"]
            tokens_used = response_result.get("tokens_used", 0)

            # 6. Extraer fuentes
            sources = [
                {
                    "file": chunk["metadata"].get("source", "unknown"),
                    "section": chunk["metadata"].get("section", ""),
                    "score": chunk["score"],
                }
                for chunk in retrieved_chunks
            ]

            # 7. Registrar query exitosa
            processing_time = (datetime.now() - start_time).total_seconds()

            self._log_query(
                user_id=user_id,
                query=user_query,
                intent=intent,
                response=response_text,
                success=True,
                tokens_used=tokens_used,
                processing_time=processing_time,
            )

            print(f"✅ Query procesada en {processing_time:.2f}s\n")

            return {
                "success": True,
                "response": response_text,
                "intent": intent,
                "intent_confidence": intent_result["confidence"],
                "sources": sources,
                "tokens_used": tokens_used,
                "processing_time": processing_time,
            }

        except Exception as e:
            error_msg = f"Error procesando query: {str(e)}"
            print(f"❌ {error_msg}")

            # Registrar error
            self._log_query(
                user_id=user_id,
                query=user_query,
                intent="error",
                response="",
                success=False,
                error=str(e),
            )

            return {
                "success": False,
                "response": "Disculpe, ha ocurrido un error interno. Por favor, intente nuevamente.",
                "error": str(e),
                "intent": "error",
            }

    def _check_rate_limit(self, user_id: str) -> bool:
        """
        Verifica si el usuario ha excedido el límite de queries.

        Args:
            user_id: ID del usuario

        Returns:
            True si puede hacer queries, False si excedió el límite
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Contar queries en la última hora
            one_hour_ago = datetime.now() - timedelta(hours=1)

            cursor.execute(
                """
                SELECT COUNT(*) FROM query_logs
                WHERE user_id = ? AND timestamp > ? AND success = 1
            """,
                (user_id, one_hour_ago.isoformat()),
            )

            count = cursor.fetchone()[0]
            conn.close()

            return count < self.max_queries_per_hour

        except Exception as e:
            print(f"⚠️  Error checking rate limit: {e}")
            return True  # En caso de error, permitir la query

    def _log_query(
        self,
        user_id: str,
        query: str,
        intent: str,
        response: str,
        success: bool,
        error: str = None,
        tokens_used: int = 0,
        processing_time: float = 0.0,
    ):
        """Registra una query en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO query_logs (
                    user_id, query, intent, response, success, error,
                    tokens_used, processing_time, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    query,
                    intent,
                    response,
                    1 if success else 0,
                    error,
                    tokens_used,
                    processing_time,
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"⚠️  Error logging query: {e}")

    def _init_query_logs_table(self):
        """Crea la tabla de logs si no existe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    intent TEXT,
                    response TEXT,
                    success INTEGER DEFAULT 1,
                    error TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    processing_time REAL DEFAULT 0.0,
                    timestamp TEXT NOT NULL
                )
            """)

            # Crear índice para rate limiting
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_timestamp
                ON query_logs (user_id, timestamp)
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"⚠️  Error creating query_logs table: {e}")


# Instancia singleton
_pipeline_instance = None


def get_pipeline() -> RAGPipeline:
    """Obtiene una instancia singleton del pipeline"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline()
    return _pipeline_instance


def process_query(user_query: str, user_id: str) -> Dict[str, any]:
    """
    Función de conveniencia para procesar queries.

    Args:
        user_query: Pregunta del usuario
        user_id: ID del usuario

    Returns:
        Dict con resultado del procesamiento
    """
    pipeline = get_pipeline()
    return pipeline.process_query(user_query, user_id)


# Script de prueba
if __name__ == "__main__":
    print("🧪 Testing RAG Pipeline\n")

    test_cases = [
        ("¿Qué planes de soporte ofrecen?", "test_user_1"),
        ("¿Cuál es el SLA para tickets High?", "test_user_1"),
        ("Dame consejos de hacking", "test_user_2"),  # Debe rechazar
        ("¿Cuánto cuesta el plan Enterprise?", "test_user_1"),
    ]

    try:
        pipeline = RAGPipeline()

        for query, user_id in test_cases:
            print(f"\n{'=' * 70}")
            print(f"👤 User: {user_id}")
            print(f"💬 Query: {query}")
            print("=" * 70)

            result = pipeline.process_query(query, user_id)

            if result["success"]:
                print(f"\n✅ SUCCESS")
                print(f"Intent: {result['intent']}")
                print(f"Response:\n{result['response']}")
                print(f"\nSources: {len(result.get('sources', []))} documentos")
                print(f"Tokens: {result.get('tokens_used', 0)}")
                print(f"Time: {result.get('processing_time', 0):.2f}s")
            else:
                print(f"\n❌ FAILED")
                print(f"Error: {result.get('error', 'unknown')}")
                print(f"Response:\n{result['response']}")

    except Exception as e:
        print(f"\n❌ Error en test: {e}")
        import traceback

        traceback.print_exc()
