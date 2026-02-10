"""
Script de prueba para el API de KnowLigo

Ejecuta queries de prueba para verificar el funcionamiento completo del sistema.
"""

import requests
import json
from typing import Dict

API_BASE_URL = "http://localhost:8000"


def test_health_check():
    """Prueba el health check"""
    print("\n" + "=" * 70)
    print("🏥 TEST: Health Check")
    print("=" * 70)

    response = requests.get(f"{API_BASE_URL}/health")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {data['status']}")
        print(f"📦 Version: {data['version']}")
        print("Components:")
        for component, status in data["components"].items():
            print(f"   - {component}: {status}")
    else:
        print(f"❌ Error: {response.status_code}")

    return response.status_code == 200


def test_query(user_id: str, message: str, expected_intent: str = None) -> Dict:
    """Prueba una query específica"""
    print(f"\n{'=' * 70}")
    print(f"💬 TEST: Query")
    print(f"{'=' * 70}")
    print(f"User: {user_id}")
    print(f"Message: {message}")
    print("-" * 70)

    payload = {"user_id": user_id, "message": message}

    response = requests.post(f"{API_BASE_URL}/query", json=payload)

    if response.status_code == 200:
        data = response.json()

        status_icon = "✅" if data["success"] else "❌"
        print(f"{status_icon} Success: {data['success']}")
        print(
            f"🎯 Intent: {data['intent']} (confidence: {data.get('intent_confidence', 'N/A')})"
        )
        print(f"\n📝 Response:\n{data['response']}\n")

        if data.get("sources"):
            print(f"📚 Sources ({len(data['sources'])}):")
            for i, source in enumerate(data["sources"][:3], 1):
                print(f"   {i}. {source['file']} (score: {source['score']:.4f})")

        if data.get("tokens_used"):
            print(
                f"\n📊 Tokens: {data['tokens_used']} | Time: {data.get('processing_time', 0):.2f}s"
            )

        if expected_intent and data["intent"] != expected_intent:
            print(
                f"\n⚠️  WARNING: Expected intent '{expected_intent}', got '{data['intent']}'"
            )

        return data
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(response.text)
        return None


def test_stats():
    """Prueba el endpoint de estadísticas"""
    print("\n" + "=" * 70)
    print("📊 TEST: Stats")
    print("=" * 70)

    response = requests.get(f"{API_BASE_URL}/stats")

    if response.status_code == 200:
        data = response.json()
        print(f"Total queries: {data['total_queries']}")
        print(f"Success rate: {data['success_rate']}")
        print(f"Unique users: {data['unique_users']}")
        print("\nIntent distribution:")
        for intent, count in data["intent_distribution"].items():
            print(f"   - {intent}: {count}")
    else:
        print(f"❌ Error: {response.status_code}")


def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("\n" + "🧪 " + "=" * 66)
    print("  KNOWLIGO RAG CHATBOT - TEST SUITE")
    print("=" * 70 + "\n")

    try:
        # 1. Health check
        health_ok = test_health_check()
        if not health_ok:
            print("\n❌ Health check falló. Verifica que la API esté corriendo.")
            return

        # 2. Queries de prueba
        test_cases = [
            ("test_user_1", "¿Qué planes de soporte ofrecen?", "planes"),
            ("test_user_1", "¿Cuál es el SLA para tickets High?", "sla"),
            ("test_user_2", "Necesito ayuda con mi servidor", "tickets"),
            ("test_user_2", "¿Hacen mantenimiento preventivo?", "mantenimiento"),
            ("test_user_3", "¿Qué es KnowLigo?", "info_general"),
            ("test_user_3", "Dame consejos de hacking", "rejected"),  # Debe rechazar
            ("test_user_4", "¿Cuánto cuesta el plan Enterprise?", "planes"),
        ]

        print("\n" + "🎯 " + "=" * 66)
        print("  TESTING QUERIES")
        print("=" * 70)

        results = []
        for user_id, message, expected_intent in test_cases:
            result = test_query(user_id, message, expected_intent)
            results.append(result)

        # 3. Estadísticas
        test_stats()

        # 4. Resumen
        print("\n" + "📋 " + "=" * 66)
        print("  RESUMEN DE TESTS")
        print("=" * 70)

        successful = sum(1 for r in results if r and r.get("success"))
        total = len(results)

        print(f"\nTotal tests: {total}")
        print(f"Exitosos: {successful}")
        print(f"Fallidos: {total - successful}")
        print(f"Success rate: {successful / total * 100:.1f}%")

        print("\n" + "=" * 70)
        if successful == total:
            print("🎉 ¡TODOS LOS TESTS PASARON!")
        else:
            print("⚠️  ALGUNOS TESTS FALLARON")
        print("=" * 70 + "\n")

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se puede conectar a la API")
        print("Verifica que esté corriendo en http://localhost:8000")
        print("\nEjecuta: python api/main.py")
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")


if __name__ == "__main__":
    run_all_tests()
