# AGENTS.md — Contexto para Agentes de IA

> Este archivo es la **memoria a largo plazo** del repositorio para agentes de codificación (Copilot, Claude, Cursor, etc.).
> Léelo completo antes de realizar cualquier cambio.

---

## 1. Identidad del Proyecto

**KnowLigo** es un agente conversacional de soporte IT para WhatsApp con RAG, flujos multi-turn y gestión transaccional.

- **Stack**: Python 3.11 · FastAPI 0.115 · Pydantic v2 · SQLite · FAISS · Groq API (Llama 3.3 70B)
- **Idioma del negocio**: Español (Argentina)
- **Idioma del código**: Inglés (nombres de variables, funciones, clases) · Español (docstrings, comments, user-facing strings)
- **Propósito**: Proyecto educativo/demo para LinkedIn — debe ser legible, bien documentado y funcional

---

## 2. Contrato de Validación (Build & Test)

```powershell
# Ejecutar TODOS los tests (145 tests, debe dar 0 failures)
py -3.11 -m pytest tests/ -v --tb=short

# Solo tests rápidos (sin cargar modelos ML)
py -3.11 -m pytest tests/test_api.py tests/test_models.py tests/test_conversation.py -v

# Verificar tipos / imports
py -3.11 -c "from api.main import app; print('OK')"
```

**Regla**: Después de cada cambio, ejecuta la suite completa. No hagas PR/commit si hay tests rotos.

---

## 3. Arquitectura de Capas y Límites

```
api/           → Capa de PRESENTACIÓN (FastAPI endpoints, Pydantic DTOs)
agent/         → Capa de LÓGICA DE NEGOCIO (orquestador, router, handlers, DB service)
rag/query/     → Capa de INFRAESTRUCTURA RAG (pipeline, retriever, responder, cache)
rag/ingest/    → Scripts OFFLINE de ingesta (chunker, build_index)
database/      → Schema SQL y seeds
knowledge/     → Base de conocimiento (Markdown docs para RAG)
tests/         → Tests unitarios + integración
scripts/       → Herramientas CLI (no se importan desde código runtime)
```

### Reglas de dependencia (NUNCA violar)

- `api/` → puede importar de `agent/` y `rag/query/`
- `agent/` → puede importar de `agent/` (interno) y `rag/query/`
- `rag/query/` → NO puede importar de `agent/` ni de `api/`
- `rag/ingest/` → módulo independiente, solo se ejecuta como script
- `scripts/` → puede importar de cualquier capa (son herramientas de desarrollo)
- `tests/` → puede importar de cualquier capa

### Flujo de una request (WhatsApp → Respuesta)

```
POST /webhook → api/main.py
  → asyncio.to_thread(orchestrator.process_message)
    → agent/orchestrator.py: normalize → find_client → check_state
      → Si hay flujo activo: agent/handlers.py (multi-turn)
      → Si no: agent/router.py (LLM classify intent)
        → dispatch a handler correcto O rag/query/pipeline.py
    → response string
  → send_whatsapp_message (httpx async)
```

---

## 4. Patrones Clave

### 4.1 Async/Sync
- **Endpoints**: siempre `async def`
- **Operaciones bloqueantes** (SQLite, ML inference, Groq API): siempre via `asyncio.to_thread()`
- **HTTP saliente** (WhatsApp): `httpx.AsyncClient` con timeout explícito
- **NUNCA** código bloqueante directo en un endpoint async

### 4.2 Configuración
- **Un solo punto**: `api/config.py` con `Pydantic BaseSettings`
- **NUNCA** hacer `load_dotenv()` en otros módulos
- **NUNCA** hardcodear API keys, URLs o magic numbers — todo va a `Settings`

### 4.3 Base de Datos
- **Acceso**: siempre via `agent/db_service.py` (métodos tipados)
- **NUNCA** SQL inline en orchestrator ni handlers
- **Parámetros**: siempre `?` placeholders (prevención SQL injection)
- **Conexiones**: `with self._conn() as conn:` (context manager)

### 4.4 Error Handling
- **Global handlers** en `api/main.py` para 422, 404, HTTP errors, Exception genérica
- **Formato de error**: siempre `ErrorResponse` (RFC 7807: type, title, status, detail)
- **NUNCA** filtrar stack traces al cliente — loguear con `exc_info=True`, responder genérico
- **Logging**: siempre `logger = logging.getLogger(__name__)` — NUNCA `print()`

### 4.5 Testing
- **DI overrides**: `app.dependency_overrides` en `conftest.py` para mockear pipeline/orchestrator
- **Tests deterministas**: mockear Groq API, no depender de servicios externos
- **Nomenclatura**: `tests/test_<módulo>.py` con clases `Test<Feature>`

---

## 5. Reglas Always / Ask / Never

### Always (hacer sin preguntar)
- Ejecutar `pytest` después de cada cambio
- Usar `logger` (nunca `print`) en código runtime (`api/`, `agent/`, `rag/query/`)
- Docstring en módulos, clases, y funciones públicas
- Usar type hints en firmas de funciones
- Validar inputs con Pydantic en la capa API
- Mantener `ErrorResponse` (RFC 7807) para toda respuesta de error

### Ask (pedir aprobación humana)
- Cambios al schema de base de datos (`database/schema/schema.sql`)
- Agregar nuevas dependencias a `requirements.txt`
- Modificar el flujo del orchestrator (`process_message`)
- Cambiar la lógica del router de intenciones
- Cambiar settings o sus defaults en `api/config.py`
- Refactorizaciones que toquen más de 3 archivos

### Never (prohibido)
- Commitear API keys, tokens o secretos (ni en tests)
- Eliminar tests existentes sin reemplazo equivalente
- Usar `print()` en código runtime (solo permitido en `scripts/` y `rag/ingest/`)
- Usar `exit()` o `sys.exit()` en código runtime
- Importar desde `rag/query/` hacia `agent/` rompiendo la dirección de dependencias
- Hacer SQL inline fuera de `db_service.py`
- Poner lógica de negocio en los endpoints de FastAPI (va en `agent/`)

---

## 6. Decisiones Arquitectónicas (ADRs)

Consultar `docs/adr/` para el razonamiento detrás de decisiones clave:

| ADR | Decisión |
|-----|----------|
| [ADR-001](docs/adr/ADR-001-sqlite-over-postgresql.md) | SQLite sobre PostgreSQL |
| [ADR-002](docs/adr/ADR-002-faiss-bm25-hybrid-retrieval.md) | FAISS + BM25 híbrido con RRF |
| [ADR-003](docs/adr/ADR-003-groq-free-tier-llm.md) | Groq API (free tier) como LLM |
| [ADR-004](docs/adr/ADR-004-direct-webhook-over-n8n.md) | Webhook directo en FastAPI sobre n8n |

---

## 7. Estructura de Tests

```
tests/
├── conftest.py           → Fixtures: test_settings, mock_pipeline, mock_orchestrator, client
├── test_api.py           → Endpoints HTTP (200, 400, 404, 422, 429)
├── test_orchestrator.py  → 55 tests: flujos completos del agente
├── test_messages.py      → 25 tests: mensajes interactivos WhatsApp (payloads, tipos, IDs)
├── test_db_service.py    → CRUD: clients, tickets, contracts, payments
├── test_conversation.py  → Máquina de estados
├── test_intent.py        → Clasificador de intenciones
├── test_models.py        → Schemas Pydantic
├── test_validator.py     → Validación de dominio + prompt injection
```

Total: **145 tests** · Tiempo: ~37s (carga modelo de embeddings)

---

## 8. Variables de Entorno Críticas

| Variable | Requerida | Default | Propósito |
|----------|-----------|---------|-----------|
| `GROQ_API_KEY` | **Sí** | — | API key de Groq para LLM |
| `LLM_MODEL` | No | `llama-3.3-70b-versatile` | Modelo de lenguaje |
| `MAX_QUERIES_PER_HOUR` | No | `30` | Rate limit por usuario (solo RAG queries) |
| `RERANK_ENABLED` | No | `true` | Cross-Encoder reranking |
| `CACHE_ENABLED` | No | `true` | Caché semántico FAISS |
| `WHATSAPP_TOKEN` | No | — | Token de WhatsApp Business API |
| `WHATSAPP_PHONE_NUMBER_ID` | No | — | Phone Number ID de Meta |
