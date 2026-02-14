"""
Tests para el clasificador de intenciones.

Cubre:
- Clasificación correcta de cada tipo de intent
- Query sin intención clara → UNKNOWN
- Confianza proporcional al número de keywords
"""

import pytest
from rag.query.intent import IntentClassifier, Intent


@pytest.fixture
def classifier():
    """Instancia del clasificador."""
    return IntentClassifier()


class TestIntentClassification:
    """Clasificación correcta por categoría."""

    def test_intent_planes(self, classifier):
        result = classifier.classify("¿Cuánto cuesta el plan Enterprise?")
        assert result["intent"] == Intent.PLANES
        assert result["confidence"] > 0

    def test_intent_sla(self, classifier):
        result = classifier.classify(
            "¿Cuál es el tiempo de respuesta para prioridad alta?"
        )
        assert result["intent"] == Intent.SLA

    def test_intent_tickets(self, classifier):
        result = classifier.classify("Necesito abrir un ticket de incidente urgente")
        assert result["intent"] == Intent.TICKETS

    def test_intent_mantenimiento(self, classifier):
        result = classifier.classify("¿Realizan mantenimiento preventivo y backup?")
        assert result["intent"] == Intent.MANTENIMIENTO

    def test_intent_info_general(self, classifier):
        result = classifier.classify("¿Qué es KnowLigo y dónde está la empresa?")
        assert result["intent"] == Intent.INFO_GENERAL

    def test_intent_unknown(self, classifier):
        result = classifier.classify("asdfghjkl random text")
        assert result["intent"] == Intent.UNKNOWN
        assert result["confidence"] == 0.0

    def test_confidence_multiple_keywords(self, classifier):
        """Más keywords = más confianza."""
        result_1kw = classifier.classify("plan")
        result_3kw = classifier.classify("plan precio enterprise cuanto cuesta")
        assert result_3kw["confidence"] >= result_1kw["confidence"]

    def test_matched_keywords_returned(self, classifier):
        result = classifier.classify("¿Cuánto cuesta el plan Enterprise?")
        assert len(result["matched_keywords"]) > 0
        assert isinstance(result["matched_keywords"], list)
