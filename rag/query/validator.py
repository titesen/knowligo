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
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


"""
- Patrones de Prompt Injection
- Detecta intentos de manipular el sistema vía instrucciones maliciosas.
- Incluye patrones en español e inglés para cobertura completa.
"""
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

        # 4. Query es válida — el filtrado de temas lo maneja el LLM router
        # (se eliminó el keyword-gating por ser demasiado restrictivo).
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
                logger.warning(
                    f"Prompt injection detectado: patrón '{pattern.pattern}'"
                )
                return True
        return False
