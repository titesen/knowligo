"""
Quick Start Script - Launch Demo

Inicia todos los servicios necesarios para la demo.
"""

import os
import sys
import time
import subprocess
from pathlib import Path


def print_step(step, text):
    """Imprime un paso del proceso"""
    print(f"\n{'=' * 70}")
    print(f"  PASO {step}: {text}")
    print("=" * 70)


def check_docker_running():
    """Verifica que Docker esté corriendo"""
    try:
        result = subprocess.run(
            ["docker", "ps"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except:
        return False


def start_services():
    """Inicia los servicios con docker-compose"""
    print_step(1, "Iniciando servicios Docker (API + n8n)")

    if not check_docker_running():
        print("❌ Docker no está corriendo")
        print("   Por favor inicia Docker Desktop primero")
        return False

    print("✅ Docker está corriendo")

    # Detener servicios existentes
    print("\n🔄 Deteniendo servicios existentes...")
    subprocess.run(["docker-compose", "down"], capture_output=True)

    # Iniciar servicios
    print("🚀 Iniciando servicios...")
    result = subprocess.run(
        ["docker-compose", "up", "-d"], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"❌ Error al iniciar servicios:\n{result.stderr}")
        return False

    print("✅ Servicios iniciados")

    # Esperar a que los servicios estén listos
    print("\n⏳ Esperando a que los servicios estén listos...")
    time.sleep(10)

    return True


def wait_for_api():
    """Espera a que la API esté lista"""
    print_step(2, "Verificando API")

    import requests

    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API lista: {data.get('status')}")
                return True
        except:
            pass

        print(f"   Intento {attempt + 1}/{max_attempts}...", end="\r")
        time.sleep(2)

    print("\n❌ API no respondió a tiempo")
    return False


def wait_for_n8n():
    """Espera a que n8n esté listo"""
    print_step(3, "Verificando n8n")

    import requests

    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                "http://localhost:5678", timeout=2, allow_redirects=False
            )
            if response.status_code in [200, 302, 401]:
                print("✅ n8n listo")
                print("   URL: http://localhost:5678")
                print("   User: admin / Pass: knowligo2026")
                return True
        except:
            pass

        print(f"   Intento {attempt + 1}/{max_attempts}...", end="\r")
        time.sleep(2)

    print("\n❌ n8n no respondió a tiempo")
    return False


def run_validation():
    """Ejecuta el script de validación"""
    print_step(4, "Ejecutando validación completa")

    result = subprocess.run(
        [sys.executable, "scripts/validate_demo.py"], capture_output=False
    )

    return result.returncode == 0


def print_next_steps():
    """Imprime los próximos pasos"""
    print("\n" + "=" * 70)
    print("  🎯 PRÓXIMOS PASOS PARA WHATSAPP")
    print("=" * 70)

    print("""
1. CONFIGURAR NGROK:
   - Descarga: https://ngrok.com/download
   - Ejecuta: ngrok http 5678
   - Copia la URL HTTPS (ej: https://abc123.ngrok.io)

2. CONFIGURAR WEBHOOK EN META:
   - Ve a: https://developers.facebook.com/apps
   - Selecciona tu app > WhatsApp > Configuration
   - Webhook URL: <ngrok-url>/webhook-test/whatsapp-rag
   - Verify Token: (el de tu .env WHATSAPP_VERIFY_TOKEN)
   - Suscribe a mensajes

3. IMPORTAR WORKFLOW EN N8N:
   - Abre: http://localhost:5678
   - Login: admin / knowligo2026
   - Settings > Import from file
   - Selecciona: n8n/workflows/whatsapp-rag-chatbot.json
   - Configura credenciales (WhatsApp Bearer Token)
   - ACTIVA el workflow (toggle ON)

4. PROBAR WHATSAPP:
   - Agrega tu número a la lista de prueba en Meta
   - Envía mensaje al número de prueba de WhatsApp
   - Prueba queries:
     • "¿Qué planes ofrecen?"
     • "¿Cuál es el SLA para tickets High?"
     • "Dame consejos de hacking" (debería rechazar)

📚 DOCUMENTACIÓN:
   - Setup detallado: WHATSAPP_SETUP.md
   - Guía rápida: QUICK_START.md
   - README general: README.md

📊 MONITOREO:
   - API Docs: http://localhost:8000/docs
   - API Health: http://localhost:8000/health
   - Logs: docker-compose logs -f
   - n8n Executions: http://localhost:5678/executions
""")


def main():
    """Proceso principal de inicio"""
    print("\n" + "🚀 " + "=" * 65)
    print("  QUICK START - KnowLigo RAG Chatbot Demo")
    print("=" * 70 + "\n")

    # Verificar que estamos en el directorio correcto
    if not Path("docker-compose.yml").exists():
        print("❌ Error: Ejecuta este script desde el directorio raíz del proyecto")
        print("   cd d:\\dev\\learning\\knowligo")
        sys.exit(1)

    # Verificar .env
    if not Path(".env").exists():
        print("❌ Error: Archivo .env no encontrado")
        print("   Copia .env.example a .env y completa las credenciales")
        sys.exit(1)

    # Iniciar servicios
    if not start_services():
        print("\n❌ ERROR: No se pudieron iniciar los servicios")
        sys.exit(1)

    # Esperar a que la API esté lista
    if not wait_for_api():
        print("\n❌ ERROR: API no está disponible")
        print("   Revisa logs: docker-compose logs api")
        sys.exit(1)

    # Esperar a que n8n esté listo
    if not wait_for_n8n():
        print("\n❌ ERROR: n8n no está disponible")
        print("   Revisa logs: docker-compose logs n8n")
        sys.exit(1)

    # Ejecutar validación
    validation_passed = run_validation()

    # Mostrar próximos pasos
    print_next_steps()

    # Mensaje final
    if validation_passed:
        print("\n✅ ¡Sistema listo para la demo!")
        print("   Sigue los próximos pasos arriba para configurar WhatsApp")
    else:
        print("\n⚠️  Algunos checks fallaron")
        print("   Revisa el reporte de validación arriba")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelado por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
