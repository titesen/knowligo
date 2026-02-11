# 📱 Guía Completa de Configuración de WhatsApp para KnowLigo

## Paso 1: Obtener Credenciales de Meta for Developers

### 1.1 Crear App en Meta

1. Ve a https://developers.facebook.com/apps
2. Click **"Create App"** (Crear aplicación)
3. Tipo de aplicación: **Business**
4. Nombre de la app: `KnowLigo Chatbot` (o el que prefieras)
5. Email de contacto: tu email
6. Click **"Create App"**

### 1.2 Agregar Producto WhatsApp

1. En el dashboard de tu app, busca **"WhatsApp"**
2. Click **"Set Up"** (Configurar)
3. Esto te llevará al panel de WhatsApp Business API

### 1.3 Obtener Phone Number ID

1. En el panel de WhatsApp, sección **"API Setup"**
2. Verás un **número de prueba** (ej: +1 555-0100)
3. Debajo dice **"Phone number ID"**: Copia este ID
   - Ejemplo: `123456789012345`
4. Guárdalo para el archivo `.env`

### 1.4 Obtener Access Token

1. En la misma sección "API Setup"
2. Busca **"Temporary access token"**
3. Click **"Copy"** para copiar el token
   - Ejemplo: `EAABsbCS1iHgBO7ZA9rF...` (muy largo)
4. **IMPORTANTE**: Este token expira en 24 horas

#### Crear Token Permanente (Recomendado)

1. En el menú lateral, ve a **"Business Settings"**
2. Click **"System Users"** (Usuarios del sistema)
3. Click **"Add"** → Nombre: `KnowLigo Bot`
4. Rol: **Admin**
5. Click en el usuario creado → **"Add Assets"**
6. Selecciona tu app → Permisos: **Full control**
7. Click **"Generate New Token"**
   - Selecciona tu app
   - Permisos: `whatsapp_business_messaging`, `whatsapp_business_management`
   - Expiration: **Never** (Nunca)
8. Copia el token y guárdalo en lugar seguro

### 1.5 Actualizar archivo .env

Edita `D:\dev\learning\knowligo\.env`:

```bash
# WhatsApp Business Cloud API
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_VERIFY_TOKEN=knowligo_webhook_verify_token
```

---

## Paso 2: Configurar Ngrok (para desarrollo local)

### 2.1 Instalar Ngrok

1. Descarga desde https://ngrok.com/download
2. Extrae el archivo
3. (Opcional) Regístrate en ngrok.com para auth token

### 2.2 Ejecutar Ngrok

```powershell
# En una terminal separada
ngrok http 5678
```

Verás algo como:

```
Forwarding    https://abcd-1234-5678.ngrok-free.app -> http://localhost:5678
```

**Copia la URL HTTPS** (ej: `https://abcd-1234-5678.ngrok-free.app`)

> **Nota**: Esta URL cambia cada vez que reinicias ngrok. Para URL fija, usa cuenta Pro de ngrok.

---

## Paso 3: Configurar Webhook en Meta

### 3.1 Ir a Configuración de Webhook

1. En el panel de WhatsApp de tu app
2. Sección **"Configuration"** → **"Webhook"**
3. Click **"Edit"** (Editar)

### 3.2 Configurar URL y Token

**Callback URL**:
```
https://TU-URL-DE-NGROK.ngrok-free.app/webhook/whatsapp-webhook
```

Ejemplo:
```
https://abcd-1234-5678.ngrok-free.app/webhook/whatsapp-webhook
```

**Verify token**:
```
knowligo_webhook_verify_token
```
(Debe coincidir exactamente con `WHATSAPP_VERIFY_TOKEN` en `.env`)

### 3.3 Verificar Webhook

1. Click **"Verify and save"**
2. Meta hará un GET request a tu webhook
3. Si todo está bien, verás ✅ **"Webhook verified"**

**Si falla**:
- Verifica que n8n esté corriendo
- Verifica que ngrok esté activo
- Revisa los logs de n8n para ver el error

### 3.4 Suscribirse a Eventos

1. En la misma página de Webhook
2. Sección **"Webhook fields"**
3. Click **"Manage"**
4. Selecciona ✅ **messages** (obligatorio)
5. Click **"Save"**

---

## Paso 4: Levantar Servicios

### 4.1 Iniciar con Docker

```powershell
# En la raíz del proyecto
docker-compose up -d
```

Espera ~30 segundos a que los servicios inicien.

### 4.2 O iniciar solo n8n localmente

```powershell
# Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# En una terminal: Iniciar API
python api\main.py

# En otra terminal: Iniciar n8n (sin Docker)
npx n8n
```

---

## Paso 5: Configurar Credenciales en n8n

### 5.1 Acceder a n8n

1. Abre http://localhost:5678
2. Usuario: `admin`
3. Contraseña: `knowligo2026`

### 5.2 Crear Credencial de WhatsApp

1. Click en tu perfil (esquina superior derecha)
2. **Settings** → **Credentials**
3. Click **"Add Credential"**
4. Busca **"Header Auth"**
5. Configura:
   - **Name**: `WhatsApp Bearer Token`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer TU_WHATSAPP_TOKEN_AQUI`
     - Ejemplo: `Bearer EAABsbCS1iHgBO...`
6. Click **"Save"**

### 5.3 Importar Workflow

1. En n8n, click **"Workflows"** → **"Add Workflow"**
2. Click **"⋮"** (tres puntos) → **"Import from File"**
3. Selecciona: `n8n/workflows/whatsapp-rag-chatbot.json`
4. El workflow se importará automáticamente

### 5.4 Configurar Nodos que Usan Credenciales

1. Busca los nodos **"Send WhatsApp (Success)"** y **"Send WhatsApp (Error)"**
2. En cada uno, sección **"Credential to connect with"**
3. Selecciona **"WhatsApp Bearer Token"** (la que acabas de crear)
4. Click **"Save"** en el workflow (esquina superior derecha)

### 5.5 Activar Workflow

1. En la esquina superior derecha, el switch debe estar en **ON** (azul)
2. Si está en OFF (gris), click para activarlo

---

## Paso 6: Probar el Chatbot

### 6.1 Agregar tu Número a la Lista de Prueba

1. En Meta for Developers, panel de WhatsApp
2. Sección **"API Setup"**
3. **"Phone numbers"** → **"Add phone number"**
4. Ingresa tu número de WhatsApp (con código de país)
   - Ejemplo: `+54 9 11 1234-5678`
5. Recibirás un código por WhatsApp
6. Ingrésalo para verificar

### 6.2 Enviar Mensaje de Prueba

1. Desde tu WhatsApp, envía mensaje al **número de prueba de Meta**
   - Lo encuentras en "API Setup" (ej: +1 555-0100)
2. Escribe: **"¿Qué planes de soporte ofrecen?"**

### 6.3 Verificar Respuesta

Deberías recibir una respuesta como:

```
KnowLigo ofrece tres planes de servicio:

1. Basic ($199/mes): Soporte de lunes a viernes, 9-18h
2. Professional ($499/mes): Soporte 24/7 con SLA garantizado
3. Enterprise (precio personalizado): Soluciones a medida

¿Te gustaría más información sobre algún plan en particular?
```

---

## Paso 7: Debugging (si algo falla)

### 7.1 Ver Logs de n8n

```powershell
# Si usas Docker
docker-compose logs -f n8n

# Si usas npx n8n
# Los logs aparecen en la misma terminal
```

### 7.2 Ver Logs de la API

```powershell
# Si usas Docker
docker-compose logs -f api

# Si usas Python directo
# Los logs aparecen en la misma terminal
```

### 7.3 Verificar Webhook Recibido

1. En Meta for Developers
2. Panel de WhatsApp → **"Webhooks"**
3. Hay un historial de webhooks enviados

### 7.4 Ver Ejecuciones en n8n

1. En n8n UI, click **"Executions"**
2. Verás todas las ejecuciones del workflow
3. Click en una para ver detalles paso a paso

### 7.5 Problemas Comunes

#### ❌ Webhook no verifica

**Causa**: n8n no está corriendo o la URL de ngrok cambió

**Solución**:
1. Verifica que n8n esté activo: http://localhost:5678
2. Reinicia ngrok si la URL cambió
3. Actualiza la URL en Meta for Developers

#### ❌ No recibo respuesta en WhatsApp

**Causa**: Credenciales incorrectas o número no agregado a lista de prueba

**Solución**:
1. Verifica `WHATSAPP_TOKEN` en `.env`
2. Verifica que tu número esté registrado en Meta
3. Revisa logs de n8n (puede mostrar error 403 de WhatsApp API)

#### ❌ La API responde lento

**Causa**: Groq API puede tardar 3-5 segundos

**Solución**: Esto es normal. Meta espera hasta 20 segundos.

#### ❌ Error "Rate limit exceeded"

**Causa**: Más de 10 mensajes en 1 hora del mismo usuario

**Solución**: Espera 1 hora o cambia `MAX_QUERIES_PER_HOUR` en `.env`

---

## Paso 8: Producción (Opcional)

### 8.1 Migrar a Servidor

Para producción, necesitas:

1. **Servidor con IP pública** (AWS EC2, DigitalOcean, etc.)
2. **Dominio** (ej: `api.knowligo.com`)
3. **SSL Certificate** (Let's Encrypt gratis)
4. Configurar webhook en Meta con tu dominio

### 8.2 Token Permanente

Reemplaza el token temporal con el token de System User (Paso 1.4).

### 8.3 Número de WhatsApp Real

1. En Meta for Developers, ve a **"Phone Numbers"**
2. Click **"Add Phone Number"**
3. Sigue el proceso de verificación de Meta
4. Esto requiere una cuenta de **WhatsApp Business** verificada

---

## 📊 Resumen de URLs y Credenciales

| Item | Valor | Dónde se usa |
|------|-------|--------------|
| n8n UI | http://localhost:5678 | Navegador |
| API Docs | http://localhost:8000/docs | Navegador |
| Webhook URL | https://XXX.ngrok-free.app/webhook/whatsapp-webhook | Meta Developers |
| n8n User | `admin` | Login n8n |
| n8n Password | `knowligo2026` | Login n8n |
| Verify Token | `knowligo_webhook_verify_token` | .env + Meta |
| Phone Number ID | (de Meta) | .env |
| Access Token | (de Meta) | .env + n8n credential |

---

## ✅ Checklist Final

```
[ ] Cuenta en Meta for Developers creada
[ ] App de WhatsApp Business creada
[ ] Phone Number ID copiado
[ ] Access Token copiado (temporal o permanente)
[ ] Archivo .env actualizado con credenciales
[ ] Ngrok instalado y corriendo
[ ] URL de ngrok copiada
[ ] Webhook configurado en Meta
[ ] Webhook verificado ✅ en Meta
[ ] Eventos "messages" suscritos
[ ] Docker Compose corriendo (o API + n8n por separado)
[ ] Credencial "WhatsApp Bearer Token" creada en n8n
[ ] Workflow importado en n8n
[ ] Workflow activado (ON)
[ ] Tu número agregado a lista de prueba en Meta
[ ] Mensaje de prueba enviado
[ ] Respuesta recibida ✅
```

---

## 🎥 Listo para Grabar Demo

Una vez que todos los checks estén ✅, puedes grabar tu video mostrando:

1. ✅ Arquitectura del sistema (diagrama)
2. ✅ API funcionando (Swagger UI)
3. ✅ Workflow de n8n (mostrar nodos)
4. ✅ **Demo en vivo**: Enviar mensaje a WhatsApp y recibir respuesta
5. ✅ Mostrar logs/analytics en tiempo real
6. ✅ Código del RAG pipeline (explicar componentes)

---

**¿Tienes dudas?** Revisa esta guía paso a paso o consulta los logs de n8n/API para debugging.
