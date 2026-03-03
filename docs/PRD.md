# Product Requirements Document (PRD)
# KnowLigo - RAG-Powered IT Support Chatbot

---

## 📌 Resumen 

**KnowLigo** es un chatbot inteligente de soporte IT para PyMEs que opera a través de WhatsApp Business, implementando tecnología RAG (Retrieval-Augmented Generation) para proporcionar respuestas precisas y contextuales sobre servicios de soporte técnico, planes, políticas y SLAs.

### Propuesta de Valor

- **Para clientes:** Acceso 24/7 a información de servicios IT y resolución instantánea de consultas comunes
- **Para la empresa:** Automatización de consultas frecuentes, reducción de carga operativa y escalabilidad sin aumentar personal
- **Para el equipo técnico:** Base de conocimiento estructurada y trazabilidad de consultas

---

## 🎯 Objetivos del Producto

### Objetivos de Negocio

1. **Automatizar el 70%** de las consultas frecuentes de clientes
2. **Reducir en 50%** el tiempo de respuesta promedio a consultas básicas
3. **Mejorar la satisfacción del cliente** mediante disponibilidad 24/7
4. **Escalar el soporte** sin aumentar costos operativos linealmente
5. **Capturar métricas** de consultas para optimización continua

### Objetivos Técnicos

1. Implementar un sistema RAG robusto con precisión >85% en recuperación de información
2. Mantener tiempo de respuesta <3 segundos en el 95% de las consultas
3. Lograr 99.5% de uptime del servicio
4. Implementar rate limiting y abuse prevention efectivos
5. Garantizar costo operativo <$50/mes usando servicios freemium

---

## 👥 Usuarios y Stakeholders

### Usuarios Primarios

**Clientes de KnowLigo (PyMEs)**
- **Perfil:** Empresas pequeñas y medianas con 5-50 empleados
- **Necesidades:** Soporte técnico rápido, información sobre planes y SLAs, gestión de tickets
- **Comportamiento:** Prefieren canales de mensajería instantánea, buscan respuestas inmediatas
- **Contexto de uso:** Horario laboral principalmente, pero con necesidad ocasional fuera de horario

### Usuarios Secundarios

**Equipo de Soporte IT de KnowLigo**
- **Necesidades:** Reducir carga de consultas repetitivas, acceso a analytics de consultas
- **Uso:** Revisar logs de conversaciones, ajustar base de conocimiento

### Stakeholders

- **Management:** ROI, métricas de adopción, satisfacción del cliente
- **Equipo Técnico:** Mantenibilidad, escalabilidad, observabilidad
- **Compliance:** Privacidad de datos, cumplimiento normativo

---

## 🔑 Características Principales

### MVP (Versión 1.0)

#### 1. Sistema RAG Conversacional

**Descripción:** Motor de procesamiento de lenguaje natural que responde consultas usando contexto de documentos empresariales.

**Componentes:**
- **Validator:** Filtra consultas off-topic (insultos, spam, temas no relacionados)
- **Intent Classifier:** Clasifica intención (planes, SLA, mantenimiento, tickets, FAQs, empresa)
- **Retriever:** Búsqueda vectorial en FAISS con embeddings paraphrase-multilingual-MiniLM-L12-v2
- **Responder:** Generación de respuestas naturales con Groq API (Llama 3.3 70B)

**Flujo:**
```
User Query → Validation → Intent → Retrieval → LLM Response → WhatsApp
```

#### 2. Integración WhatsApp Business

**Descripción:** Canal de comunicación principal vía WhatsApp Business API.

**Implementación:**
- FastAPI webhook directo para recibir/enviar mensajes
- Verificación de webhook con token
- Envío de respuestas vía WhatsApp Cloud API
- Gestión de sesiones de usuario

**Capacidades:**
- Recepción de mensajes de texto e interactivos (list_reply, button_reply)
- Envío de respuestas con formato de texto
- Envío de mensajes interactivos (Interactive Lists, Reply Buttons)
- Manejo de multimedia (limitado en MVP)

#### 3. Control de Uso y Abuse Prevention

**Descripción:** Protección contra uso indebido y DoS.

**Características:**
- Rate limiting: 15 consultas/hora por usuario (configurable)
- Límite de longitud de mensaje: 150 caracteres (configurable)
- Detección de contenido inapropiado
- Blacklist de usuarios abusivos

#### 4. Logging y Analytics

**Descripción:** Registro de todas las interacciones para análisis.

**Datos capturados:**
- User ID (hash por privacidad)
- Query original
- Intent clasificado
- Respuesta generada
- Timestamp
- Success/error status
- Fuentes consultadas

**Almacenamiento:** SQLite (database/sqlite/knowligo.db)

#### 5. API REST

**Descripción:** FastAPI con endpoints para integración.

**Endpoints:**
- `POST /query` - Procesar consulta del chatbot
- `GET /health` - Health check del sistema
- `GET /metrics` - Métricas básicas (consultas, intents, errores)
- `GET /docs` - Documentación interactiva (Swagger)

#### 6. Base de Conocimiento

**Documentos vectorizados:**
- **company.md** - Información general de KnowLigo
- **faq.md** - Preguntas frecuentes
- **plans.md** - Planes de servicio (Básico, Profesional, Empresarial)
- **policies.md** - Políticas de uso y privacidad
- **services.md** - Servicios ofrecidos
- **sla.md** - Service Level Agreements

**Proceso de indexación:**
1. Chunking semántico (markdown headers)
2. Embeddings con Sentence Transformers
3. Almacenamiento en FAISS
4. Metadata en JSON para trazabilidad

---

## ⚙️ Requisitos Funcionales

### RF-01: Procesamiento de Consultas

**Prioridad:** Alta  
**Descripción:** El sistema debe procesar consultas en lenguaje natural y generar respuestas precisas.

**Criterios de Aceptación:**
- [ ] Responder en <3 segundos el 95% de las consultas
- [ ] Proporcionar fuentes para respuestas (archivos consultados)
- [ ] Manejar consultas en español de Argentina
- [ ] Detectar queries off-topic con >90% precisión
- [ ] Clasificar intención con >85% accuracy

### RF-02: Validación de Queries

**Prioridad:** Alta  
**Descripción:** Filtrar y rechazar consultas inapropiadas o fuera de alcance.

**Criterios de Aceptación:**
- [ ] Detectar insultos y lenguaje ofensivo
- [ ] Rechazar consultas sobre temas no IT/soporte
- [ ] Limitar longitud de mensajes a 150 caracteres
- [ ] Proporcionar mensaje explicativo al rechazar

### RF-03: Clasificación de Intención

**Prioridad:** Media  
**Descripción:** Clasificar queries en categorías predefinidas.

**Categorías:**
- `planes` - Consultas sobre planes de servicio
- `sla` - Preguntas sobre SLAs
- `mantenimiento` - Mantenimiento preventivo
- `tickets` - Gestión de incidencias
- `faq` - Preguntas frecuentes
- `empresa` - Información general
- `saludo` - Saludos/despedidas
- `otro` - No clasificable

**Criterios de Aceptación:**
- [ ] Clasificar correctamente >85% de las queries
- [ ] Retornar score de confianza
- [ ] Usar intent para enriquecer contexto de recuperación

### RF-04: Recuperación de Contexto

**Prioridad:** Alta  
**Descripción:** Buscar información relevante en la base de conocimiento.

**Criterios de Aceptación:**
- [ ] Recuperar top-3 chunks más relevantes
- [ ] Usar similitud coseno >0.2 como threshold
- [ ] Incluir metadata de fuente (archivo, sección)
- [ ] Ordenar por relevancia

### RF-05: Generación de Respuestas

**Prioridad:** Alta  
**Descripción:** Generar respuestas naturales usando LLM con contexto recuperado.

**Criterios de Aceptación:**
- [ ] Respuestas coherentes y bien estructuradas
- [ ] Máximo 150 palabras por respuesta
- [ ] Tono profesional pero amigable
- [ ] Citar fuentes cuando sea relevante
- [ ] Admitir cuando no tiene información

### RF-06: Rate Limiting

**Prioridad:** Alta  
**Descripción:** Limitar consultas por usuario para prevenir abuso.

**Criterios de Aceptación:**
- [ ] Máximo 15 queries/hora por user_id
- [ ] Mensaje claro cuando se excede límite
- [ ] Reset automático después de 1 hora
- [ ] Configuración via variable de entorno

### RF-07: Logging de Interacciones

**Prioridad:** Media  
**Descripción:** Registrar todas las interacciones para análisis.

**Criterios de Aceptación:**
- [ ] Almacenar user_id (anonimizado), query, intent, response
- [ ] Timestamp de cada interacción
- [ ] Estado success/error
- [ ] Tiempo de procesamiento
- [ ] Tokens consumidos

### RF-08: Health Check

**Prioridad:** Media  
**Descripción:** Endpoint para verificar estado del sistema.

**Criterios de Aceptación:**
- [ ] Verificar conexión a base de datos
- [ ] Verificar índice FAISS cargado
- [ ] Verificar conectividad con Groq API
- [ ] Retornar JSON con estado de componentes

### RF-09: Métricas Básicas

**Prioridad:** Baja  
**Descripción:** Endpoint con estadísticas de uso.

**Métricas:**
- Total de queries procesadas
- Distribución de intents
- Tasa de error
- Queries por día/hora
- Usuarios únicos

---

## 🏗️ Requisitos No Funcionales

### RNF-01: Performance

- **Latencia:** <3 segundos p95 para respuestas
- **Throughput:** Mínimo 10 queries/segundo
- **Startup time:** <30 segundos

### RNF-02: Disponibilidad

- **Uptime:** 99.5% mensual
- **Recovery time:** <5 minutos en caso de falla
- **Graceful degradation:** Respuesta genérica si LLM falla

### RNF-03: Escalabilidad

- **Usuarios concurrentes:** Hasta 100 usuarios simultáneos
- **Base de conocimiento:** Hasta 50 documentos (500KB)
- **Índice vectorial:** <100MB en memoria

### RNF-04: Seguridad

- **Autenticación:** API protegida (opcional en MVP)
- **Rate limiting:** Protección contra DoS
- **Data sanitization:** Limpieza de inputs
- **Secrets management:** .env para API keys

### RNF-05: Privacidad

- **Anonimización:** Hash de user_id en logs
- **Retención:** Logs conservados por 90 días
- **No almacenar:** Información sensible de clientes
- **Cumplimiento:** Preparado para GDPR-like requirements

### RNF-06: Mantenibilidad

- **Código:** Python 3.11+, typed hints, docstrings
- **Logging:** Structured logging con niveles
- **Testing:** Cobertura mínima 70% (no en MVP)
- **Documentación:** README, API docs, código comentado

### RNF-07: Costo

- **Operación:** <$50/mes usando tier gratuito
- **Groq API:** Free tier (30 req/min)
- **Infrastructure:** Local o cloud básico
- **Almacenamiento:** SQLite (sin costos)

### RNF-08: Observabilidad

- **Logs:** Archivo y stdout
- **Métricas:** Endpoint /metrics
- **Health checks:** Endpoint /health
- **Tracing:** Request ID en logs (futuro)

---

## 🏛️ Arquitectura Técnica

### Stack Tecnológico

**Backend:**
- Python 3.11+
- FastAPI 0.115+ (framework web)
- Uvicorn (ASGI server)

**RAG Components:**
- Sentence Transformers 3.3.1 (embeddings multilingües)
- FAISS 1.13.2 (vector store)
- Groq API 0.11.0 (LLM - Llama 3.3 70B)
- Cross-Encoder ms-marco-MiniLM-L-6-v2 (reranking)

**Data:**
- SQLite3 (logs, analytics)
- JSON (metadata)
- Markdown (documentos fuente)

**Integration:**
- WhatsApp Business Cloud API (webhook directo en FastAPI)

**DevOps:**
- Docker & Docker Compose
- Pydantic Settings (config centralizada)

### Arquitectura de Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                       Usuario (WhatsApp)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp Business API                     │
│                     (Meta Platform)                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (api/main.py)                     │
│  ┌────────────────────────────────────────────────────┐     │
│  │  GET/POST /webhook  (WhatsApp verification + msgs) │     │
│  │  POST /query                                       │     │
│  │  - Recibe: user_id, message, history              │     │
│  │  - Retorna: response, intent, sources, metadata   │     │
│  └──────────────────────┬─────────────────────────────┘     │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              RAG Pipeline (rag/query/pipeline.py)            │
│                                                              │
│  1. Rate Limiting                                            │
│     ├─ Check queries/hour per user                          │
│     └─ Reject if exceeded                                   │
│                                                              │
│  2. Validation (validator.py)                                │
│     ├─ Check message length                                 │
│     ├─ Detect off-topic/abuse                               │
│     └─ Return friendly rejection if invalid                 │
│                                                              │
│  3. Intent Classification (intent.py)                        │
│     ├─ Keyword + heuristic based                            │
│     └─ Return: intent + confidence                          │
│                                                              │
│  4. Retrieval (retriever.py)                                 │
│     ├─ Embed query → FAISS search                           │
│     ├─ Get top-3 chunks (similarity > 0.2)                  │
│     └─ Return: chunks + metadata + scores                   │
│                                                              │
│  5. Response Generation (responder.py)                       │
│     ├─ Build prompt with context + query                    │
│     ├─ Call Groq API (Llama 3.3 70B)                       │
│     └─ Return: response + token count                       │
│                                                              │
│  6. Logging                                                  │
│     └─ Save to SQLite: query_logs table                     │
│                                                              │
└──────────────────┬──────────────────────┬───────────────────┘
                   │                      │
                   ▼                      ▼
        ┌──────────────────┐   ┌──────────────────────┐
        │  FAISS Index     │   │  SQLite Database     │
        │                  │   │                      │
        │  - Embeddings    │   │  - query_logs        │
        │  - Metadata      │   │  - analytics         │
        │                  │   │                      │
        └──────────────────┘   └──────────────────────┘
                   ▲
                   │
        ┌──────────────────────┐
        │  Knowledge Base      │
        │  (Markdown docs)     │
        │                      │
        │  - company.md        │
        │  - faq.md            │
        │  - plans.md          │
        │  - policies.md       │
        │  - services.md       │
        │  - sla.md            │
        └──────────────────────┘

External APIs:
┌──────────────────────┐
│   Groq Cloud API     │
│   (LLM Inference)    │
│                      │
│   Model:             │
│   llama-3.3-70b      │
└──────────────────────┘
```

### Flujo de Datos

1. **Ingesta (build_index.py):**
   ```
   Markdown docs → Chunker → Embeddings → FAISS Index + Metadata JSON
   ```

2. **Query Processing:**
   ```
   WhatsApp msg → FastAPI /webhook → Pipeline → Validator → Intent
                                          ↓
   Response ← LLM ← Prompt Builder ← Retriever ← Query Embedding
   ```

3. **Logging:**
   ```
   Pipeline → SQLite (user_id, query, intent, response, timestamp, etc.)
   ```

### Estructura de Directorios

```
knowligo/
├── api/                    # FastAPI application
│   ├── main.py            # API endpoints
│   ├── models.py          # Pydantic schemas
│   └── __init__.py
│
├── rag/                    # RAG core logic
│   ├── ingest/
│   │   ├── build_index.py # Vectoriza documentos
│   │   └── chunker.py     # Divide docs en chunks
│   │
│   ├── query/
│   │   ├── pipeline.py    # Orquestador principal
│   │   ├── validator.py   # Filtro de queries
│   │   ├── intent.py      # Clasificador de intención
│   │   ├── retriever.py   # Búsqueda vectorial
│   │   └── responder.py   # Generación LLM
│   │
│   └── store/             # Vector store
│       ├── faiss.index    # Índice FAISS
│       └── metadata.json  # Metadata chunks
│
├── database/
│   ├── schema/schema.sql  # Schema DB
│   ├── seeds/seed.sql     # Datos iniciales
│   └── sqlite/            # SQLite files
│
├── knowledge/             # Docs para vectorizar
│   └── documents/
│       ├── company.md
│       ├── faq.md
│       ├── plans.md
│       ├── policies.md
│       ├── services.md
│       └── sla.md
│
├── scripts/
│   ├── start.ps1          # Script inicio
│   ├── test_api.py        # Tests API
│   └── utils/
│       └── init_db.py     # Inicializa DB
│
├── tests/                 # Tests con pytest
│   ├── test_health.py
│   ├── test_query.py
│   ├── test_webhook.py
│   └── test_errors.py
│
├── docker-compose.yml     # Orquestación servicios
├── Dockerfile             # Imagen API
├── requirements.txt       # Dependencias Python
├── .env                   # Variables entorno
└── README.md             # Documentación
```

---

## 🌊 Flujos de Usuario

### Flujo Principal: Consulta Exitosa

```
1. Usuario envía mensaje "¿Qué planes tienen?" por WhatsApp
   ↓
2. WhatsApp Business API recibe mensaje
   ↓
3. Webhook de FastAPI recibe el POST en /webhook
   ↓
4. FastAPI extrae:
   - user_id: +549xxxxxxxxx
   - message: "¿Qué planes tienen?"
   ↓
5. RAGPipeline.process_query()
   ↓
6. Rate Limiter verifica: Usuario tiene 3/15 queries esta hora ✓
   ↓
7. Validator verifica:
   - Longitud OK (19 chars < 150)
   - No insultos
   - Topic relevante ✓
   ↓
8. Intent Classifier:
   - Detecta keywords: "planes"
   - Intent: "planes" (confidence: 0.95)
   ↓
9. Retriever:
    - Genera embedding de query
    - Busca en FAISS
    - Cross-Encoder reranking
    - Recupera top-3 chunks:
      1. plans.md - "Planes de servicio" (score: 0.78)
      2. plans.md - "Plan Básico" (score: 0.65)
      3. plans.md - "Plan Profesional" (score: 0.63)
   ↓
10. Responder:
    - Construye prompt con contexto
    - Llama a Groq API (Llama 3.3 70B)
    - Recibe respuesta generada
   ↓
11. Response:
    "KnowLigo ofrece tres planes de servicio:
     
     • Plan Básico ($199/mes): Soporte en horario laboral,
       incidencias baja/media, mantenimiento trimestral.
     
     • Plan Profesional ($499/mes): Incluye incidencias de alta
       prioridad y mantenimiento mensual.
     
     • Plan Empresarial: Personalizado según necesidades.
     
     ¿Querés más detalles de algún plan?"
   ↓
12. Pipeline registra en SQLite:
    - query, intent, response, timestamp, tokens_used
   ↓
13. FastAPI retorna JSON:
    {
      "success": true,
      "response": "...",
      "intent": "planes",
      "sources": [{"file": "plans.md", ...}]
    }
   ↓
14. FastAPI envía respuesta a WhatsApp vía Cloud API
   ↓
15. Usuario recibe mensaje
```

### Flujo Alternativo: Query Inválida

```
1. Usuario envía "me das tu numero de celular bb?"
   ↓
2-4. [Mismo flujo hasta Validator]
   ↓
7. Validator detecta:
   - Contenido inapropiado
   - Off-topic (no es consulta IT)
   ↓
8. Retorna mensaje:
   "Solo puedo ayudarte con consultas sobre servicios IT,
    planes, mantenimiento y tickets de KnowLigo."
   ↓
9. [No se ejecuta Retrieval ni LLM]
   ↓
10. Log registro: intent="rejected", success=false
   ↓
11. Usuario recibe mensaje de rechazo
```

### Flujo Alternativo: Rate Limit Excedido

```
1. Usuario envía query #16 en la misma hora
   ↓
2-3. [Mismo flujo inicial]
   ↓
4. Rate Limiter verifica: 15/15 queries ✗
   ↓
5. Retorna:
   "Has alcanzado el límite de 15 consultas por hora.
    Por favor, intenta nuevamente en 45 minutos."
   ↓
8. [No procesa query]
   ↓
9. Log: error="rate_limit_exceeded"
   ↓
10. Usuario recibe mensaje de límite
```

---

## 📊 Objetivos de Diseño

### Objetivos Primarios

| Objetivo | Criterio |
|----------|----------|
| **Automatización** | Mayoría de consultas resueltas sin escalamiento humano |
| **Tiempo de Respuesta** | Respuestas en segundos (dependiente de Groq API) |
| **Precisión** | Respuestas basadas únicamente en la base de conocimiento |
| **Disponibilidad** | Health checks automatizados |
| **Costo** | $0 (free tier de Groq + infraestructura local) |

### Objetivos de Calidad RAG

| Objetivo | Estrategia |
|----------|------------|
| **Retrieval Precision** | Hybrid search (FAISS + BM25) con Cross-Encoder reranking |
| **Baja alucinación** | System prompt estricto + contexto acotado a chunks relevantes |
| **Relevancia de contexto** | RRF fusion + reranking reduce ruido en chunks |
| **Coherencia** | Temperature 0.5 + max_tokens controlados |

---

## �️ Funcionalidades Implementadas

### Completado

- [x] Sistema RAG funcional (FAISS + BM25 + RRF + Cross-Encoder reranking)
- [x] Integración WhatsApp vía webhook FastAPI directo
- [x] 10 intents con LLM Router (Groq)
- [x] Rate limiting por usuario
- [x] Logging estructurado
- [x] API REST con FastAPI (/webhook, /query, /health, /stats)
- [x] Docker Compose deployment
- [x] Documentación completa (ADRs, diagramas Mermaid, PRD, INDEX)
- [x] Tests unitarios con pytest (145 tests)
- [x] Embeddings multilingües + Cross-Encoder reranking
- [x] Caché semántico + Protección prompt injection
- [x] Configuración centralizada (Pydantic Settings)
- [x] Historial conversacional multi-turno
- [x] Botones interactivos en WhatsApp (Interactive Lists + Reply Buttons)
- [x] Flujos multi-turn: registro, tickets, contratos, pagos
- [x] HyDE-lite query rewriting
- [x] Detección de gibberish y saludos repetidos
- [x] Menú adaptativo según estado de registro

### Pendiente

- [ ] Soporte para multimedia (imágenes, PDFs)
- [ ] Dashboard de métricas (Grafana/Streamlit)
- [ ] Soporte multiidioma (ES/EN/PT)
- [ ] Monitoreo con Prometheus/Grafana
- [ ] Frontend web para administración

---

## 🚨 Riesgos y Mitigaciones

### Riesgos Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Groq API down/rate limited** | Media | Alto | Implementar fallback a OpenAI/Anthropic; caching de respuestas comunes |
| **FAISS index corruption** | Baja | Alto | Backups diarios; re-indexing automático |
| **WhatsApp API cambios** | Media | Alto | Monitorear changelog Meta; abstraer integración |
| **Alucinaciones del LLM** | Alta | Medio | Validación de respuestas; disclaimers; grounding en contexto |
| **SQLite locks bajo carga** | Media | Medio | Migrar a PostgreSQL; write buffer |
| **Latencia >3s** | Media | Medio | Optimizar embeddings; parallel retrieval; caching |

### Riesgos de Negocio

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Baja adopción usuarios** | Media | Alto | Campaña de comunicación; onboarding claro; valor demostrable |
| **Costos Groq exceden free tier** | Baja | Medio | Monitoreo de usage; alerts; plan de migración |
| **Información desactualizada** | Alta | Medio | Proceso de actualización docs; versionado |
| **Privacidad/compliance issues** | Baja | Alto | Auditoría legal; anonimización; términos claros |

### Riesgos de Producto

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **UX confusa en WhatsApp** | Media | Medio | Testing con usuarios reales; iteración rápida |
| **Expectativas no cumplidas** | Alta | Alto | Comunicación clara de capacidades; disclaimers |
| **Abuse/spam del bot** | Media | Medio | Rate limiting robusto; blacklist; captcha |
| **Scope creep** | Alta | Medio | PRD claro; priorización estricta; MVP focus |

---

## 🔐 Consideraciones de Seguridad y Privacidad

### Seguridad

1. **Autenticación API:**
   - Considerar API keys para /query endpoint (post-MVP)
   - HTTPS obligatorio en producción

2. **Input Sanitization:**
   - Validación estricta de largos
   - Escape de caracteres especiales
   - SQL injection prevention (parametrized queries)

3. **Rate Limiting:**
   - Por user_id (actual)
   - Por IP (futuro)
   - Blacklist automática de abusadores

4. **Secrets Management:**
   - .env para desarrollo
   - Secrets manager en producción (AWS Secrets, Vault)
   - Never commit .env al repo

### Privacidad

1. **Data Minimization:**
   - Solo almacenar datos necesarios
   - No guardar información sensible de clientes

2. **Anonimización:**
   - Hash SHA256 de user_id en logs
   - No almacenar contenido de mensajes íntegro (solo para debugging limitado)

3. **Retención:**
   - Logs: 90 días
   - Analytics agregados: indefinido
   - Derecho al olvido: procedimiento manual

4. **Cumplimiento:**
   - Preparado para GDPR/LGPD
   - Términos de servicio claros
   - Opt-out disponible

---

## 🧪 Plan de Testing (Post-MVP)

### Unit Tests

- Validator: detección off-topic, límites
- Intent Classifier: cobertura de keywords
- Retriever: precisión de búsqueda
- Responder: parsing de respuestas LLM

**Objetivo:** >70% cobertura

### Integration Tests

- Pipeline end-to-end
- API endpoints
- Rate limiting
- Database operations

### Performance Tests

- Load testing: 50 queries/segundo
- Stress testing: 200 usuarios concurrentes
- Latency: p50, p95, p99

### User Acceptance Testing (UAT)

- Beta con 20 clientes reales
- Feedback cualitativo
- Medición de satisfacción

---

## 📚 Documentación

### Documentación Técnica

- [x] **README.md** - Guía de inicio rápido
- [x] **PRD.md** (este documento)
- [ ] **API.md** - Especificación OpenAPI
- [ ] **ARCHITECTURE.md** - Detalles de arquitectura
- [ ] **DEPLOYMENT.md** - Guía de deployment
- [ ] **CONTRIBUTING.md** - Guía de contribución

### Documentación de Usuario

- [ ] **USER_GUIDE.md** - Manual para clientes
- [ ] **FAQ_BOT.md** - FAQs sobre el bot
- [ ] **ONBOARDING.md** - Guía de primeros pasos

### Documentación de Código

- Docstrings en todas las funciones/clases
- Type hints (Python)
- Comentarios inline para lógica compleja

---

## 🤝 Stakeholders y Responsabilidades

| Rol | Responsable | Responsabilidades |
|-----|-------------|-------------------|
| **Product Owner** | TBD | Visión, roadmap, priorización |
| **Tech Lead** | TBD | Arquitectura, decisiones técnicas |
| **Backend Developer** | TBD | Implementación API, RAG pipeline |
| **ML Engineer** | TBD | Optimización embeddings, LLM prompts |
| **DevOps Engineer** | TBD | Deployment, monitoring, scaling |
| **QA Engineer** | TBD | Testing, calidad |
| **Content Manager** | TBD | Actualización base conocimiento |

---

## 📞 Contacto y Soporte

**Proyecto:** KnowLigo RAG Chatbot  
**Repositorio:** https://github.com/titesen/knowligo  
**Documentación:** [README.md](README.md)  
**Issues:** GitHub Issues  
**Discusiones:** GitHub Discussions

---

## 📄 Apéndices

### A. Glosario

- **RAG:** Retrieval-Augmented Generation - técnica que combina búsqueda de información con generación de texto
- **FAISS:** Facebook AI Similarity Search - librería para búsqueda vectorial eficiente
- **Embedding:** Representación vectorial de texto en espacio semántico
- **Intent:** Intención clasificada de una query de usuario
- **Chunk:** Fragmento de documento vectorizado
- **LLM:** Large Language Model - modelo de lenguaje grande
- **SLA:** Service Level Agreement - acuerdo de nivel de servicio
- **PyME:** Pequeña y Mediana Empresa
- **n8n:** Plataforma de automatización de workflows (ya no utilizada en la implementación actual)
- **Groq:** Proveedor de inferencia de LLMs de alta velocidad

### B. Referencias

- [Sentence Transformers Documentation](https://www.sbert.net/)
- [FAISS Wiki](https://github.com/facebookresearch/faiss/wiki)
- [Groq API Docs](https://console.groq.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)

### C. Historial del PRD

| Versión | Cambios | Autor |
|---------|---------|-------|
| 1.0 | Documento inicial | Facundo |
