# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [1.1.0]

### Added
- **UI interactiva de WhatsApp**: Interactive Lists para menús y selección de prioridad/planes, Reply Buttons para confirmaciones y métodos de pago
- `agent/messages.py`: Modelos tipados para mensajes interactivos (TextMessage, ListMessage, ButtonMessage)
- Webhook acepta mensajes `type: "interactive"` (list_reply, button_reply)
- `tests/test_messages.py`: 25 tests para mensajes interactivos (payloads, serialización, integración)
- `scripts/evaluate_rag.py`: Evaluación RAGAS-inspired del pipeline RAG con Groq como LLM-judge

### Changed
- `agent/orchestrator.py`: `_build_menu()` retorna `ListMessage` con secciones organizadas por categoría
- `agent/handlers.py`: Flujos de tickets y contratos usan ListMessage/ButtonMessage en lugar de texto plano
- `api/main.py`: `send_whatsapp_message()` envía payloads interactivos para ListMessage/ButtonMessage
- Total de tests: 119 → 145

## [1.0.0]

### Added
- Agente conversacional completo con 10 intenciones (saludo, RAG, tickets, contratos, planes, cuenta, etc.)
- Pipeline RAG: FAISS + BM25 hybrid retrieval con RRF fusion
- Cross-Encoder reranking (ms-marco-MiniLM-L-6-v2)
- HyDE-lite query rewriting para mejor dense retrieval
- Caché semántico FAISS (threshold 0.92, TTL 3600s, LRU eviction)
- Intent routing con LLM (Groq Llama 3.3 70B, temperature=0)
- Flujos multi-turn: registro de usuario, creación de tickets, contratación de planes
- Máquina de estados conversacional por teléfono
- Detección de prompt injection (21 patrones bilingües)
- Rate limiting por usuario (30 queries/hora)
- Detección de gibberish y saludos repetidos
- Menú adaptativo según estado de registro del cliente
- API REST: /webhook, /query, /health, /stats
- Docker multi-stage build con non-root user y healthcheck
- Base de conocimiento: 6 documentos Markdown (empresa, planes, servicios, SLA, políticas, FAQ)
- Documentación: 4 ADRs, 6 diagramas Mermaid, PRD, INDEX
- 119 tests unitarios e integración con pytest
