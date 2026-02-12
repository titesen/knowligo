# =============================================================================
# Multi-stage Dockerfile para KnowLigo RAG API
# Optimizado para tamaño mínimo y máxima eficiencia
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Instala dependencias
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Instalar solo build dependencies necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y crear virtualenv
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias en virtualenv
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Imagen final mínima
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# Metadata
LABEL maintainer="KnowLigo" \
      description="RAG-powered IT support chatbot API" \
      version="1.0.0"

WORKDIR /app

# Copiar virtualenv desde builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crear usuario non-root para seguridad
RUN groupadd -r knowligo && useradd -r -g knowligo -u 1001 knowligo && \
    mkdir -p /app/database/sqlite /app/rag/store && \
    chown -R knowligo:knowligo /app

# Copiar código (orden optimizado para layer caching)
COPY --chown=knowligo:knowligo database/ ./database/
COPY --chown=knowligo:knowligo knowledge/ ./knowledge/
COPY --chown=knowligo:knowligo rag/ ./rag/
COPY --chown=knowligo:knowligo api/ ./api/

# Cambiar a usuario non-root
USER knowligo

# Exponer puerto
EXPOSE 8000

# Healthcheck sin curl (usa Python requests)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=3).raise_for_status()" || exit 1

# Comando de inicio
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
