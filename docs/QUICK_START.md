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
WHATSAPP_VERIFY_TOKEN=knowligo_webhook_2026
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
python api\main.py
```

### 5️⃣ Configurar Ngrok

```powershell
# Ngrok apunta a la API FastAPI (puerto 8000)
ngrok http 8000
```

Copia la URL HTTPS (ej: `https://abc123.ngrok-free.app`)

### 6️⃣ Configurar WhatsApp Webhook

1. Ve a https://developers.facebook.com/apps
2. Tu app → WhatsApp → Configuration → Webhook
3. **Callback URL**: `https://TU-URL-NGROK.ngrok-free.app/webhook`
4. **Verify token**: `knowligo_webhook_2026`
5. Click **"Verify and save"**
6. Suscribirse a **"messages"**

### 7️⃣ Probar

1. Agrega tu número en Meta Developers (API Setup → Add phone number)
2. Envía mensaje al número de prueba:
   ```
   ¿Qué planes de soporte ofrecen?
   ```
3. ¡Deberías recibir respuesta del bot! 🎉

---

### Queries de ejemplo:

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
# Verificar que la API esté corriendo
curl http://localhost:8000/health

# Ver logs
docker-compose logs -f api
```

### No recibo respuestas
```powershell
# Ver logs de API
docker-compose logs -f api
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
| Health | http://localhost:8000/health | - |
| Stats | http://localhost:8000/stats | - |

---

## ✅ Checklist Pre-Demo

```
[ ] .env configurado con credenciales reales
[ ] Base de datos inicializada
[ ] Índice FAISS construido (122 vectores)
[ ] Docker Compose up (API)
[ ] Ngrok corriendo
[ ] Webhook verificado en Meta ✅
[ ] Tu número agregado en Meta
[ ] Mensaje de prueba enviado → respuesta recibida ✅
```

---

¡Listo para usar! 🚀
