"""
Intent Classifier - Clasifica la intención de las consultas.

Este módulo:
1. Analiza el tipo de consulta del usuario
2. Clasifica en categorías (info, planes, sla, tickets, etc.)
3. Ayuda a enrutar y registrar analytics
"""

from typing import Dict
from enum import Enum


class Intent(str, Enum):
    """Tipos de intención de consultas"""

    INFO_GENERAL = "info_general"  # Preguntas sobre la empresa
    PLANES = "planes"  # Consultas sobre planes/pricing
    SLA = "sla"  # Preguntas sobre SLA/tiempos
    TICKETS = "tickets"  # Gestión de tickets
    MANTENIMIENTO = "mantenimiento"  # Mantenimiento preventivo
    FAQ = "faq"  # Preguntas frecuentes
    UNKNOWN = "unknown"  # No clasificado


class IntentClassifier:
    """Clasifica la intención de queries usando keyword matching"""

    def __init__(self):
        """Inicializa el clasificador con patrones de keywords"""

        # Keywords para cada tipo de intención
        self.intent_patterns = {
            Intent.PLANES: [
                "plan",
                "planes",
                "precio",
                "costo",
                "paquete",
                "tier",
                "basic",
                "professional",
                "enterprise",
                "cuanto cuesta",
                "contratar",
                "servicio",
                "ofrecen",
            ],
            Intent.SLA: [
                "sla",
                "tiempo",
                "respuesta",
                "cuanto tarda",
                "cuando",
                "prioridad",
                "urgente",
                "critical",
                "high",
                "medium",
                "low",
                "horario",
                "disponibilidad",
            ],
            Intent.TICKETS: [
                "ticket",
                "incidente",
                "problema",
                "issue",
                "reporte",
                "solicitud",
                "caso",
                "abrir ticket",
                "crear ticket",
                "estado",
                "seguimiento",
            ],
            Intent.MANTENIMIENTO: [
                "mantenimiento",
                "preventivo",
                "actualizacion",
                "backup",
                "maintenance",
                "update",
                "parche",
                "patch",
                "monitoreo",
            ],
            Intent.FAQ: [
                "como",
                "donde",
                "cuando",
                "porque",
                "que es",
                "puedo",
                "debo",
                "necesito",
                "requisito",
                "incluye",
            ],
            Intent.INFO_GENERAL: [
                "knowligo",
                "empresa",
                "compañía",
                "quienes son",
                "que hacen",
                "sobre",
                "contacto",
                "ubicacion",
            ],
        }

    def classify(self, query: str) -> Dict[str, any]:
        """
        Clasifica la intención de una query.

        Args:
            query: Consulta del usuario

        Returns:
            Dict con:
            - intent: Intent enum
            - confidence: float (0-1) basado en matches
            - matched_keywords: lista de keywords que matchearon
        """
        query_lower = query.lower()

        # Contar matches por intención
        intent_scores = {}
        intent_matches = {}

        for intent, keywords in self.intent_patterns.items():
            matches = [kw for kw in keywords if kw in query_lower]
            if matches:
                intent_scores[intent] = len(matches)
                intent_matches[intent] = matches

        # Si no hay matches, retornar UNKNOWN
        if not intent_scores:
            return {"intent": Intent.UNKNOWN, "confidence": 0.0, "matched_keywords": []}

        # Obtener la intención con más matches
        best_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[best_intent]

        # Calcular confidence normalizado (simple heuristic)
        # Más keywords = más confianza, pero cap en 1.0
        confidence = min(max_score / 3.0, 1.0)

        return {
            "intent": best_intent,
            "confidence": confidence,
            "matched_keywords": intent_matches[best_intent],
        }


# Instancia singleton
_classifier_instance = None


def get_classifier() -> IntentClassifier:
    """Obtiene una instancia singleton del clasificador"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance


def classify_intent(query: str) -> Dict[str, any]:
    """
    Función de conveniencia para clasificar intención.

    Args:
        query: Consulta a clasificar

    Returns:
        Dict con intent, confidence, matched_keywords
    """
    classifier = get_classifier()
    return classifier.classify(query)


# Script de prueba
if __name__ == "__main__":
    print("🎯 Testing Intent Classifier\n")

    test_queries = [
        "¿Qué planes de soporte ofrecen?",
        "¿Cuál es el SLA para tickets High?",
        "Necesito abrir un ticket urgente",
        "¿Hacen mantenimiento preventivo?",
        "¿Qué es KnowLigo?",
        "¿Cuánto cuesta el plan Enterprise?",
        "¿Cuánto tiempo tardan en responder?",
        "¿Cómo puedo contactarlos?",
    ]

    classifier = IntentClassifier()

    for query in test_queries:
        result = classifier.classify(query)

        confidence_bar = "█" * int(result["confidence"] * 10)

        print(f"Query: '{query}'")
        print(f"  Intent: {result['intent'].value}")
        print(f"  Confidence: {result['confidence']:.2f} {confidence_bar}")
        print(f"  Keywords: {', '.join(result['matched_keywords'])}")
        print()
