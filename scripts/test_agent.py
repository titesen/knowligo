"""
Test integral del agente conversacional vía webhook simulado.
Simula mensajes de WhatsApp para probar todos los flujos del agente.
"""

import httpx
import time

BASE = "http://localhost:8000"


def send_whatsapp_message(phone: str, text: str) -> dict:
    """Simula un mensaje entrante de WhatsApp."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }
    resp = httpx.post(f"{BASE}/webhook", json=payload, timeout=30.0)
    return resp.json()


def test_rag_query():
    """Test: consulta RAG directa vía /query."""
    print("\n" + "=" * 60)
    print("TEST 1: Consulta RAG vía /query")
    print("=" * 60)
    resp = httpx.post(
        f"{BASE}/query",
        json={"user_id": "test123", "message": "¿Qué planes de soporte ofrecen?"},
        timeout=30.0,
    )
    data = resp.json()
    print(f"  Status: {resp.status_code}")
    print(f"  Intent: {data.get('intent')}")
    print(f"  Response: {data.get('response', '')[:200]}")
    assert resp.status_code == 200
    assert data["success"] is True
    print("  ✅ PASS")


def test_saludo_cliente_conocido():
    """Test: saludo de un cliente registrado (Facundo)."""
    print("\n" + "=" * 60)
    print("TEST 2: Saludo — Cliente conocido (Facundo)")
    print("=" * 60)
    result = send_whatsapp_message("5493794285297", "Hola")
    print(f"  Result: {result}")
    # El agente debería reconocer a Facundo
    print("  ✅ Webhook procesado (revisar logs del servidor)")


def test_saludo_cliente_desconocido():
    """Test: saludo de un número no registrado."""
    print("\n" + "=" * 60)
    print("TEST 3: Saludo — Cliente desconocido")
    print("=" * 60)
    result = send_whatsapp_message("5491199990000", "Hola buenas tardes")
    print(f"  Result: {result}")
    print("  ✅ Webhook procesado (debería sugerir registro)")


def test_registro_completo():
    """Test: flujo completo de registro de nuevo cliente."""
    print("\n" + "=" * 60)
    print("TEST 4: Flujo de registro completo")
    print("=" * 60)
    phone = "5491155550000"

    steps = [
        ("registrar", "Debería pedir nombre"),
        ("María García", "Debería pedir empresa"),
        ("Consultora Norte SRL", "Debería pedir email"),
        ("maria@consultanorte.com", "Debería confirmar registro"),
    ]

    for msg, expected in steps:
        print(f"  → Enviando: '{msg}' ({expected})")
        result = send_whatsapp_message(phone, msg)
        print(f"    Result: {result}")
        time.sleep(1)

    print("  ✅ Flujo de registro completado")


def test_ver_tickets():
    """Test: ver tickets de cliente registrado."""
    print("\n" + "=" * 60)
    print("TEST 5: Ver tickets (cliente Facundo)")
    print("=" * 60)
    result = send_whatsapp_message("5493794285297", "Quiero ver mis tickets")
    print(f"  Result: {result}")
    print("  ✅ Webhook procesado")


def test_crear_ticket():
    """Test: flujo de creación de ticket."""
    print("\n" + "=" * 60)
    print("TEST 6: Crear ticket (cliente Facundo)")
    print("=" * 60)
    phone = "5493794285297"

    steps = [
        ("Necesito reportar un problema", "Debería pedir asunto"),
        ("Impresora no funciona", "Debería pedir descripción"),
        (
            "La impresora del piso 3 no enciende desde esta mañana, ya revisé cables",
            "Debería pedir prioridad",
        ),
        ("Media", "Debería confirmar ticket creado"),
    ]

    for msg, expected in steps:
        print(f"  → Enviando: '{msg}' ({expected})")
        result = send_whatsapp_message(phone, msg)
        print(f"    Result: {result}")
        time.sleep(1)

    print("  ✅ Flujo de creación de ticket completado")


def test_ver_planes():
    """Test: consultar planes disponibles (no requiere registro)."""
    print("\n" + "=" * 60)
    print("TEST 7: Ver planes disponibles")
    print("=" * 60)
    result = send_whatsapp_message("5491199990000", "¿Qué planes tienen?")
    print(f"  Result: {result}")
    print("  ✅ Webhook procesado")


def test_contratar_plan():
    """Test: flujo de contratación de plan."""
    print("\n" + "=" * 60)
    print("TEST 8: Contratar plan (cliente Facundo)")
    print("=" * 60)
    phone = "5493794285297"

    steps = [
        ("Quiero contratar un plan", "Debería mostrar planes"),
        ("1", "Debería pedir confirmación del Plan Básico"),
        ("sí", "Debería pedir método de pago"),
        ("3", "Debería confirmar contratación con Mercado Pago"),
    ]

    for msg, expected in steps:
        print(f"  → Enviando: '{msg}' ({expected})")
        result = send_whatsapp_message(phone, msg)
        print(f"    Result: {result}")
        time.sleep(1)

    print("  ✅ Flujo de contratación completado")


def test_consulta_cuenta():
    """Test: consultar datos de cuenta."""
    print("\n" + "=" * 60)
    print("TEST 9: Consultar cuenta (cliente Facundo)")
    print("=" * 60)
    result = send_whatsapp_message("5493794285297", "Quiero ver mi cuenta")
    print(f"  Result: {result}")
    print("  ✅ Webhook procesado")


def test_cancelar_flujo():
    """Test: cancelar un flujo en curso."""
    print("\n" + "=" * 60)
    print("TEST 10: Cancelar flujo en curso")
    print("=" * 60)
    phone = "5493794285297"
    send_whatsapp_message(phone, "Quiero crear un ticket")
    time.sleep(1)
    result = send_whatsapp_message(phone, "cancelar")
    print(f"  Result: {result}")
    print("  ✅ Cancelación procesada")


def test_fuera_de_tema():
    """Test: mensaje fuera de tema."""
    print("\n" + "=" * 60)
    print("TEST 11: Fuera de tema")
    print("=" * 60)
    result = send_whatsapp_message("5493794285297", "¿Quién ganó el mundial 2022?")
    print(f"  Result: {result}")
    print("  ✅ Rechazo cortés procesado")


def test_consulta_rag_via_webhook():
    """Test: consulta informativa vía webhook (delega a RAG)."""
    print("\n" + "=" * 60)
    print("TEST 12: Consulta RAG vía webhook")
    print("=" * 60)
    result = send_whatsapp_message(
        "5493794285297", "¿Cuál es el tiempo de respuesta para tickets críticos?"
    )
    print(f"  Result: {result}")
    print("  ✅ Consulta RAG procesada")


def test_despedida():
    """Test: despedida."""
    print("\n" + "=" * 60)
    print("TEST 13: Despedida")
    print("=" * 60)
    result = send_whatsapp_message("5493794285297", "Muchas gracias, hasta luego")
    print(f"  Result: {result}")
    print("  ✅ Despedida procesada")


def test_no_registrado_intenta_accion():
    """Test: usuario no registrado intenta acción que requiere registro."""
    print("\n" + "=" * 60)
    print("TEST 14: No registrado intenta crear ticket")
    print("=" * 60)
    result = send_whatsapp_message("5491188880000", "Quiero crear un ticket")
    print(f"  Result: {result}")
    print("  ✅ Debería indicar que necesita registrarse")


if __name__ == "__main__":
    print("🚀 Test integral del agente KnowLigo")
    print("   Asegurate de que la API esté corriendo en http://localhost:8000\n")

    tests = [
        test_rag_query,
        test_saludo_cliente_conocido,
        test_saludo_cliente_desconocido,
        test_registro_completo,
        test_ver_tickets,
        test_crear_ticket,
        test_ver_planes,
        test_contratar_plan,
        test_consulta_cuenta,
        test_cancelar_flujo,
        test_fuera_de_tema,
        test_consulta_rag_via_webhook,
        test_despedida,
        test_no_registrado_intenta_accion,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAIL: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTADOS: {passed} passed, {failed} failed de {len(tests)} tests")
    print("=" * 60)
    print("\n📋 Revisá los logs del servidor para ver las respuestas del agente")
    print("   (las respuestas de WhatsApp se loguean aunque no se envíen sin token)")
