"""
FastAPI Application - API REST para KnowLigo RAG Chatbot

Expone endpoints para:
- Procesar queries del chatbot
- Health checks
- Métricas básicas
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# Agregar directorio raíz al path para imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from api.models import QueryRequest, QueryResponse, HealthResponse, SourceInfo
from rag.query.pipeline import RAGPipeline

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Inicializar pipeline (lazy loading)
_pipeline = None


def get_pipeline() -> RAGPipeline:
    """Obtiene o inicializa el pipeline RAG"""
    global _pipeline
    if _pipeline is None:
        logger.info("Inicializando RAG Pipeline...")
        _pipeline = RAGPipeline()
        logger.info("Pipeline inicializado correctamente")
    return _pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler"""
    # Startup
    logger.info("🚀 KnowLigo API iniciando...")
    try:
        get_pipeline()
        logger.info("✅ Pipeline pre-cargado")
    except Exception as e:
        logger.error(f"❌ Error inicializando pipeline: {e}")

    yield

    # Shutdown
    logger.info("👋 KnowLigo API cerrando...")


# Crear app
app = FastAPI(
    title="KnowLigo RAG API",
    description="API REST para chatbot de soporte IT con RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware (para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz"""
    return {
        "message": "KnowLigo RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Verifica el estado de:
    - Base de datos
    - Índice FAISS
    - Groq API (via API key)
    """
    components = {}
    overall_status = "healthy"

    try:
        pipeline = get_pipeline()

        # Check database
        try:
            if pipeline.db_path.exists():
                components["database"] = "ok"
            else:
                components["database"] = "missing"
                overall_status = "degraded"
        except Exception as e:
            components["database"] = f"error: {str(e)}"
            overall_status = "degraded"

        # Check FAISS index
        try:
            if pipeline.retriever.index.ntotal > 0:
                components["faiss_index"] = (
                    f"ok ({pipeline.retriever.index.ntotal} vectors)"
                )
            else:
                components["faiss_index"] = "empty"
                overall_status = "degraded"
        except Exception as e:
            components["faiss_index"] = f"error: {str(e)}"
            overall_status = "unhealthy"

        # Check Groq API (verificar que existe API key)
        try:
            if pipeline.responder.client.api_key:
                components["groq_api"] = "ok"
            else:
                components["groq_api"] = "no_api_key"
                overall_status = "degraded"
        except Exception as e:
            components["groq_api"] = f"error: {str(e)}"
            overall_status = "degraded"

    except Exception as e:
        logger.error(f"Error en health check: {e}")
        overall_status = "unhealthy"
        components["pipeline"] = f"error: {str(e)}"

    return HealthResponse(status=overall_status, version="1.0.0", components=components)


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def process_query(request: QueryRequest):
    """
    Procesa una query del usuario a través del pipeline RAG.

    **Flujo:**
    1. Validación de dominio
    2. Rate limiting
    3. Clasificación de intención
    4. Recuperación de contexto (FAISS)
    5. Generación de respuesta (Groq LLM)
    6. Logging

    **Rate Limiting:**
    - Máximo 10 queries por usuario por hora (configurable)

    **Errores posibles:**
    - 400: Query inválida o fuera de dominio
    - 429: Rate limit excedido
    - 500: Error interno del pipeline
    """
    try:
        logger.info(
            f"Query recibida de user {request.user_id}: {request.message[:50]}..."
        )

        # Obtener pipeline
        pipeline = get_pipeline()

        # Procesar query
        result = pipeline.process_query(
            user_query=request.message,
            user_id=request.user_id,
            conversation_history=request.conversation_history,
        )

        # Mapear resultado a response model
        if result["success"]:
            logger.info(f"Query procesada exitosamente para {request.user_id}")

            # Convertir sources a SourceInfo objects
            sources = None
            if "sources" in result and result["sources"]:
                sources = [
                    SourceInfo(
                        file=src["file"],
                        section=src.get("section", ""),
                        score=src["score"],
                    )
                    for src in result["sources"]
                ]

            return QueryResponse(
                success=True,
                response=result["response"],
                intent=result["intent"],
                intent_confidence=result.get("intent_confidence"),
                sources=sources,
                tokens_used=result.get("tokens_used"),
                processing_time=result.get("processing_time"),
                error=None,
            )
        else:
            # Error en el procesamiento
            error_type = result.get("error", "unknown")

            # Rate limit
            if error_type == "rate_limit_exceeded":
                logger.warning(f"Rate limit excedido para {request.user_id}")
                return QueryResponse(
                    success=False,
                    response=result["response"],
                    intent=result["intent"],
                    error=error_type,
                )

            # Query inválida
            elif error_type == "invalid_query":
                logger.info(f"Query inválida de {request.user_id}")
                return QueryResponse(
                    success=False,
                    response=result["response"],
                    intent=result["intent"],
                    error=error_type,
                )

            # Otro error
            else:
                logger.error(f"Error procesando query: {error_type}")
                return QueryResponse(
                    success=False,
                    response=result["response"],
                    intent=result.get("intent", "error"),
                    error=error_type,
                )

    except Exception as e:
        logger.error(f"Error inesperado en /query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@app.get("/stats", tags=["Stats"])
async def get_stats():
    """
    Obtiene estadísticas básicas del sistema.

    Retorna:
    - Total de queries procesadas
    - Queries por intent
    - Rate de éxito
    """
    try:
        import sqlite3

        pipeline = get_pipeline()

        conn = sqlite3.connect(pipeline.db_path)
        cursor = conn.cursor()

        # Total queries
        cursor.execute("SELECT COUNT(*) FROM query_logs")
        total_queries = cursor.fetchone()[0]

        # Queries exitosas
        cursor.execute("SELECT COUNT(*) FROM query_logs WHERE success = 1")
        successful_queries = cursor.fetchone()[0]

        # Queries por intent
        cursor.execute("""
            SELECT intent, COUNT(*) as count 
            FROM query_logs 
            GROUP BY intent 
            ORDER BY count DESC
        """)
        intent_stats = {row[0]: row[1] for row in cursor.fetchall()}

        # Usuarios únicos
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM query_logs")
        unique_users = cursor.fetchone()[0]

        conn.close()

        success_rate = (
            (successful_queries / total_queries * 100) if total_queries > 0 else 0
        )

        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "success_rate": f"{success_rate:.2f}%",
            "unique_users": unique_users,
            "intent_distribution": intent_stats,
        }

    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}",
        )


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handler para 404"""
    return JSONResponse(status_code=404, content={"detail": "Endpoint no encontrado"})


if __name__ == "__main__":
    import uvicorn

    # Configuración para desarrollo
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
