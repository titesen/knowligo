"""
FastAPI Application - API REST para KnowLigo RAG Chatbot
- Settings centralizado (Pydantic BaseSettings via config.py)
- Dependency Injection con Depends()
- HTTP Status Codes correctos + Error Handler global
- Async con asyncio.to_thread para operaciones bloqueantes

Endpoints:
- GET  /          → Raíz informativa
- GET  /health    → Health check
- GET  /webhook   → Verificación de WhatsApp
- POST /webhook   → Mensajes entrantes de WhatsApp
- POST /query     → Procesar query RAG
- GET  /stats     → Estadísticas del sistema
"""

import asyncio
import sys
import time
import httpx
import sqlite3
import logging
from collections import OrderedDict
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError

# Agregar directorio raíz al path para imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from api.config import Settings, get_settings
from api.models import (
    QueryRequest,
    QueryResponse,
    HealthResponse,
    SourceInfo,
    ErrorResponse,
)
from rag.query.pipeline import RAGPipeline
from agent.orchestrator import AgentOrchestrator

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Message deduplication — prevent double-processing of WhatsApp retries
_MAX_SEEN = 500
_SEEN_TTL = 300  # 5 minutes
_seen_messages: OrderedDict[str, float] = OrderedDict()


def _is_duplicate_message(msg_id: str) -> bool:
    """Returns True if this message ID was already processed recently."""
    now = time.monotonic()
    # Purge expired entries
    while _seen_messages:
        oldest_key, oldest_time = next(iter(_seen_messages.items()))
        if now - oldest_time > _SEEN_TTL:
            _seen_messages.pop(oldest_key)
        else:
            break
    if msg_id in _seen_messages:
        return True
    _seen_messages[msg_id] = now
    # Cap size
    while len(_seen_messages) > _MAX_SEEN:
        _seen_messages.popitem(last=False)
    return False


# Dependency Injection
# Singleton del pipeline, inyectable via Depends() para facilitar testing

_pipeline: RAGPipeline | None = None
_orchestrator: AgentOrchestrator | None = None


def get_pipeline(settings: Settings = Depends(get_settings)) -> RAGPipeline:
    """
    Dependency que provee el pipeline RAG.

    Permite override en tests via app.dependency_overrides[get_pipeline].
    """
    global _pipeline
    if _pipeline is None:
        logger.info("Inicializando RAG Pipeline...")
        _pipeline = RAGPipeline(settings=settings)
        logger.info("Pipeline inicializado correctamente")
    return _pipeline


def get_orchestrator(settings: Settings = Depends(get_settings)) -> AgentOrchestrator:
    """
    Dependency que provee el AgentOrchestrator.

    Crea el orchestrator con el pipeline RAG inyectado.
    Permite override en tests via app.dependency_overrides[get_orchestrator].
    """
    global _orchestrator
    if _orchestrator is None:
        pipeline = get_pipeline(settings)
        logger.info("Inicializando AgentOrchestrator...")
        _orchestrator = AgentOrchestrator(
            db_path=settings.db_full_path,
            groq_api_key=settings.GROQ_API_KEY,
            llm_model=settings.LLM_MODEL,
            rag_pipeline=pipeline,
        )
        logger.info("AgentOrchestrator inicializado correctamente")
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler: pre-carga el pipeline al startup."""
    logger.info("KnowLigo API iniciando...")
    try:
        settings = get_settings()
        get_pipeline(settings)
        get_orchestrator(settings)
        logger.info("Pipeline y Orchestrator pre-cargados")
    except Exception as e:
        logger.error(f"Error inicializando pipeline/orchestrator: {e}")

    yield
    logger.info("KnowLigo API cerrando...")


# FastAPI App

app = FastAPI(
    title="KnowLigo RAG API",
    description="API REST para chatbot de soporte IT con RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    responses={
        422: {"model": ErrorResponse, "description": "Error de validación"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
)

# CORS middleware (para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Error Handlers


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Errores de validación Pydantic → 422 con formato ErrorResponse."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            type="validation_error",
            title="Datos de entrada inválidos",
            status=422,
            detail=str(exc.errors()),
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTPException → ErrorResponse con el status original."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            type="http_error",
            title=exc.detail if isinstance(exc.detail, str) else "Error",
            status=exc.status_code,
            detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Excepción no manejada → 500 genérico.

    Loguea el error real pero devuelve mensaje genérico al cliente
    para no filtrar detalles internos (Best Practices §4.2).
    """
    logger.error(f"Error no manejado en {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            type="internal_error",
            title="Error Interno",
            status=500,
            detail="Error interno del servidor. Intenta nuevamente más tarde.",
        ).model_dump(),
    )


# Endpoints


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
async def health_check(pipeline: RAGPipeline = Depends(get_pipeline)):
    """
    Health check endpoint.

    Verifica el estado de:
    - Base de datos
    - Índice FAISS
    - Groq API (via API key)
    """
    components = {}
    overall_status = "healthy"

    # Check database
    try:
        if pipeline.db_path.exists():
            components["database"] = "ok"
        else:
            components["database"] = "missing"
            overall_status = "degraded"
    except Exception:
        components["database"] = "error"
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
    except Exception:
        components["faiss_index"] = "error"
        overall_status = "unhealthy"

    # Check Groq API
    try:
        if pipeline.responder.client.api_key:
            components["groq_api"] = "ok"
        else:
            components["groq_api"] = "no_api_key"
            overall_status = "degraded"
    except Exception:
        components["groq_api"] = "error"
        overall_status = "degraded"

    return HealthResponse(status=overall_status, version="1.0.0", components=components)


@app.get("/webhook", tags=["Webhook"])
async def verify_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """
    Verificación del webhook de WhatsApp (Meta).

    Meta envía un GET request con:
    - hub.mode=subscribe
    - hub.verify_token=<tu_token>
    - hub.challenge=<string_aleatorio>

    Debemos validar el token y devolver el challenge como texto plano.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    verify_token = settings.WHATSAPP_VERIFY_TOKEN

    logger.info(
        f"🔐 Webhook verification request: mode={mode}, token={'***' if token else 'None'}, challenge={challenge}"
    )
    logger.info(f"🔐 Expected verify token: {verify_token}")

    if mode == "subscribe" and token == verify_token:
        logger.info("✅ Webhook verificado correctamente")
        # Meta espera SOLO el challenge como texto plano
        return PlainTextResponse(content=challenge, status_code=200)
    else:
        logger.warning(
            f"❌ Webhook verification failed. mode={mode}, token_match={token == verify_token}"
        )
        raise HTTPException(status_code=403, detail="Verification failed")


async def send_whatsapp_message(to: str, message: str, settings: Settings):
    """
    Envía un mensaje de WhatsApp usando la Cloud API de Meta.
    """
    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    whatsapp_token = settings.WHATSAPP_TOKEN

    if not phone_number_id or not whatsapp_token:
        logger.error(
            "❌ WHATSAPP_PHONE_NUMBER_ID o WHATSAPP_TOKEN no configurados en .env"
        )
        return False

    # Normalizar número argentino: WhatsApp envía 5493794285297 (con 9)
    # pero Meta puede requerir 543794285297 (sin 9). Intentar ambos formatos.
    normalized_to = to
    is_argentine_mobile = to.startswith("549") and len(to) == 13
    if is_argentine_mobile:
        # Probar sin el 9 primero (formato que Meta registra)
        normalized_to = "54" + to[3:]
        logger.info(
            f"📱 Número argentino detectado: {to} → normalizado a {normalized_to}"
        )

    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": normalized_to,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                logger.info(f"✅ Mensaje enviado a {normalized_to}")
                return True
            else:
                logger.warning(
                    f"⚠️ Error con {normalized_to}: {response.status_code} - {response.text}"
                )
                # Si falló con formato sin 9, intentar con el original (con 9)
                if normalized_to != to:
                    logger.info(f"🔄 Reintentando con formato original: {to}")
                    payload["to"] = to
                    response2 = await client.post(url, json=payload, headers=headers)
                    if response2.status_code == 200:
                        logger.info(f"✅ Mensaje enviado a {to} (formato original)")
                        return True
                    else:
                        logger.error(
                            f"❌ Error enviando mensaje: {response2.status_code} - {response2.text}"
                        )
                return False
    except Exception as e:
        logger.error(f"❌ Excepción enviando mensaje WhatsApp: {e}")
        return False


@app.post("/webhook", tags=["Webhook"])
async def handle_webhook(
    request: Request,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings),
):
    """
    Recibe mensajes de WhatsApp desde Meta.

    Procesa el mensaje a través del AgentOrchestrator que decide:
    - Si hay un flujo multi-turn activo → continúa el handler
    - Si no → clasifica intención y despacha (RAG, tickets, contratos, etc.)
    """
    try:
        body = await request.json()
        logger.info("Webhook POST recibido")

        # Validar que sea un evento de WhatsApp Business
        if body.get("object") != "whatsapp_business_account":
            logger.info("Evento ignorado (no es whatsapp_business_account)")
            return {"status": "ignored"}

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Ignorar si no hay mensajes (puede ser status update, etc.)
                if "messages" not in value:
                    continue

                for message in value["messages"]:
                    # Deduplicate (WhatsApp may retry delivery)
                    msg_id = message.get("id", "")
                    if msg_id and _is_duplicate_message(msg_id):
                        logger.info(f"Mensaje duplicado ignorado: {msg_id}")
                        continue

                    # Solo procesar mensajes de texto
                    if message.get("type") != "text":
                        logger.info(
                            f"Mensaje no-texto ignorado: tipo={message.get('type')}"
                        )
                        await send_whatsapp_message(
                            message["from"],
                            "Disculpe, solo puedo procesar mensajes de texto.",
                            settings,
                        )
                        continue

                    from_number = message["from"]
                    message_body = message.get("text", {}).get("body", "")

                    logger.info(f"Mensaje de {from_number}: {message_body}")

                    # Procesar a través del AgentOrchestrator (no bloquea event loop)
                    try:
                        response_text = await asyncio.to_thread(
                            orchestrator.process_message,
                            raw_phone=from_number,
                            message=message_body,
                        )
                    except Exception as e:
                        logger.error(f"Error en orchestrator: {e}", exc_info=True)
                        response_text = (
                            "Disculpe, tengo problemas técnicos en este momento. "
                            "Por favor, intente nuevamente en unos momentos."
                        )

                    # Enviar respuesta por WhatsApp
                    await send_whatsapp_message(from_number, response_text, settings)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error procesando webhook: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                type="webhook_error",
                title="Error procesando webhook",
                status=500,
                detail="Error interno procesando el mensaje.",
            ).model_dump(),
        )


@app.post(
    "/query",
    response_model=QueryResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Query inválida o fuera de dominio",
        },
        429: {"model": ErrorResponse, "description": "Rate limit excedido"},
    },
    tags=["Query"],
)
async def process_query(
    request: QueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    """
    Procesa una query del usuario a través del pipeline RAG.

    **Flujo:**
    1. Validación de dominio
    2. Rate limiting
    3. Clasificación de intención
    4. Recuperación de contexto (FAISS)
    5. Generación de respuesta (Groq LLM)
    6. Logging

    **Errores posibles:**
    - 400: Query inválida o fuera de dominio
    - 429: Rate limit excedido
    - 500: Error interno del pipeline
    """
    logger.info(f"Query recibida de user {request.user_id}: {request.message[:50]}...")

    # Procesar query (no bloquea el event loop)
    result = await asyncio.to_thread(
        pipeline.process_query,
        user_query=request.message,
        user_id=request.user_id,
        conversation_history=request.conversation_history,
    )

    # Success
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

    # Rate Limit → 429
    error_type = result.get("error", "unknown")

    if error_type == "rate_limit_exceeded":
        logger.warning(f"Rate limit excedido para {request.user_id}")
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                type="rate_limit",
                title="Rate Limit Exceeded",
                status=429,
                detail=result["response"],
            ).model_dump(),
        )

    # Query Inválida → 400
    if error_type == "invalid_query":
        logger.info(f"Query inválida de {request.user_id}")
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                type="invalid_query",
                title="Query Inválida",
                status=400,
                detail=result["response"],
            ).model_dump(),
        )

    # Otro error del pipeline → 500
    logger.error(f"Error procesando query: {error_type}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            type="pipeline_error",
            title="Error de Procesamiento",
            status=500,
            detail="Error procesando la consulta. Intenta nuevamente.",
        ).model_dump(),
    )


@app.get("/stats", tags=["Stats"])
async def get_stats(pipeline: RAGPipeline = Depends(get_pipeline)):
    """
    Obtiene estadísticas básicas del sistema.

    Retorna:
    - Total de queries procesadas
    - Queries por intent
    - Rate de éxito
    """

    def _fetch_stats(db_path):
        """Operación bloqueante de SQLite, ejecutada en thread."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM query_logs")
        total_queries = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM query_logs WHERE success = 1")
        successful_queries = cursor.fetchone()[0]

        cursor.execute("""
            SELECT intent, COUNT(*) as count 
            FROM query_logs 
            GROUP BY intent 
            ORDER BY count DESC
        """)
        intent_stats = {row[0]: row[1] for row in cursor.fetchall()}

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

    return await asyncio.to_thread(_fetch_stats, pipeline.db_path)


# Error Handler 404


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handler para 404"""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            type="not_found",
            title="No Encontrado",
            status=404,
            detail=f"El endpoint '{request.url.path}' no existe.",
        ).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info",
    )
