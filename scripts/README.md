# Scripts de KnowLigo

Scripts de utilidad para inicializar, validar y probar el sistema.

---

## 📋 Scripts Disponibles

### 🚀 `quick_start.py`
**Inicio rápido de todos los servicios**

Inicia automáticamente todos los servicios necesarios (API) y ejecuta validación completa.

```powershell
python scripts\quick_start.py
```

**Qué hace:**
1. Verifica que Docker esté corriendo
2. Detiene servicios existentes
3. Inicia servicios con `docker-compose up -d`
4. Espera a que API esté lista (max 60s)
5. Ejecuta validación completa (`validate_demo.py`)
6. Muestra próximos pasos para WhatsApp

**Cuándo usar:**
- Primera vez configurando el proyecto
- Después de reiniciar tu máquina
- Cuando quieras iniciar todos los servicios de una vez

---

### ✅ `validate_demo.py`
**Validación pre-demo completa**

Verifica que todos los componentes estén configurados correctamente.

```powershell
python scripts\validate_demo.py
```

**Checks realizados:**
1. ✅ Archivo `.env` existe y tiene todas las variables
2. ✅ Base de datos SQLite inicializada con datos
3. ✅ Índice FAISS construido con chunks
4. ✅ API corriendo y respondiendo
5. ✅ Query de prueba funciona correctamente

**Output:**
- ✅ Checks pasados (verde)
- ❌ Checks fallidos (rojo) con instrucciones de fix
- Resumen final con % de completitud

**Exit code:**
- `0` - Todos los checks pasaron
- `1` - Uno o más checks fallaron

---

### 🧪 `test_api.py`
**Suite de tests para la API**

Ejecuta tests funcionales completos de todos los endpoints.

```powershell
python scripts\test_api.py
```

**Tests incluidos:**
1. Health check endpoint
2. Query con mensaje válido
3. Query con mensaje vacío (error)
4. Query sin user_id (error)  
5. Stats endpoint
6. Query off-topic (rechazo)
7. Campos en respuesta

**Requisitos:**
- API debe estar corriendo (localhost:8000)
- Índice FAISS debe estar construido
- Base de datos debe estar inicializada

**Output:**
```
Running API Tests...
✓ Health check
✓ Valid query
✓ Empty message handling
...
All tests passed! ✓
```

---

### 🔄 `start.ps1`
**Script interactivo de PowerShell**

Script interactivo con menú de opciones para gestionar el proyecto.

```powershell
.\scripts\start.ps1
```

**Opciones del menú:**
1. Iniciar API (desarrollo local)
2. Ejecutar tests automáticos
3. Iniciar con Docker
4. Ver documentación API (Swagger)
5. Salir

**Cuándo usar:**
- Gestión diaria del proyecto
- Cuando prefieras menú interactivo vs comandos manuales
- Para usuarios menos familiarizados con CLI

---

## 🛠️ Scripts de Utilidades (`utils/`)

### `utils/init_db.py`
**Inicializar base de datos SQLite**

Crea la base de datos, ejecuta schema SQL e inserta datos de prueba.

```powershell
python scripts\utils\init_db.py
```

**Qué hace:**
1. Crea `database/sqlite/knowligo.db`
2. Ejecuta `database/schema/schema.sql` (tablas)
3. Ejecuta `database/seeds/seed.sql` (datos de prueba)

**Datos creados:**
- 8 clientes
- 3 planes (Basic, Professional, Enterprise)
- 8 contratos
- 17 tickets de ejemplo

**Cuándo usar:**
- Primera configuración del proyecto
- Después de corromper la base de datos
- Para resetear datos de prueba

---

## 📊 Workflow de Desarrollo

### Setup inicial (primera vez)
```powershell
# 1. Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar .env
Copy-Item .env.example .env
# Editar .env con tus credenciales

# 4. Inicializar DB
python scripts\utils\init_db.py

# 5. Construir índice FAISS
python rag\ingest\build_index.py

# 6. Validar
python scripts\validate_demo.py
```

### Inicio diario
```powershell
# Opción A: Script automático
python scripts\quick_start.py

# Opción B: Manual
docker-compose up -d
python scripts\validate_demo.py
```

### Desarrollo
```powershell
# Iniciar API en modo dev
python api\main.py

# En otra terminal: ejecutar tests
python scripts\test_api.py

# Ver logs
docker-compose logs -f
```

### Pre-demo (antes de grabar video)
```powershell
# 1. Validar completo
python scripts\validate_demo.py

# 2. Si algo falla, ver DEMO_CHECKLIST.md
# 3. Ejecutar tests
python scripts\test_api.py

# 4. Probar query manual en WhatsApp
```

---

## 🐛 Troubleshooting

### Error: "API no está corriendo"
```powershell
# Ver logs
docker-compose logs api

# Reiniciar servicio
docker-compose restart api

# O ejecutar en modo dev
python api\main.py
```

### Error: "Base de datos no existe"
```powershell
python scripts\utils\init_db.py
```

### Error: "Índice FAISS no existe"  
```powershell
python rag\ingest\build_index.py
```

### Error: "GROQ_API_KEY no configurado"
```powershell
# Verificar .env existe
Get-Content .env

# Si falta, copiar template
Copy-Item .env.example .env

# Editar y agregar API key
notepad .env
```

### Error: "Docker no está corriendo"
```powershell
# Iniciar Docker Desktop manualmente
# Luego:
docker-compose up -d
```

---

## 📚 Referencias

- **WHATSAPP_SETUP.md** - Configuración completa de WhatsApp
- **QUICK_START.md** - Guía rápida de inicio
- **DEMO_CHECKLIST.md** - Checklist pre-demo
- **DEMO_SCRIPT.md** - Script para video de LinkedIn
- **README.md** - Documentación principal

---

## 💡 Tips

1. **Ejecuta `validate_demo.py` frecuentemente** para detectar problemas temprano
2. **Usa `quick_start.py`** para inicios rápidos
3. **`test_api.py`** es útil para CI/CD (exit code 0/1)
4. **`start.ps1`** es ideal para demos en vivo (menú visual)
5. **Revisa logs** con `docker-compose logs -f` cuando haya errores

---

**¿Dudas?** Revisa la documentación principal en `README.md`
