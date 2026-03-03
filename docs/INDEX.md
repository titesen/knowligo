# KnowLigo — Documentación del Proyecto

> Índice principal para agentes de IA y humanos.  
> Cada línea: descripción breve + ruta al archivo.

## Contexto del Proyecto
- [AGENTS.md](../AGENTS.md): Contexto completo para agentes de IA — arquitectura, reglas, patrones, límites
- [README.md](../README.md): Documentación principal — quick start, endpoints, configuración, roadmap

## Documentación Técnica
- [PRD](PRD.md): Product Requirements Document — objetivos, usuarios, features, métricas, riesgos (906 líneas)
- [Diagramas de Arquitectura](diagrams/architecture.md): Mermaid — C4, flujo de mensajes, pipeline RAG, ERD, máquina de estados
- [Quick Start](QUICK_START.md): Guía paso a paso para iniciar el proyecto
- [WhatsApp Setup](WHATSAPP_SETUP.md): Configuración de WhatsApp Business Cloud API + webhook

## Decisiones Arquitectónicas (ADR)
- [ADR-001](adr/ADR-001-sqlite-over-postgresql.md): SQLite sobre PostgreSQL — portabilidad y cero dependencias
- [ADR-002](adr/ADR-002-faiss-bm25-hybrid-retrieval.md): Retrieval híbrido FAISS + BM25 con RRF — cobertura léxica + semántica
- [ADR-003](adr/ADR-003-groq-free-tier-llm.md): Groq API free tier como LLM — costo $0 y latencia líder
- [ADR-004](adr/ADR-004-direct-webhook-over-n8n.md): Webhook directo sobre n8n — simplicidad y testabilidad

## Base de Conocimiento (RAG)
- [company.md](../knowledge/documents/company.md): Información de la empresa KnowLigo
- [plans.md](../knowledge/documents/plans.md): Planes de servicio (Básico, Profesional, Empresarial)
- [services.md](../knowledge/documents/services.md): Servicios de soporte IT
- [sla.md](../knowledge/documents/sla.md): Acuerdos de nivel de servicio
- [policies.md](../knowledge/documents/policies.md): Políticas de la empresa
- [faq.md](../knowledge/documents/faq.md): Preguntas frecuentes

## API
- OpenAPI/Swagger: `http://localhost:8000/docs` (generado automáticamente por FastAPI)
- ReDoc: `http://localhost:8000/redoc`

## Código Fuente — Mapa de Módulos
- `api/main.py`: Endpoints FastAPI — webhook, query, health, stats
- `api/config.py`: Pydantic BaseSettings — configuración centralizada
- `api/models.py`: Schemas Pydantic — request/response DTOs
- `agent/orchestrator.py`: Orquestador principal — entry point del agente conversacional
- `agent/router.py`: Clasificación de intención con LLM (Groq)
- `agent/handlers.py`: Lógica de flujos multi-turn (registro, tickets, contratos)
- `agent/conversation.py`: Máquina de estados por teléfono
- `agent/db_service.py`: Capa de acceso a datos SQLite
- `rag/query/pipeline.py`: Pipeline RAG — rate limit, cache, retrieve, rerank, respond
- `rag/query/retriever.py`: FAISS + BM25 hybrid retrieval con RRF fusion
- `rag/query/responder.py`: Generación de respuestas con Groq LLM
- `rag/query/reranker.py`: Cross-Encoder reranking
- `rag/query/cache.py`: Caché semántico FAISS
- `rag/query/validator.py`: Validación de dominio + detección prompt injection
