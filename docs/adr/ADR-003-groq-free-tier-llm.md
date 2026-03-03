# ADR-003: Groq API (Free Tier) como Proveedor LLM

**Estado**: Aceptada  
**Fecha**: 2025-12-01  
**Autores**: Facundo  

---

## Contexto

KnowLigo necesita un LLM para:
1. Generar respuestas RAG en español
2. Clasificar intenciones del usuario (router)
3. Reescribir queries (HyDE)
4. Generar saludos/despedidas variados

Las opciones evaluadas fueron:

| Proveedor | Modelo | Costo | Latencia | Calidad español |
|-----------|--------|-------|----------|-----------------|
| OpenAI | GPT-4o | ~$5-15/1M tokens | ~800ms | Excelente |
| Anthropic | Claude 3.5 Sonnet | ~$3-15/1M tokens | ~1s | Excelente |
| **Groq** | **Llama 3.3 70B** | **$0 (free tier)** | **~300ms** | **Muy bueno** |
| Ollama (local) | Llama 3.1 8B | $0 (GPU local) | ~2s+ | Aceptable |

El proyecto es un **demo educativo** con objetivo de **costo operativo $0/mes** y la menor barrera de entrada posible para quien quiera replicarlo.

## Decisión

**Usamos Groq API con el modelo Llama 3.3 70B Versatile** en su free tier.

## Consecuencias

### Beneficios
- **Costo $0**: Free tier con límite generoso (14,400 requests/día, 6,000 tokens/min)
- **Latencia líder**: Groq usa hardware LPU especializado — ~300ms para generación, 3-10x más rápido que cloud LLMs convencionales
- **Calidad suficiente**: Llama 3.3 70B maneja español correctamente, sigue instrucciones de sistema, genera JSON válido para el router
- **SDK oficial Python**: `pip install groq` — API compatible con OpenAI client patterns
- **Barrera de entrada mínima**: Crear cuenta en console.groq.com toma 1 minuto

### Trade-offs aceptados
- **Rate limits free tier**: 30 req/min, 14,400 req/día. Suficiente para demo, requiere rate limiting propio (30 queries/hora/usuario)
- **Sin fine-tuning**: Groq no ofrece fine-tuning en free tier — usamos system prompts detallados como compensación
- **Vendor lock-in mínimo**: El code usa `Groq` client pero la interfaz es idéntica a OpenAI — migrar requiere cambiar 1 import + API key
- **Disponibilidad**: Free tier no tiene SLA — aceptable para proyecto educativo

### Criterio de migración
Si el proyecto necesita producción:
1. Migrar a OpenAI GPT-4o o Anthropic Claude para SLA + fine-tuning
2. Cambiar `GroqResponder` → `OpenAIResponder` (misma interfaz chat completions)
3. Ajustar rate limits y token budgets
