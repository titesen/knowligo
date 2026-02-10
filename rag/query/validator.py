"""
Validator - Valida que las consultas estén dentro del dominio permitido.

Este módulo:
1. Carga topics permitidos y prohibidos desde metadata
2. Valida si una query es relevante al negocio
3. Rechaza queries fuera de tópico o inapropiadas
"""

import json
from pathlib import Path
from typing import Tuple


class QueryValidator:
    """Valida queries contra topics permitidos y prohibidos"""

    def __init__(self, metadata_path: str = None):
        """
        Inicializa el validador con metadata.

        Args:
            metadata_path: Ruta al JSON de metadata. Si es None, usa knowledge/metadata.json
        """
        if metadata_path is None:
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent.parent
            metadata_path = project_root / "knowledge" / "metadata.json"
        else:
            metadata_path = Path(metadata_path)

        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata no encontrada: {metadata_path}")

        with open(metadata_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        self.allowed_topics = self.metadata.get("allowed_topics", [])
        self.forbidden_topics = self.metadata.get("forbidden_topics", [])
        self.domain = self.metadata.get("domain", "IT Support Services")

    def is_valid_query(self, query: str) -> Tuple[bool, str]:
        """
        Valida si una query es apropiada para el chatbot.

        Args:
            query: Consulta del usuario

        Returns:
            Tuple de (is_valid: bool, reason: str)
            - Si es válida: (True, "")
            - Si es inválida: (False, "razón del rechazo")
        """
        query_lower = query.lower()

        # 1. Verificar que no esté vacía
        if not query.strip():
            return False, "La consulta está vacía"

        # 2. Verificar que no contenga topics prohibidos
        for forbidden in self.forbidden_topics:
            keywords = forbidden.lower().split()
            if any(keyword in query_lower for keyword in keywords):
                return (
                    False,
                    f"Lo siento, no puedo ayudar con consultas sobre {forbidden}. "
                    f"Me especializo en {self.domain}.",
                )

        # 3. Verificar que contenga algún topic permitido
        # Keywords relacionados a cada topic permitido
        topic_keywords = {
            "support": [
                "soporte",
                "ayuda",
                "asistencia",
                "problema",
                "issue",
                "support",
                "help",
            ],
            "plans": [
                "plan",
                "planes",
                "paquete",
                "servicio",
                "tier",
                "basic",
                "professional",
                "enterprise",
            ],
            "sla": [
                "sla",
                "tiempo",
                "respuesta",
                "prioridad",
                "urgente",
                "critical",
                "high",
                "medium",
                "low",
            ],
            "tickets": ["ticket", "incidente", "caso", "reporte", "solicitud"],
            "maintenance": [
                "mantenimiento",
                "preventivo",
                "actualizacion",
                "backup",
                "maintenance",
                "update",
            ],
        }

        # Verificar si algún keyword de topics permitidos está presente
        contains_allowed_topic = False
        for topic in self.allowed_topics:
            if topic in topic_keywords:
                keywords = topic_keywords[topic]
                if any(keyword in query_lower for keyword in keywords):
                    contains_allowed_topic = True
                    break

        # También permitir preguntas generales sobre la empresa
        general_keywords = [
            "knowligo",
            "empresa",
            "compañía",
            "servicio",
            "ofrecen",
            "hacen",
            "que es",
            "quienes",
        ]
        if any(keyword in query_lower for keyword in general_keywords):
            contains_allowed_topic = True

        if not contains_allowed_topic:
            return (
                False,
                f"Lo siento, solo puedo responder preguntas sobre {self.domain}. "
                f"Puedo ayudarte con: planes de servicio, SLA, tickets de soporte y mantenimiento.",
            )

        # 4. Query es válida
        return True, ""


# Funciones de conveniencia
_validator_instance = None


def get_validator() -> QueryValidator:
    """Obtiene una instancia singleton del validador"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = QueryValidator()
    return _validator_instance


def validate_query(query: str) -> Tuple[bool, str]:
    """
    Función de conveniencia para validar una query.

    Args:
        query: Consulta a validar

    Returns:
        Tuple de (is_valid, reason)
    """
    validator = get_validator()
    return validator.is_valid_query(query)


# Script de prueba
if __name__ == "__main__":
    print("🔍 Testing Query Validator\n")

    test_queries = [
        ("¿Qué planes de soporte ofrecen?", True),
        ("¿Cuál es el SLA para tickets High?", True),
        ("Necesito ayuda con mi servidor", True),
        ("Dame consejos de hacking", False),
        ("¿Cuál es tu opinión política?", False),
        ("¿Puedes recomendarme un celular?", False),
        ("¿Qué es KnowLigo?", True),
        ("¿Hacen mantenimiento preventivo?", True),
    ]

    validator = QueryValidator()

    for query, expected_valid in test_queries:
        is_valid, reason = validator.is_valid_query(query)
        status = "✅" if is_valid == expected_valid else "❌"

        print(f"{status} Query: '{query}'")
        print(f"   Valid: {is_valid}")
        if not is_valid:
            print(f"   Reason: {reason}")
        print()
