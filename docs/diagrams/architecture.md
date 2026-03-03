# Diagramas de Arquitectura — KnowLigo

Todos los diagramas usan [Mermaid.js](https://mermaid.js.org/) y se renderizan automáticamente en GitHub, VS Code y cualquier visor Markdown moderno.

---

## 1. Arquitectura General (C4 — Nivel Contexto)

```mermaid
graph TB
    User["👤 Usuario<br>(WhatsApp)"]
    Meta["☁️ Meta<br>WhatsApp Cloud API"]
    API["🖥️ KnowLigo API<br>FastAPI + Uvicorn"]
    Groq["🤖 Groq Cloud<br>Llama 3.3 70B"]

    User -->|Mensaje texto/interactivo| Meta
    Meta -->|Webhook POST /webhook| API
    API -->|Chat Completions API| Groq
    Groq -->|Respuesta generada| API
    API -->|POST /messages| Meta
    Meta -->|Respuesta| User

    style API fill:#2196F3,color:#fff
    style Groq fill:#FF9800,color:#fff
    style Meta fill:#25D366,color:#fff
```

---

## 2. Arquitectura Interna (C4 — Nivel Contenedores)

```mermaid
graph TB
    subgraph "FastAPI Application"
        direction TB
        MW["Middleware<br>CORS + Error Handlers"]
        EP["Endpoints<br>/webhook · /query · /health · /stats"]
    end

    subgraph "Agent Layer"
        direction TB
        ORC["AgentOrchestrator<br>orchestrator.py"]
        RTR["IntentRouter<br>router.py (LLM)"]
        HND["Handlers<br>handlers.py"]
        MSG["Messages<br>messages.py"]
        CNV["ConversationManager<br>conversation.py"]
        DBS["DBService<br>db_service.py"]
    end

    subgraph "RAG Layer"
        direction TB
        PIP["RAGPipeline<br>pipeline.py"]
        VAL["QueryValidator<br>validator.py"]
        RET["HybridRetriever<br>FAISS + BM25 + RRF"]
        RRK["CrossEncoderReranker<br>reranker.py"]
        CAC["SemanticCache<br>cache.py"]
        RSP["GroqResponder<br>responder.py"]
    end

    subgraph "Data Stores"
        direction TB
        DB[("SQLite<br>knowligo.db")]
        IDX[("FAISS Index<br>faiss.index")]
        KNW["📄 Knowledge Base<br>Markdown docs"]
    end

    EP --> ORC
    ORC --> RTR
    ORC --> HND
    HND --> MSG
    ORC --> CNV
    ORC --> DBS
    ORC --> PIP
    HND --> DBS
    CNV --> DBS
    DBS --> DB
    PIP --> VAL
    PIP --> CAC
    PIP --> RET
    PIP --> RRK
    PIP --> RSP
    RET --> IDX
    RSP -.->|Groq API| Groq["🤖 Groq"]

    style ORC fill:#2196F3,color:#fff
    style PIP fill:#4CAF50,color:#fff
    style DB fill:#FF9800,color:#fff
    style IDX fill:#FF9800,color:#fff
```

---

## 3. Flujo de Procesamiento de Mensajes

```mermaid
flowchart TD
    A["📩 Mensaje WhatsApp"] --> B{Tipo texto o\ninteractive?}
    B -->|Otro| B1["Responder: tipo no soportado"]
    B -->|Texto| C{Duplicado?}
    B -->|Interactive| B2["Extraer list_reply.id\no button_reply.id"]
    B2 --> C
    C -->|Sí| C1["Ignorar (dedup 5min)"]
    C -->|No| D["Normalizar teléfono"]
    D --> E["Buscar cliente por phone"]
    E --> F{Flujo activo?}
    F -->|Sí| G["Continuar handler<br>(registro/ticket/contrato)"]
    F -->|No| H{¿Cancelar?}
    H -->|Sí| H1["Resetear a IDLE"]
    H -->|No| I{¿Casual/Menú/Gibberish?}
    I -->|Sí| I1["Respuesta directa<br>(sin LLM)"]
    I -->|No| J["LLM Router<br>clasificar intención"]
    J --> K{Intent}
    K -->|SALUDO| K1["Saludo personalizado"]
    K -->|CONSULTA_RAG| K2["Pipeline RAG"]
    K -->|VER_TICKETS| K3["Mostrar tickets"]
    K -->|CREAR_TICKET| K4["Iniciar flujo ticket"]
    K -->|VER_PLANES| K5["Mostrar planes"]
    K -->|CONTRATAR_PLAN| K6["Iniciar flujo contrato"]
    K -->|CONSULTA_CUENTA| K7["Info de cuenta"]
    K -->|DESPEDIDA| K8["Despedida + menú"]
    K -->|FUERA_DE_TEMA| K9["Rechazar cortésmente"]
    G --> L["Log interacción"]
    I1 --> L
    K1 --> L
    K2 --> L
    K3 --> L
    K4 --> L
    K5 --> L
    K6 --> L
    K7 --> L
    K8 --> L
    K9 --> L
    L --> M["📤 Enviar por WhatsApp"]
```

---

## 4. Pipeline RAG (Detalle)

```mermaid
flowchart LR
    Q["Query del usuario"] --> RL{Rate limit<br>OK?}
    RL -->|No| RL1["429: Límite alcanzado"]
    RL -->|Sí| CC{Cache hit?<br>similitud ≥ 0.92}
    CC -->|Sí| CC1["Respuesta cacheada"]
    CC -->|No| VL["Validar dominio<br>+ prompt injection"]
    VL -->|Rechazada| VL1["400: Fuera de tema"]
    VL -->|OK| HY["HyDE Query Rewrite"]
    HY --> RT["Hybrid Retrieval<br>FAISS + BM25"]
    RT --> RRF["RRF Fusion<br>top-15 candidatos"]
    RRF --> RR["Cross-Encoder<br>Reranking → top-5"]
    RR --> LLM["Groq LLM<br>Generar respuesta"]
    LLM --> SC["Guardar en cache"]
    SC --> LOG["Log en query_logs"]
    LOG --> R["✅ Respuesta final"]
```

---

## 5. Diagrama Entidad-Relación (ERD)

```mermaid
erDiagram
    plans ||--o{ contracts : "tiene"
    clients ||--o{ contracts : "contrata"
    clients ||--o{ tickets : "abre"
    contracts ||--o{ payments : "recibe"

    plans {
        int id PK
        text name UK
        text description
        real price_ars
        int max_tickets_month
        text support_hours
        int includes_onsite
        int includes_backup
        int includes_drp
        text maintenance_frequency
    }

    clients {
        int id PK
        text name
        text industry
        text contact_name
        text contact_email
        text phone UK
        int employee_count
    }

    contracts {
        int id PK
        int client_id FK
        int plan_id FK
        text start_date
        text end_date
        text status
        real monthly_amount
    }

    tickets {
        int id PK
        int client_id FK
        text priority
        text status
        text category
        text subject
        text description
    }

    payments {
        int id PK
        int contract_id FK
        real amount
        text status
        text payment_method
        text reference_code
    }

    query_logs {
        int id PK
        text user_id
        text query
        text intent
        int success
        int tokens_used
        real processing_time
    }

    conversations {
        int id PK
        text phone UK
        text state
        text context
    }
```

---

## 6. Máquina de Estados (Conversación)

```mermaid
stateDiagram-v2
    [*] --> IDLE

    IDLE --> REG_AWAIT_NAME : "registrar" (no registrado)
    REG_AWAIT_NAME --> REG_AWAIT_COMPANY : nombre recibido
    REG_AWAIT_COMPANY --> REG_AWAIT_EMAIL : empresa recibida
    REG_AWAIT_EMAIL --> IDLE : email válido → cliente creado

    IDLE --> TICKET_AWAIT_SUBJECT : CREAR_TICKET (registrado)
    TICKET_AWAIT_SUBJECT --> TICKET_AWAIT_DESCRIPTION : asunto recibido
    TICKET_AWAIT_DESCRIPTION --> TICKET_AWAIT_PRIORITY : descripción recibida
    TICKET_AWAIT_PRIORITY --> IDLE : prioridad → ticket creado

    IDLE --> CONTRACT_AWAIT_PLAN : CONTRATAR_PLAN (registrado)
    CONTRACT_AWAIT_PLAN --> CONTRACT_AWAIT_CONFIRM : plan seleccionado
    CONTRACT_AWAIT_CONFIRM --> CONTRACT_AWAIT_PAYMENT : "sí" confirmado
    CONTRACT_AWAIT_PAYMENT --> IDLE : método pago → contrato creado

    REG_AWAIT_NAME --> IDLE : "cancelar"
    REG_AWAIT_COMPANY --> IDLE : "cancelar"
    REG_AWAIT_EMAIL --> IDLE : "cancelar"
    TICKET_AWAIT_SUBJECT --> IDLE : "cancelar"
    TICKET_AWAIT_DESCRIPTION --> IDLE : "cancelar"
    TICKET_AWAIT_PRIORITY --> IDLE : "cancelar"
    CONTRACT_AWAIT_PLAN --> IDLE : "cancelar"
    CONTRACT_AWAIT_CONFIRM --> IDLE : "cancelar"
    CONTRACT_AWAIT_PAYMENT --> IDLE : "cancelar"
```
