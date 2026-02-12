# =============================================================================
# Verificación de Optimización Docker - KnowLigo
# =============================================================================
# Ejecutar después del build: .\verify-docker.ps1

Write-Host "`n🔍 Verificación de Optimización Docker KnowLigo" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

# Verificar que Docker está corriendo
try {
    docker ps | Out-Null
}
catch {
    Write-Host "❌ Error: Docker no está corriendo`n" -ForegroundColor Red
    exit 1
}

Write-Host "📊 Análisis de Imagen Docker`n" -ForegroundColor Yellow

# 1. Tamaño de imagen
Write-Host "1. Tamaño de Imagen:" -ForegroundColor Cyan
$imageInfo = docker images knowligo-api:latest --format "{{.Repository}}:{{.Tag}}`t{{.Size}}`t{{.CreatedAt}}"
if ($imageInfo) {
    Write-Host "   $imageInfo" -ForegroundColor Green
    
    # Extraer tamaño
    $size = docker images knowligo-api:latest --format "{{.Size}}"
    $sizeValue = [float]($size -replace '[^0-9.]', '')
    
    if ($size -match "GB") {
        if ($sizeValue -lt 0.7) {
            Write-Host "   ✅ Tamaño óptimo (<700MB)" -ForegroundColor Green
        }
        else {
            Write-Host "   ⚠️  Tamaño alto (>${sizeValue}GB)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "   ✅ Tamaño excelente (<1GB)" -ForegroundColor Green
    }
}
else {
    Write-Host "   ❌ Imagen no encontrada. Ejecuta primero: .\docker-build.ps1" -ForegroundColor Red
    exit 1
}

# 2. Número de layers
Write-Host "`n2. Layers de Imagen:" -ForegroundColor Cyan
$layers = docker history knowligo-api:latest --no-trunc --format "{{.CreatedBy}}" | Measure-Object | Select-Object -ExpandProperty Count
Write-Host "   Total de layers: $layers" -ForegroundColor White

if ($layers -le 10) {
    Write-Host "   ✅ Número óptimo de layers (<10)" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  Considerar consolidar layers" -ForegroundColor Yellow
}

# 3. Verificar multi-stage build
Write-Host "`n3. Multi-Stage Build:" -ForegroundColor Cyan
$dockerfileContent = Get-Content "Dockerfile" -Raw
if ($dockerfileContent -match "FROM.*AS builder" -and $dockerfileContent -match "FROM.*AS runtime") {
    Write-Host "   ✅ Multi-stage build detectado (builder + runtime)" -ForegroundColor Green
}
else {
    Write-Host "   ❌ Multi-stage build no encontrado" -ForegroundColor Red
}

# 4. Verificar usuario non-root
Write-Host "`n4. Seguridad - Usuario:" -ForegroundColor Cyan
if ($dockerfileContent -match "USER knowligo") {
    Write-Host "   ✅ Usuario non-root configurado (knowligo)" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  Ejecutando como root (riesgo de seguridad)" -ForegroundColor Yellow
}

# 5. Verificar BuildKit
Write-Host "`n5. BuildKit:" -ForegroundColor Cyan
if ($env:DOCKER_BUILDKIT -eq "1") {
    Write-Host "   ✅ BuildKit habilitado" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  BuildKit no habilitado (builds más lentos)" -ForegroundColor Yellow
    Write-Host "   Ejecuta: `$env:DOCKER_BUILDKIT=1" -ForegroundColor Gray
}

# 6. Verificar healthcheck
Write-Host "`n6. Healthcheck:" -ForegroundColor Cyan
$inspect = docker inspect knowligo-api:latest | ConvertFrom-Json
if ($inspect.Config.Healthcheck) {
    Write-Host "   ✅ Healthcheck configurado" -ForegroundColor Green
    $healthCmd = $inspect.Config.Healthcheck.Test -join " "
    Write-Host "   Comando: $healthCmd" -ForegroundColor Gray
}
else {
    Write-Host "   ❌ Healthcheck no configurado" -ForegroundColor Red
}

# 7. Verificar contenedores corriendo
Write-Host "`n7. Contenedores en Ejecución:" -ForegroundColor Cyan
$running = docker ps --filter "name=knowligo" --format "{{.Names}}`t{{.Status}}"
if ($running) {
    $running | ForEach-Object {
        Write-Host "   $_" -ForegroundColor Green
    }
}
else {
    Write-Host "   ⚠️  No hay contenedores corriendo" -ForegroundColor Yellow
    Write-Host "   Ejecuta: docker-compose up -d" -ForegroundColor Gray
}

# 8. Verificar optimizaciones en requirements.txt
Write-Host "`n8. Dependencias:" -ForegroundColor Cyan
$reqContent = Get-Content "requirements.txt" -Raw
$packages = (Get-Content "requirements.txt" | Where-Object { $_ -match "==" }).Count

Write-Host "   Total de dependencias directas: $packages" -ForegroundColor White

if ($packages -le 10) {
    Write-Host "   ✅ Dependencias mínimas ($packages paquetes)" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  Considerar revisar dependencias ($packages paquetes)" -ForegroundColor Yellow
}

# Verificar versiones pinned
$unpinned = Get-Content "requirements.txt" | Where-Object { $_ -match "^\w" -and $_ -notmatch "==" }
if ($unpinned.Count -eq 0) {
    Write-Host "   ✅ Todas las versiones están pinned (==)" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  Algunas versiones no están pinned:" -ForegroundColor Yellow
    $unpinned | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
}

# 9. Verificar .dockerignore
Write-Host "`n9. .dockerignore:" -ForegroundColor Cyan
if (Test-Path ".dockerignore") {
    $ignoreLines = (Get-Content ".dockerignore" | Where-Object { $_ -match "^\w" -or $_ -match "^\*" }).Count
    Write-Host "   ✅ Archivo existe ($ignoreLines reglas)" -ForegroundColor Green
    
    # Verificar reglas importantes
    $ignoreContent = Get-Content ".dockerignore" -Raw
    $importantRules = @("__pycache__", "*.pyc", ".git", "*.md", "venv", ".env")
    $missing = @()
    
    foreach ($rule in $importantRules) {
        if ($ignoreContent -notmatch [regex]::Escape($rule)) {
            $missing += $rule
        }
    }
    
    if ($missing.Count -eq 0) {
        Write-Host "   ✅ Reglas esenciales presentes" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️  Faltan reglas: $($missing -join ', ')" -ForegroundColor Yellow
    }
}
else {
    Write-Host "   ❌ .dockerignore no encontrado" -ForegroundColor Red
}

# 10. Verificar volúmenes
Write-Host "`n10. Volúmenes Docker:" -ForegroundColor Cyan
$volumes = docker volume ls --filter "name=knowligo" --format "{{.Name}}"
if ($volumes) {
    $volumes | ForEach-Object {
        Write-Host "   $_" -ForegroundColor Green
    }
    Write-Host "   ✅ Volúmenes persistentes configurados" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  No hay volúmenes creados" -ForegroundColor Yellow
}

# Resumen final
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📋 Resumen de Optimización" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$checks = @(
    @{Name="Multi-stage build"; Pass=$dockerfileContent -match "AS builder"},
    @{Name="Usuario non-root"; Pass=$dockerfileContent -match "USER knowligo"},
    @{Name="Healthcheck"; Pass=$inspect.Config.Healthcheck -ne $null},
    @{Name="BuildKit"; Pass=$env:DOCKER_BUILDKIT -eq "1"},
    @{Name=".dockerignore"; Pass=Test-Path ".dockerignore"},
    @{Name="Versiones pinned"; Pass=$unpinned.Count -eq 0},
    @{Name="Tamaño optimizado"; Pass=$size -notmatch "GB" -or $sizeValue -lt 0.7}
)

$passed = ($checks | Where-Object { $_.Pass }).Count
$total = $checks.Count

Write-Host "`nChecks pasados: $passed/$total" -ForegroundColor White

foreach ($check in $checks) {
    $icon = if ($check.Pass) { "✅" } else { "❌" }
    $color = if ($check.Pass) { "Green" } else { "Red" }
    Write-Host "$icon $($check.Name)" -ForegroundColor $color
}

if ($passed -eq $total) {
    Write-Host "`n🎉 ¡Todas las optimizaciones están aplicadas!" -ForegroundColor Green
}
elseif ($passed -ge ($total * 0.8)) {
    Write-Host "`n👍 La mayoría de optimizaciones están presentes" -ForegroundColor Yellow
}
else {
    Write-Host "`n⚠️  Considera aplicar más optimizaciones" -ForegroundColor Yellow
}

Write-Host "`n📚 Documentación:" -ForegroundColor Cyan
Write-Host "   - DOCKER_OPTIMIZATIONS.md" -ForegroundColor Gray
Write-Host "   - DEPENDENCIES.md" -ForegroundColor Gray
Write-Host "`n"
