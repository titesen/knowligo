# ADR-004: Webhook Directo en FastAPI sobre n8n

**Estado**: Aceptada (reemplaza implementación anterior)  
**Autores**: Facundo  

---

## Contexto

El proyecto inicialmente usaba **n8n** como middleware de automatización para recibir mensajes de WhatsApp y enviarlos a la API de KnowLigo. El flujo era:

```
WhatsApp → Meta Webhook → n8n (workflow JSON) → HTTP Request → FastAPI /query → respuesta → n8n → WhatsApp
```

Esto generaba varios problemas:
1. **Dependencia adicional**: n8n requiere su propio contenedor Docker + configuración
2. **Latencia extra**: Cada mensaje pasaba por n8n antes de llegar a la API (~200ms overhead)
3. **Complejidad de debug**: Errores en el workflow JSON de n8n eran difíciles de diagnosticar
4. **Estado duplicado**: n8n no conocía el contexto conversacional — todo el state management terminaba en FastAPI de todas formas
5. **Fragilidad**: El workflow de n8n (`whatsapp-rag-chatbot.json`) era un blob JSON monolítico difícil de versionar

## Decisión

**Eliminamos n8n** y manejamos el webhook de WhatsApp Business **directamente en FastAPI** con dos endpoints:

- `GET /webhook` — Verificación de Meta (challenge response)
- `POST /webhook` — Recepción de mensajes entrantes

## Consecuencias

### Beneficios
- **Una sola pieza**: Todo el flujo (recibir → procesar → responder) vive en un solo servicio
- **Docker simplificado**: `docker-compose.yml` pasa de 2 servicios (api + n8n) a 1 servicio (api)
- **Observabilidad**: Logs unificados — cada mensaje se loguea con `logger.info` en la misma aplicación
- **Testeable**: El webhook se testea con `TestClient` de FastAPI como cualquier otro endpoint
- **Latencia reducida**: ~200ms menos por eliminación del hop intermedio
- **State management nativo**: El `AgentOrchestrator` maneja contexto conversacional directamente

### Trade-offs aceptados
- **Sin UI visual de flujos**: n8n ofrecía una interfaz gráfica para ver el workflow — perdemos eso. Compensamos con diagramas Mermaid en la documentación
- **Más código Python**: El manejo del webhook (normalización de números argentinos, retry, dedup) ahora está en `api/main.py` (~80 líneas)
- **Carpeta `n8n/` residual**: Se mantiene el directorio con el workflow original como referencia histórica

### Implementación
```python
# api/main.py
@app.post("/webhook")
async def handle_webhook(request, orchestrator, settings):
    body = await request.json()
    # Validar → Extraer mensaje → Dedup → Orchestrator → WhatsApp reply
```

Funcionalidades incluidas en el webhook directo:
- Deduplicación de mensajes (`_is_duplicate_message` con TTL 5min)
- Normalización de números argentinos (549→54)
- Retry con formato alternativo si Meta rechaza el primer envío
- Manejo de mensajes no-texto con respuesta informativa
