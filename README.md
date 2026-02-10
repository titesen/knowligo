# KnowLigo - RAG-Powered IT Support Chatbot

**Proyecto educativo**: Chatbot inteligente de soporte IT para WhatsApp usando RAG (Retrieval-Augmented Generation) con FAISS y Groq LLM.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Descripción

KnowLigo es una empresa ficticia de soporte IT para PyMEs. Este proyecto implementa un chatbot conversacional que:

- ✅ Responde consultas sobre **planes de servicio**, **SLAs**, **mantenimiento** y **tickets**
- ✅ Usa **RAG** (vectorización con FAISS + embeddings) para recuperar información relevante
- ✅ Genera respuestas naturales con **Groq API** (Mixtral-8x7b)
- ✅ Integra con **WhatsApp Business API** vía **n8n**
- ✅ Controla respuestas on-topic, rate limiting y abuse prevention
- ✅ 100% gratuito (usa APIs free tier)

## 🏗️ Arquitectura

```
Usuario (WhatsApp)
    ↓
n8n Workflow (webhook)
    ↓
FastAPI (rag/query/pipeline.py)
    ├── Validator (topic control)
    ├── Intent Classifier
    ├── Retriever (FAISS vector search)
    └── Responder (Groq LLM)
    ↓
Respuesta → WhatsApp
```

## 🚀 Quick Start

### 1. Requisitos previos

- Python 3.11+
- Docker & Docker Compose
- Cuenta en [Groq](https://console.groq.com) (gratis)
- Cuenta en [Meta for Developers](https://developers.facebook.com) (para WhatsApp)

### 2. Instalación

```powershell
# Clonar repositorio
git clone https://github.com/tu-usuario/knowligo.git
cd knowligo

# Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
Copy-Item .env.example .env
# Edita .env y agrega tu GROQ_API_KEY
```

### 3. Inicializar base de datos y vectorizar documentos

```powershell
# Crear base de datos SQLite
python scripts\utils\init_db.py

# Vectorizar documentos (crear índice FAISS)
python rag\ingest\build_index.py
```

### 4. Ejecutar API localmente

```powershell
# Iniciar API FastAPI
python api\main.py

# En otra terminal, probar
python scripts\test_api.py
```

Abre http://localhost:8000/docs para ver la documentación interactiva.

### 5. Desplegar con Docker

```powershell
# Construir y levantar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Acceder a n8n
# http://localhost:5678 (user: admin, pass: knowligo2026)
```

## 📁 Estructura del Proyecto

```
knowligo/
├── api/                    # FastAPI application
│   ├── main.py            # Endpoints REST
│   └── models.py          # Pydantic schemas
├── rag/
│   ├── ingest/            # Pipeline de vectorización
│   │   ├── build_index.py # Crear índice FAISS
│   │   └── chunker.py     # Procesamiento de documentos
│   ├── query/             # Pipeline de consultas
│   │   ├── pipeline.py    # Orquestador principal
│   │   ├── validator.py   # Control de dominio
│   │   ├── retriever.py   # Búsqueda vectorial FAISS
│   │   ├── responder.py   # Generación LLM (Groq)
│   │   └── intent.py      # Clasificación de intención
│   └── store/             # Índices y chunks
│       ├── faiss.index    # Índice vectorial
│       ├── chunks.pkl     # Chunks procesados
│       └── metadata.json  # Metadata del índice
├── knowledge/             # Base de conocimiento
│   ├── documents/         # Documentos markdown
│   └── metadata.json      # Topics permitidos/prohibidos
├── database/
│   ├── schema/            # Schema SQL
│   ├── seeds/             # Datos de prueba
│   └── sqlite/            # Base de datos
├── n8n/
│   ├── workflows/         # WhatsApp workflow
│   └── credentials/       # Config de credenciales
├── scripts/
│   ├── test_api.py        # Tests automatizados
│   └── utils/             # Utilidades
├── docker-compose.yml     # Orquestación de servicios
├── Dockerfile             # Imagen de la API
└── requirements.txt       # Dependencias Python
```

## 🔧 Configuración de WhatsApp

### Opción A: WhatsApp Cloud API (Recomendado - Gratis)

1. **Crear app en Meta for Developers**:
   - https://developers.facebook.com/apps
   - Agrega producto **WhatsApp**
   - Obtén `Phone Number ID` y `Access Token`

2. **Configurar Webhook**:
   - URL: `https://tu-dominio.com/webhook/whatsapp-webhook`
   - Verify Token: `knowligo_webhook_verify_token`
   - Fields: `messages`

3. **Para desarrollo local, usa ngrok**:
   ```bash
   ngrok http 5678
   ```
   Usa la URL HTTPS como Callback URL en Meta.

4. **Importar workflow en n8n**:
   - Abre http://localhost:5678
   - Importa `n8n/workflows/whatsapp-rag-chatbot.json`
   - Configura credenciales (ver `n8n/credentials/README.md`)
   - Activa el workflow

### Opción B: Solo API (sin WhatsApp)

Usa la API directamente:

```powershell
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{"user_id":"test","message":"¿Qué planes ofrecen?"}'
```

## 🧪 Testing

### Test automático del pipeline

```powershell
python scripts\test_api.py
```

Prueba queries de ejemplo:
- "¿Qué planes de soporte ofrecen?" → Intent: planes
- "¿Cuál es el SLA para tickets High?" → Intent: sla
- "Dame consejos de hacking" → Rechazado (fuera de dominio)

### Probar componentes individuales

```powershell
# Validator
python rag\query\validator.py

# Retriever
python rag\query\retriever.py

# Intent Classifier
python rag\query\intent.py

# Responder (requiere GROQ_API_KEY en .env)
python rag\query\responder.py

# Pipeline completo
python rag\query\pipeline.py
```

## 📊 Endpoints de la API

### `POST /query`
Procesa una consulta del usuario.

**Request:**
```json
{
  "user_id": "+5491112345678",
  "message": "¿Qué planes ofrecen?"
}
```

**Response:**
```json
{
  "success": true,
  "response": "KnowLigo ofrece tres planes: Basic ($199/mes), Professional ($499/mes) y Enterprise (personalizado)...",
  "intent": "planes",
  "intent_confidence": 0.95,
  "sources": [
    {"file": "plans.md", "section": "Planes", "score": 0.23}
  ],
  "tokens_used": 142,
  "processing_time": 1.25
}
```

### `GET /health`
Verifica el estado del sistema.

### `GET /stats`
Estadísticas de uso (queries procesadas, intents, etc.).

## 🛡️ Controles y Limitaciones

### Topic Validation
- Solo responde consultas sobre: **soporte IT, planes, SLA, tickets, mantenimiento**
- Rechaza: hacking, política, opiniones personales, topics no relacionados

### Rate Limiting
- Máximo **10 queries por usuario por hora**
- Configurable en `.env` (`MAX_QUERIES_PER_HOUR`)

### Response Control
- Máximo **120 palabras** por respuesta
- Tono **profesional, conciso, serio**
- Solo usa información de la base de conocimiento

## 🔐 Variables de Entorno

Edita `.env` con tus credenciales:

```bash
# Groq API (https://console.groq.com/keys)
GROQ_API_KEY=gsk_xxxxxxxxxxxxx

# WhatsApp Business Cloud API
WHATSAPP_TOKEN=EAAxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=knowligo_webhook_verify_token

# Configuración
MAX_MESSAGE_LENGTH=120
MAX_QUERIES_PER_HOUR=10
LLM_MODEL=mixtral-8x7b-32768
```

## 📈 Roadmap

- [x] Pipeline RAG con FAISS
- [x] Integración Groq LLM
- [x] API REST con FastAPI
- [x] Validación de dominio y rate limiting
- [x] Workflow n8n para WhatsApp
- [x] Docker compose
- [ ] Tests unitarios con pytest
- [ ] Monitoreo con Prometheus/Grafana
- [ ] Frontend web para administración
- [ ] Soporte para múltiples idiomas

## 🤝 Contribuir

Este es un proyecto educativo. Pull requests son bienvenidos.

## 📄 Licencia

MIT License - Proyecto educativo de código abierto

## 👤 Autor

**Facundo** - Proyecto educacional para demostración en LinkedIn

## 🙏 Agradecimientos

- [Groq](https://groq.com) por su LLM API gratuita
- [n8n](https://n8n.io) por la plataforma de automatización
- [Meta](https://developers.facebook.com) por WhatsApp Business API
- [Sentence Transformers](https://www.sbert.net/) por los embeddings
- [FAISS](https://github.com/facebookresearch/faiss) por el vector search

---

⭐ Si este proyecto te fue útil, dale una star en GitHub!
