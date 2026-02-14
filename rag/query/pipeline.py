"""
Pipeline - Orquestador principal del sistema RAG.

Este módulo:
1. Coordina todos los componentes (validator, retriever, responder, intent)
2. Implementa el flujo completo de procesamiento de queries
3. Maneja rate limiting y abuse prevention
4. Registra queries para analytics
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

# Importar componentes del RAG
from .validator import QueryValidator
from .retriever import FAISSRetriever
from .reranker import CrossEncoderReranker
from .cache import SemanticCache
from .responder import GroqResponder
from .intent import IntentClassifier

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Pipeline principal que orquesta el sistema RAG"""

    def __init__(
        self, db_path: str = None, max_queries_per_hour: int = None, settings=None
    ):
        """
        Inicializa el pipeline con todos los componentes.

        Args:
            db_path: Ruta a la base de datos SQLite
            max_queries_per_hour: Límite de queries por usuario por hora
            settings: Instancia de Settings (si None, carga automáticamente)
        """
        # Cargar config centralizada
        if settings is None:
            from api.config import get_settings

            settings = get_settings()

        self._settings = settings

        # Configurar DB
        if db_path is None:
            db_path = settings.db_full_path
        self.db_path = Path(db_path)

        # Rate limiting config
        self.max_queries_per_hour = (
            max_queries_per_hour or settings.MAX_QUERIES_PER_HOUR
        )

        # Retrieval config (más candidatos para reranking)
        self.top_k = settings.TOP_K_RETRIEVAL
        self.rerank_enabled = settings.RERANK_ENABLED
        self.cache_enabled = settings.CACHE_ENABLED

        # Inicializar componentes
        logger.info("Inicializando RAG Pipeline...")

        try:
            self.validator = QueryValidator()
            logger.info("Validator cargado")

            self.retriever = FAISSRetriever(model_name=settings.EMBEDDING_MODEL)
            logger.info("Retriever cargado")

            self.responder = GroqResponder(
                api_key=settings.GROQ_API_KEY,
                model=settings.LLM_MODEL,
                max_words=settings.MAX_MESSAGE_LENGTH,
            )
            logger.info("Responder cargado")

            self.intent_classifier = IntentClassifier()
            logger.info("Intent Classifier cargado")

            if self.rerank_enabled:
                self.reranker = CrossEncoderReranker(
                    model_name=settings.RERANK_MODEL,
                    top_n=settings.RERANK_TOP_N,
                )
                logger.info("Reranker cargado")
            else:
                self.reranker = None
                logger.info("Reranker deshabilitado")

            if self.cache_enabled:
                self.cache = SemanticCache(
                    model=self.retriever.model,
                    threshold=settings.CACHE_THRESHOLD,
                    ttl_seconds=settings.CACHE_TTL_SECONDS,
                    max_size=settings.CACHE_MAX_SIZE,
                )
                logger.info("Cache semántico cargado")
            else:
                self.cache = None
                logger.info("Cache semántico deshabilitado")

            # Inicializar tabla de logs si no existe
            self._init_query_logs_table()
            logger.info("Database configurada")

            logger.info("Pipeline listo para procesar queries")

        except Exception as e:
            logger.error(f"Error inicializando pipeline: {e}")
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

            # 2. Cache semántico - buscar respuesta cacheada
            if self.cache:
                cached = self.cache.lookup(user_query)
                if cached:
                    processing_time = (datetime.now() - start_time).total_seconds()
                    logger.info(
                        f"Cache HIT (score={cached['cache_score']:.3f}) "
                        f"en {processing_time:.3f}s"
                    )

                    self._log_query(
                        user_id=user_id,
                        query=user_query,
                        intent=cached["intent"],
                        response=cached["response"],
                        success=True,
                        processing_time=processing_time,
                    )

                    return {
                        "success": True,
                        "response": cached["response"],
                        "intent": cached["intent"],
                        "sources": cached["sources"],
                        "processing_time": processing_time,
                        "cached": True,
                        "cache_score": cached["cache_score"],
                    }

            # 3. Validar query
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

            # 4. Clasificar intención
            intent_result = self.intent_classifier.classify(user_query)
            intent = intent_result["intent"].value

            logger.info(
                f"Intent: {intent} (confidence: {intent_result['confidence']:.2f})"
            )

            # 5. Recuperar contexto relevante
            logger.info(f"Buscando contexto para: '{user_query[:50]}...'")
            retrieved_chunks = self.retriever.retrieve(user_query, top_k=self.top_k)

            logger.info(f"Recuperados {len(retrieved_chunks)} chunks")

            # 6. Reranking (si está habilitado)
            if self.reranker and retrieved_chunks:
                logger.info(f"Reranking {len(retrieved_chunks)} chunks...")
                retrieved_chunks = self.reranker.rerank(user_query, retrieved_chunks)
                logger.info(
                    f"Reranked: top {len(retrieved_chunks)} chunks seleccionados"
                )

            # 7. Generar respuesta con LLM
            logger.info("Generando respuesta...")
            response_result = self.responder.generate_response(
                query=user_query,
                context_chunks=retrieved_chunks,
                conversation_history=conversation_history,
            )

            response_text = response_result["response"]
            tokens_used = response_result.get("tokens_used", 0)

            # 8. Extraer fuentes
            sources = [
                {
                    "file": chunk["metadata"].get("source", "unknown"),
                    "section": chunk["metadata"].get("section", ""),
                    "score": chunk["score"],
                }
                for chunk in retrieved_chunks
            ]

            # 9. Registrar query exitosa
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

            # 10. Guardar en cache para futuras consultas similares
            if self.cache:
                self.cache.store(
                    query=user_query,
                    response=response_text,
                    intent=intent,
                    sources=sources,
                )

            logger.info(f"Query procesada en {processing_time:.2f}s")

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
            logger.error(error_msg)

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
            logger.warning(f"Error checking rate limit: {e}")
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
            logger.warning(f"Error logging query: {e}")

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
            logger.warning(f"Error creating query_logs table: {e}")
