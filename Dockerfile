# Dockerfile para KnowLigo RAG API
FROM python:3.11-slim

# Metadata
LABEL maintainer="KnowLigo"
LABEL description="RAG-powered IT support chatbot API"

# Configurar directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY rag/ ./rag/
COPY api/ ./api/
COPY knowledge/ ./knowledge/
COPY database/ ./database/

# Crear directorios necesarios
RUN mkdir -p /app/database/sqlite /app/rag/store

# Exponer puerto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicio
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
