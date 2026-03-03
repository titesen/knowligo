# ADR-001: SQLite sobre PostgreSQL

**Estado**: Aceptada  
**Fecha**: 2025-12-01  
**Autores**: Facundo  

---

## Contexto

KnowLigo necesita una base de datos relacional para almacenar clientes, contratos, tickets, pagos y logs de conversaciones. Las opciones evaluadas fueron:

1. **PostgreSQL** — Base de datos relacional completa, escalable, con soporte para pgvector
2. **SQLite** — Base de datos embebida, sin servidor, incluida en Python stdlib

El proyecto es un **demo educativo** que debe ser ejecutable en una sola máquina sin infraestructura adicional, desplegable con `docker-compose up` sin dependencias de servicios externos.

## Decisión

**Usamos SQLite** como base de datos principal.

## Consecuencias

### Beneficios
- **Cero dependencias**: SQLite viene built-in con Python 3.11 — no requiere servidor, instalación ni configuración
- **Portabilidad total**: La base de datos es un archivo (`knowligo.db`) que se copia, respalda o reinicia trivialmente
- **Docker simplificado**: Un solo contenedor (API) en lugar de dos (API + DB), reduce complejidad del compose
- **Setup instantáneo**: `python scripts/utils/init_db.py` crea todo el schema + seed data en <1 segundo
- **Ideal para demo**: Audiencia de LinkedIn puede clonar y ejecutar sin instalar PostgreSQL

### Trade-offs aceptados
- **Sin concurrencia de escritura**: SQLite usa file-level locking — suficiente para un bot WhatsApp single-user pero no escalaría a cientos de usuarios concurrentes
- **Sin async driver nativo**: Usamos `sqlite3` síncrono + `asyncio.to_thread()` para no bloquear el event loop. Para producción se recomendaría `asyncpg` con PostgreSQL
- **Sin pgvector**: Vectores se almacenan en FAISS (archivo separado), no en la DB. Si migramos a PostgreSQL, podríamos unificar con pgvector
- **Sin JSON operators nativos**: El campo `context` de `conversations` usa JSON como TEXT — parseamos en Python

### Criterio de migración
Si el proyecto escala a producción, migrar a PostgreSQL con:
1. SQLAlchemy 2.0 async + asyncpg
2. pgvector para unificar vectores + datos relacionales
3. Alembic para migraciones de schema
