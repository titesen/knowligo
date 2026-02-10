# KnowLigo - Script de Inicio Rápido
# Ejecuta: .\scripts\start.ps1

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   🚀 KnowLigo RAG Chatbot - Inicio" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Verificar entorno virtual
if (!(Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Entorno virtual no encontrado" -ForegroundColor Red
    Write-Host "   Ejecuta: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Activar entorno virtual
Write-Host "📦 Activando entorno virtual..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1

# Verificar .env
if (!(Test-Path ".env")) {
    Write-Host "⚠️  Archivo .env no encontrado" -ForegroundColor Yellow
    Write-Host "   Copiando desde .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "   ✅ Archivo .env creado" -ForegroundColor Green
    Write-Host "   ⚠️  IMPORTANTE: Edita .env y agrega tu GROQ_API_KEY" -ForegroundColor Yellow
    Write-Host "   Obtén tu key en: https://console.groq.com/keys`n" -ForegroundColor Cyan
}

# Verificar base de datos
if (!(Test-Path ".\database\sqlite\knowligo.db")) {
    Write-Host "📊 Inicializando base de datos..." -ForegroundColor Green
    python scripts\utils\init_db.py
}

# Verificar índice FAISS
if (!(Test-Path ".\rag\store\faiss.index")) {
    Write-Host "`n🔍 Construyendo índice vectorial..." -ForegroundColor Green
    Write-Host "   (Esto puede tardar 1-2 minutos la primera vez)`n" -ForegroundColor Yellow
    python rag\ingest\build_index.py
}

# Menú de opciones
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   Selecciona una opción:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Iniciar API (desarrollo local)" -ForegroundColor White
Write-Host "2. Ejecutar tests automáticos" -ForegroundColor White
Write-Host "3. Iniciar con Docker (API + n8n)" -ForegroundColor White
Write-Host "4. Ver documentación API (Swagger)" -ForegroundColor White
Write-Host "5. Salir`n" -ForegroundColor White

$opcion = Read-Host "Opción"

switch ($opcion) {
    "1" {
        Write-Host "`n🚀 Iniciando API en http://localhost:8000" -ForegroundColor Green
        Write-Host "   Docs: http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host "   Presiona CTRL+C para detener`n" -ForegroundColor Yellow
        python api\main.py
    }
    "2" {
        Write-Host "`n🧪 Ejecutando tests..." -ForegroundColor Green
        Write-Host "   (Asegúrate de que la API esté corriendo en otra terminal)`n" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        python scripts\test_api.py
    }
    "3" {
        Write-Host "`n🐳 Iniciando servicios con Docker..." -ForegroundColor Green
        Write-Host "   API: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "   n8n: http://localhost:5678 (admin/knowligo2026)" -ForegroundColor Cyan
        Write-Host "`n   Presiona CTRL+C y luego ejecuta 'docker-compose down' para detener`n" -ForegroundColor Yellow
        docker-compose up
    }
    "4" {
        Write-Host "`n📖 Abriendo documentación..." -ForegroundColor Green
        Start-Process "http://localhost:8000/docs"
        Write-Host "   Si la API no está corriendo, ejecuta la opción 1 primero" -ForegroundColor Yellow
    }
    "5" {
        Write-Host "`n👋 ¡Hasta luego!" -ForegroundColor Cyan
        exit 0
    }
    default {
        Write-Host "`n❌ Opción inválida" -ForegroundColor Red
    }
}

Write-Host "`n========================================`n" -ForegroundColor Cyan
