# 🚀 Quick Start - KnowLigo WhatsApp Demo

Script rápido para levantar todo y hacer demo.

## Pre-requisitos

- [x] Python 3.11+ instalado
- [x] Docker Desktop instalado y corriendo
- [x] Cuenta en Groq (API key)
- [x] Cuenta en Meta for Developers (WhatsApp)
- [x] Ngrok instalado

## Setup Rápido (15 minutos)

### 1️⃣ Clonar y preparar entorno

```powershell
git clone https://github.com/tu-usuario/knowligo.git
cd knowligo

# Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### 2️⃣ Configurar credenciales

Edita `.env` con tus credenciales:

```bash
# Groq API (https://console.groq.com/keys)
GROQ_API_KEY=gsk_tu_key_aqui

# WhatsApp (https://developers.facebook.com)
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_TOKEN=EAAtu_token_aqui
WHATSAPP_VERIFY_TOKEN=knowligo_webhook_verify_token
```

### 3️⃣ Inicializar base de datos y vectorizar

```powershell
# Crear DB
python scripts\utils\init_db.py

# Construir índice FAISS (~1-2 min)
python rag\ingest\build_index.py
```

### 4️⃣ Levantar servicios

```powershell
# Opción A: Con Docker (recomendado)
docker-compose up -d

# Opción B: Sin Docker (desarrollo)
# Terminal 1:
python api\main.py

# Terminal 2:
npx n8n
```

### 5️⃣ Configurar Ngrok

```powershell
# Nueva terminal
ngrok http 5678
```

Copia la URL HTTPS (ej: `https://abc123.ngrok-free.app`)

### 6️⃣ Configurar WhatsApp Webhook

1. Ve a https://developers.facebook.com/apps
2. Tu app → WhatsApp → Configuration → Webhook
3. **Callback URL**: `https://TU-URL-NGROK.ngrok-free.app/webhook/whatsapp-webhook`
4. **Verify token**: `knowligo_webhook_verify_token`
5. Click **"Verify and save"**
6. Suscribirse a **"messages"**

### 7️⃣ Configurar n8n

1. Abre http://localhost:5678 (admin / knowligo2026)
2. Credentials → Add
   - Type: **Header Auth**
   - Name: `WhatsApp Bearer Token`
   - Header: `Authorization`
   - Value: `Bearer TU_WHATSAPP_TOKEN`
3. Workflows → Import → `n8n/workflows/whatsapp-rag-chatbot.json`
4. Configurar credenciales en nodos "Send WhatsApp"
5. Activar workflow (switch ON)

### 8️⃣ Probar

1. Agrega tu número en Meta Developers (API Setup → Add phone number)
2. Envía mensaje al número de prueba:
   ```
   ¿Qué planes de soporte ofrecen?
   ```
3. ¡Deberías recibir respuesta del bot! 🎉

---

## 🎥 Elementos para Demo en Video

### Mostrar en el video:

1. **Arquitectura** (diagrama del README)
2. **Swagger UI** (http://localhost:8000/docs)
   - Ejecutar query manualmente
3. **n8n Workflow** (mostrar nodos)
4. **WhatsApp en vivo**:
   - Enviar: "¿Qué planes ofrecen?"
   - Enviar: "¿Cuál es el SLA para tickets High?"
   - Enviar: "Dame consejos de hacking" (debe rechazar)
5. **Logs en tiempo real** (`docker-compose logs -f`)
6. **Stats endpoint** (http://localhost:8000/stats)

### Queries de ejemplo para demo:

✅ **Válidas**:
- "¿Qué planes de soporte ofrecen?"
- "¿Cuál es el SLA para tickets High?"
- "¿Hacen mantenimiento preventivo?"
- "¿Cuánto cuesta el plan Enterprise?"
- "Necesito ayuda con mi servidor"

❌ **Rechazadas** (fuera de dominio):
- "Dame consejos de hacking"
- "¿Cuál es tu opinión política?"
- "¿Puedes recomendarme un celular?"

---

## 🐛 Troubleshooting

### Webhook no verifica
```powershell
# Verificar que n8n esté corriendo
curl http://localhost:5678

# Ver logs
docker-compose logs -f n8n
```

### No recibo respuestas
```powershell
# Ver logs de API
docker-compose logs -f api

# Ver execuciones en n8n UI
http://localhost:5678 → Executions
```

### API lenta
- Normal: Groq puede tardar 3-5 segundos
- WhatsApp espera hasta 20 segundos

---

## 📊 URLs y Accesos

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| n8n | http://localhost:5678 | admin / knowligo2026 |
| Health | http://localhost:8000/health | - |
| Stats | http://localhost:8000/stats | - |

---

## ✅ Checklist Pre-Demo

```
[ ] .env configurado con credenciales reales
[ ] Base de datos inicializada
[ ] Índice FAISS construido (25 vectores)
[ ] Docker Compose up (API + n8n)
[ ] Ngrok corriendo
[ ] Webhook verificado en Meta ✅
[ ] Credenciales configuradas en n8n
[ ] Workflow importado y activado
[ ] Tu número agregado en Meta
[ ] Mensaje de prueba enviado → respuesta recibida ✅
[ ] Cámara/screen recorder listos 🎥
```

---

¡Listo para grabar! 🚀
