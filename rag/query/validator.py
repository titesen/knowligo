"""
Validator - Valida que las consultas estén dentro del dominio permitido.

Este módulo:
1. Detecta intentos de prompt injection
2. Carga topics permitidos y prohibidos desde metadata
3. Valida si una query es relevante al negocio
4. Rechaza queries fuera de tópico o inapropiadas
"""

import re
import json
from pathlib import Path
from typing import Tuple


# ============================================================================
# Patrones de Prompt Injection
# Detecta intentos de manipular el sistema vía instrucciones maliciosas.
# Incluye patrones en español e inglés para cobertura completa.
# ============================================================================
INJECTION_PATTERNS = [
    # Intentos de override de instrucciones
    r"ignor[ae]\s+(todas?\s+las?\s+)?instrucciones",
    r"ignore\s+(all\s+)?(previous\s+)?instructions",
    r"olvida\s+(todas?\s+las?\s+)?instrucciones",
    r"forget\s+(all\s+)?(previous\s+)?instructions",
    r"descarta\s+(el\s+)?prompt\s+anterior",
    r"override\s+(system|prompt|instructions)",
    # Intentos de cambiar el rol del sistema
    r"ahora\s+(eres|act[uú]a\s+como|pretende\s+ser)",
    r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are))",
    r"nuevo\s+rol|new\s+role|cambia\s+(tu\s+)?rol",
    r"eres\s+un\s+(hacker|asistente\s+sin\s+restricciones)",
    # DAN / jailbreak comunes
    r"\bdan\s+mode\b",
    r"\bjailbreak\b",
    r"modo\s+sin\s+(restricciones|l[ií]mites|filtros)",
    r"sin\s+restricciones",
    r"do\s+anything\s+now",
    # Intentos de extraer prompt del sistema
    r"(muestra|dime|revela|comparte|repite)\s+(el|tu|the)\s+(prompt|system|instrucciones)",
    r"(show|reveal|print|repeat|display)\s+(your\s+)?(system\s+)?(prompt|instructions)",
    r"cu[aá]l\s+es\s+tu\s+(prompt|instrucciones\s+del\s+sistema)",
    r"what\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions)",
    # Inyección de delimitadores / tokens especiales
    r"<\|?(system|im_start|im_end|endoftext)\|?>",
    r"\[INST\]|\[/INST\]|\[SYSTEM\]",
    r"###\s*(system|instruction|human|assistant)",
    # Encoding/obfuscation attempts
    r"base64|rot13|hex\s+encode|unicode\s+escape",
    r"codifica|decodifica|encripta",
]

# Pre-compilar patrones para rendimiento
_COMPILED_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS
]


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

        # 2. Detectar prompt injection
        injection_detected = self._check_prompt_injection(query_lower)
        if injection_detected:
            return (
                False,
                "Lo siento, no puedo procesar esa consulta. "
                "¿Puedo ayudarte con información sobre los servicios de KnowLigo?",
            )

        # 3. Verificar que no contenga topics prohibidos (coincidencia de frase completa)
        for forbidden in self.forbidden_topics:
            forbidden_lower = forbidden.lower()
            if forbidden_lower in query_lower:
                return (
                    False,
                    f"Lo siento, no puedo ayudar con consultas sobre {forbidden}. "
                    f"Me especializo en {self.domain}.",
                )

        # 4. Verificar que contenga algún topic permitido
        # Keywords relacionados a cada topic permitido
        topic_keywords = {
            "support": [
                "soporte",
                "ayuda",
                "asistencia",
                "problema",
                "incidencia",
                "support",
                "help",
                "técnico",
                "remoto",
                "presencial",
            ],
            "plans": [
                "plan",
                "planes",
                "paquete",
                "servicio",
                "básico",
                "profesional",
                "empresarial",
                "precio",
                "costo",
                "cuánto",
                "cuanto",
                "contratar",
                "cotización",
            ],
            "sla": [
                "sla",
                "tiempo",
                "respuesta",
                "resolución",
                "prioridad",
                "urgente",
                "crítica",
                "alta",
                "media",
                "baja",
                "disponibilidad",
                "compensación",
            ],
            "tickets": [
                "ticket",
                "incidente",
                "caso",
                "reporte",
                "solicitud",
                "reclamo",
                "queja",
                "reportar",
                "estado",
            ],
            "maintenance": [
                "mantenimiento",
                "preventivo",
                "actualización",
                "backup",
                "respaldo",
                "maintenance",
                "update",
                "monitoreo",
            ],
            "company": [
                "knowligo",
                "empresa",
                "compañía",
                "equipo",
                "oficina",
                "contacto",
                "teléfono",
                "email",
                "dirección",
                "horario",
                "quiénes",
                "quienes",
            ],
            "billing": [
                "factura",
                "facturación",
                "pago",
                "cobro",
                "mora",
                "precio",
                "ajuste",
                "cancelar",
                "cancelación",
            ],
            "policies": [
                "política",
                "políticas",
                "privacidad",
                "datos",
                "confidencialidad",
                "exclusión",
                "exclusiones",
                "condiciones",
                "términos",
            ],
            "backup": [
                "backup",
                "respaldo",
                "veeam",
                "restauración",
                "recuperación",
                "drp",
                "desastre",
            ],
            "security_services": [
                "seguridad",
                "antivirus",
                "firewall",
                "ssl",
                "certificado",
                "vpn",
                "ransomware",
                "protección",
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

        # Permitir saludos y frases cortas de cortesía
        greeting_keywords = [
            "hola",
            "hello",
            "hi",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "buen día",
            "qué tal",
            "cómo estás",
            "ayuda",
            "ayudar",
            "me puedes",
            "puedes ayudar",
            "necesito ayuda",
            "gracias",
            "info",
            "información",
        ]
        if any(keyword in query_lower for keyword in greeting_keywords):
            contains_allowed_topic = True

        if not contains_allowed_topic:
            return (
                False,
                f"Lo siento, solo puedo responder preguntas sobre los servicios de KnowLigo. "
                f"Puedo ayudarte con: planes de servicio, precios, SLA, tickets de soporte, "
                f"mantenimiento, backup, políticas y facturación.",
            )

        # 5. Query es válida
        return True, ""

    def _check_prompt_injection(self, query_lower: str) -> bool:
        """
        Detecta intentos de prompt injection en la query.

        Usa patrones regex pre-compilados para detectar técnicas comunes
        de inyección en español e inglés.

        Args:
            query_lower: Query en minúsculas

        Returns:
            True si se detectó inyección, False si es segura
        """
        for pattern in _COMPILED_INJECTION_PATTERNS:
            if pattern.search(query_lower):
                print(f"⚠️  Prompt injection detectado: patrón '{pattern.pattern}'")
                return True
        return False


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
