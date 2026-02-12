# =============================================================================
# KnowLigo - Build y Deploy Optimizado con Docker
# =============================================================================
# Script para Windows PowerShell
# Uso: .\docker-build.ps1 [dev|prod|clean]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('dev', 'prod', 'clean', 'rebuild')]
    [string]$Mode = 'dev'
)

Write-Host "`n🚀 KnowLigo - Docker Build Script" -ForegroundColor Cyan
Write-Host "=================================`n" -ForegroundColor Cyan

# Verificar que Docker está corriendo
function Test-DockerRunning {
    try {
        docker ps | Out-Null
        return $true
    }
    catch {
        Write-Host "❌ Error: Docker no está corriendo" -ForegroundColor Red
        Write-Host "Inicia Docker Desktop y vuelve a intentar`n" -ForegroundColor Yellow
        exit 1
    }
}

# Habilitar BuildKit para builds más rápidos
function Enable-BuildKit {
    Write-Host "⚡ Habilitando Docker BuildKit (requerido para optimizaciones)..." -ForegroundColor Green
    $env:DOCKER_BUILDKIT = 1
    $env:COMPOSE_DOCKER_CLI_BUILD = 1
    $env:BUILDKIT_PROGRESS = "auto"
    # Habilitar inline cache para builds incremental
    $env:BUILDKIT_INLINE_CACHE = 1
}

# Verificar archivo .env
function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        Write-Host "⚠️  Archivo .env no encontrado" -ForegroundColor Yellow
        
        if (Test-Path ".env.example") {
            Write-Host "📝 Copiando .env.example a .env..." -ForegroundColor Cyan
            Copy-Item ".env.example" ".env"
            Write-Host "`n⚠️  IMPORTANTE: Edita el archivo .env con tus credenciales`n" -ForegroundColor Yellow
            return $false
        }
        else {
            Write-Host "❌ Error: No existe .env ni .env.example`n" -ForegroundColor Red
            exit 1
        }
    }
    return $true
}

# Limpiar recursos Docker
function Clear-DockerResources {
    Write-Host "`n🧹 Limpiando recursos Docker..." -ForegroundColor Yellow
    
    Write-Host "  - Deteniendo contenedores..." -ForegroundColor Gray
    docker-compose down -v 2>$null
    
    Write-Host "  - Limpiando imágenes antiguas..." -ForegroundColor Gray
    docker image prune -f | Out-Null
    
    Write-Host "  - Limpiando build cache..." -ForegroundColor Gray
    docker builder prune -f | Out-Null
    
    Write-Host "✅ Limpieza completada`n" -ForegroundColor Green
}

# Build modo desarrollo
function Build-Dev {
    Write-Host "🔨 Construyendo en modo DESARROLLO..." -ForegroundColor Cyan
    Write-Host "  - BuildKit: Habilitado (cache inline)" -ForegroundColor Gray
    Write-Host "  - Multi-stage: 2 stages optimizados" -ForegroundColor Gray
    Write-Host "  - Wheels: Pre-compilados (no compilation)" -ForegroundColor Gray
    Write-Host "  - Cache layers: Máximo reuso`n" -ForegroundColor Gray
    
    docker-compose build --parallel
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Build completado exitosamente" -ForegroundColor Green
        
        # Mostrar tamaño de imagen
        $imageSize = docker images knowligo-api:latest --format "{{.Size}}"
        Write-Host "📦 Tamaño de imagen API: $imageSize" -ForegroundColor Cyan
        
        Write-Host "`n🚀 Iniciando contenedores..." -ForegroundColor Cyan
        docker-compose up -d
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ Contenedores iniciados" -ForegroundColor Green
            Show-Status
        }
    }
    else {
        Write-Host "`n❌ Error en el build" -ForegroundColor Red
        exit 1
    }
}

# Build modo producción
function Build-Prod {
    Write-Host "🔨 Construyendo en modo PRODUCCIÓN..." -ForegroundColor Cyan
    Write-Host "  - BuildKit habilitado: Sí" -ForegroundColor Gray
    Write-Host "  - Resource limits: Sí" -ForegroundColor Gray
    Write-Host "  - Security hardening: Sí`n" -ForegroundColor Gray
    
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --parallel --pull
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Build completado exitosamente" -ForegroundColor Green
        Write-Host "`n🚀 Iniciando contenedores (producción)..." -ForegroundColor Cyan
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ Contenedores iniciados" -ForegroundColor Green
            Show-Status
        }
    }
    else {
        Write-Host "`n❌ Error en el build" -ForegroundColor Red
        exit 1
    }
}

# Rebuild completo (sin cache)
function Build-Rebuild {
    Write-Host "🔨 Rebuild completo (SIN CACHE)..." -ForegroundColor Yellow
    Write-Host "⚠️  Esto descargará todo desde cero`n" -ForegroundColor Yellow
    
    docker-compose build --no-cache --pull --parallel
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Rebuild completado" -ForegroundColor Green
        Write-Host "`n🚀 Iniciando contenedores..." -ForegroundColor Cyan
        docker-compose up -d
        
        if ($LASTEXITCODE -eq 0) {
            Show-Status
        }
    }
}

# Mostrar estado de contenedores
function Show-Status {
    Write-Host "`n📊 Estado de contenedores:" -ForegroundColor Cyan
    Write-Host "==========================`n" -ForegroundColor Cyan
    
    docker-compose ps
    
    Write-Host "`n🌐 URLs disponibles:" -ForegroundColor Cyan
    Write-Host "  - API:        http://localhost:8000" -ForegroundColor Green
    Write-Host "  - API Docs:   http://localhost:8000/docs" -ForegroundColor Green
    Write-Host "  - n8n:        http://localhost:5678" -ForegroundColor Green
    Write-Host "  - Health:     http://localhost:8000/health`n" -ForegroundColor Green
    
    Write-Host "📝 Comandos útiles:" -ForegroundColor Cyan
    Write-Host "  docker-compose logs -f api    # Ver logs de API" -ForegroundColor Gray
    Write-Host "  docker-compose logs -f n8n    # Ver logs de n8n" -ForegroundColor Gray
    Write-Host "  docker-compose down           # Detener servicios" -ForegroundColor Gray
    Write-Host "  docker-compose restart api    # Reiniciar API`n" -ForegroundColor Gray
}

# =============================================================================
# MAIN
# =============================================================================

Test-DockerRunning
Enable-BuildKit

switch ($Mode) {
    'dev' {
        if (Test-EnvFile) {
            Build-Dev
        }
    }
    'prod' {
        if (Test-EnvFile) {
            Build-Prod
        }
        else {
            Write-Host "❌ Configura .env antes de usar modo producción`n" -ForegroundColor Red
            exit 1
        }
    }
    'clean' {
        Clear-DockerResources
    }
    'rebuild' {
        if (Test-EnvFile) {
            Build-Rebuild
        }
    }
}

Write-Host "`n✨ Completado!`n" -ForegroundColor Green
