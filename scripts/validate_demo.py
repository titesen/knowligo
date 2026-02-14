"""
Pre-Demo Validation Script

Verifica que todos los componentes estén listos para la demo de WhatsApp.
"""

import os
import sys
from pathlib import Path
import requests
import sqlite3


def print_header(text):
    """Imprime un header formateado"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print("=" * 70)


def print_check(passed, message, details=""):
    """Imprime el resultado de un check"""
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    if details:
        print(f"   {details}")
    return passed


def check_env_file():
    """Verifica que existe .env con las credenciales necesarias"""
    print_header("1. Verificando archivo .env")

    env_path = Path(".env")
    if not env_path.exists():
        print_check(False, "Archivo .env no encontrado")
        print("   Copia .env.example a .env y completa las credenciales")
        return False

    print_check(True, "Archivo .env existe")

    # Cargar y verificar variables
    from dotenv import load_dotenv

    load_dotenv()

    required_vars = {
        "GROQ_API_KEY": "API key de Groq",
        "WHATSAPP_PHONE_NUMBER_ID": "Phone Number ID de WhatsApp",
        "WHATSAPP_TOKEN": "Access Token de WhatsApp",
        "WHATSAPP_VERIFY_TOKEN": "Verify Token para webhook",
    }

    all_set = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value.startswith("your_"):
            all_set = False
            print_check(False, f"{var}", f"Falta configurar: {description}")
        else:
            # Ocultar valores sensibles
            masked = value[:10] + "..." if len(value) > 10 else "***"
            print_check(True, f"{var}", f"Configurado: {masked}")

    return all_set


def check_database():
    """Verifica que la base de datos esté inicializada"""
    print_header("2. Verificando Base de Datos")

    db_path = Path("database/sqlite/knowligo.db")

    if not db_path.exists():
        print_check(False, "Base de datos no existe")
        print("   Ejecuta: python scripts/utils/init_db.py")
        return False

    print_check(True, "Archivo de base de datos existe")

    # Verificar tablas
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = ["clients", "plans", "contracts", "tickets", "query_logs"]
        missing = [t for t in required_tables if t not in tables]

        if missing:
            print_check(False, "Faltan tablas", f"Faltantes: {', '.join(missing)}")
            conn.close()
            return False

        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM clients")
        client_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM plans")
        plan_count = cursor.fetchone()[0]

        conn.close()

        print_check(True, f"Todas las tablas presentes")
        print_check(
            True, f"Datos de prueba", f"{client_count} clientes, {plan_count} planes"
        )
        return True

    except Exception as e:
        print_check(False, "Error al leer base de datos", str(e))
        return False


def check_faiss_index():
    """Verifica que el índice FAISS esté construido"""
    print_header("3. Verificando Índice FAISS")

    index_path = Path("rag/store/faiss.index")
    chunks_path = Path("rag/store/chunks.pkl")
    metadata_path = Path("rag/store/metadata.json")

    all_ok = True

    if not index_path.exists():
        print_check(False, "Índice FAISS no existe")
        print("   Ejecuta: python rag/ingest/build_index.py")
        all_ok = False
    else:
        print_check(True, "Índice FAISS existe")

    if not chunks_path.exists():
        print_check(False, "Chunks no existen")
        all_ok = False
    else:
        print_check(True, "Chunks existen")

    if not metadata_path.exists():
        print_check(False, "Metadata no existe")
        all_ok = False
    else:
        import json

        with open(metadata_path) as f:
            metadata = json.load(f)

        total_chunks = metadata.get("total_chunks", 0)
        docs = metadata.get("documents_indexed", [])

        print_check(True, "Metadata existe")
        print_check(
            total_chunks > 0,
            f"Chunks indexados",
            f"{total_chunks} chunks, {len(docs)} documentos",
        )

    return all_ok


def check_api_running():
    """Verifica que la API esté corriendo"""
    print_header("4. Verificando API")

    try:
        response = requests.get("http://localhost:8000/health", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print_check(True, "API está corriendo")
            print_check(True, f"Status: {data.get('status')}")

            components = data.get("components", {})
            for comp, status in components.items():
                is_ok = "ok" in str(status).lower()
                print_check(is_ok, f"  {comp}", status)

            return True
        else:
            print_check(
                False, "API responde con error", f"Status: {response.status_code}"
            )
            return False

    except requests.exceptions.ConnectionError:
        print_check(False, "API no está corriendo")
        print("   Ejecuta: python api/main.py")
        print("   O: docker-compose up -d")
        return False
    except Exception as e:
        print_check(False, "Error al conectar con API", str(e))
        return False


def test_api_query():
    """Prueba una query de ejemplo en la API"""
    print_header("7. Probando Query de Ejemplo")

    try:
        payload = {
            "user_id": "validation_test",
            "message": "¿Qué planes de soporte ofrecen?",
        }

        response = requests.post(
            "http://localhost:8000/query", json=payload, timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            if data.get("success"):
                print_check(True, "Query procesada exitosamente")
                print_check(True, f"Intent: {data.get('intent')}")
                print_check(
                    True, f"Response length: {len(data.get('response', ''))} chars"
                )
                print_check(True, f"Tokens used: {data.get('tokens_used', 0)}")

                # Mostrar respuesta (truncada)
                response_text = data.get("response", "")
                preview = (
                    response_text[:100] + "..."
                    if len(response_text) > 100
                    else response_text
                )
                print(f"\n   Respuesta: {preview}\n")

                return True
            else:
                print_check(False, "Query falló", data.get("error"))
                return False
        else:
            print_check(False, "API error", f"Status: {response.status_code}")
            return False

    except Exception as e:
        print_check(False, "Error en test query", str(e))
        return False


def print_summary(results):
    """Imprime resumen final"""
    print_header("RESUMEN DE VALIDACIÓN")

    total = len(results)
    passed = sum(results.values())

    print(f"\nTotal checks: {total}")
    print(f"Pasados: {passed} ✅")
    print(f"Fallidos: {total - passed} ❌")

    percentage = (passed / total * 100) if total > 0 else 0

    print(f"\nCompletado: {percentage:.1f}%")

    if percentage == 100:
        print("\n" + "=" * 70)
        print("  🎉 ¡TODO LISTO PARA LA DEMO!")
        print("=" * 70)
        print("\nPróximos pasos:")
        print("1. Configura ngrok: ngrok http 8000")
        print("2. Configura webhook en Meta Developers")
        print("3. Envía mensaje de prueba a WhatsApp")
        print("\nVer WHATSAPP_SETUP.md para instrucciones detalladas")
    else:
        print("\n" + "=" * 70)
        print("  ⚠️  FALTAN CONFIGURACIONES")
        print("=" * 70)
        print("\nRevisa los checks fallidos arriba ❌")
        print("Sigue las instrucciones de cada sección")


def main():
    """Ejecuta todas las validaciones"""
    print("\n" + "🔍 " + "=" * 66)
    print("  VALIDACIÓN PRE-DEMO - KnowLigo RAG Chatbot")
    print("=" * 70 + "\n")

    results = {}

    # Ejecutar checks
    results["env_file"] = check_env_file()
    results["database"] = check_database()
    results["faiss_index"] = check_faiss_index()
    results["api_running"] = check_api_running()

    # Solo hacer estos si la API está corriendo
    if results["api_running"]:
        results["test_query"] = test_api_query()

    # Resumen
    print_summary(results)

    # Exit code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Validación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
