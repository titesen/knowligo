# =============================================================================
# Multi-stage Dockerfile para KnowLigo RAG API
# Optimizado para tamaño mínimo y máxima eficiencia
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Instala dependencias
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Variables de optimización para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Instalar solo build dependencies necesarias (solo si son requeridas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y crear virtualenv
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias optimizadas:
# - Preferir wheels pre-compilados
# - Instalar en orden óptimo (framework primero, luego ML libs)
# - Limpiar archivos temporales inmediatamente
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
        # Web framework (ligero, instalar primero)
        fastapi==0.109.2 \
        uvicorn[standard]==0.27.1 \
        pydantic==2.6.1 \
        requests==2.31.0 \
        python-dotenv==1.0.1 \
        markdown==3.5.2 \
        groq==0.4.2 && \
    pip install --no-cache-dir \
        # ML libraries (pesadas, con wheels pre-compilados)
        faiss-cpu==1.13.2 \
        sentence-transformers==2.5.1 && \
    # Limpiar archivos temporales de Python
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name '*.pyc' -delete && \
    find /opt/venv -type f -name '*.pyo' -delete && \
    find /opt/venv -type d -name '*.dist-info' -exec sh -c 'rm -rf "$1"/{RECORD,WHEEL,INSTALLER}' _ {} \; 2>/dev/null || true

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Imagen final mínima
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# Metadata
LABEL maintainer="KnowLigo" \
      description="RAG-powered IT support chatbot API" \
      version="1.0.0"

WORKDIR /app

# Copiar virtualenv desde builder (ya optimizado y limpio)
COPY --from=builder /opt/venv /opt/venv

# Variables de entorno optimizadas para producción
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Optimizaciones de PyTorch/Transformers
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false

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

# Healthcheck eficiente usando socket directo (más rápido que HTTP request)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

# Comando de inicio
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
