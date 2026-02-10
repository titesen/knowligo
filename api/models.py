"""
Pydantic models para validación de requests/responses
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request para procesar una query"""

    user_id: str = Field(
        ..., description="ID del usuario (ej: número de teléfono)", min_length=1
    )
    message: str = Field(
        ..., description="Mensaje/pregunta del usuario", min_length=1, max_length=500
    )
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Historial opcional de conversación"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "+5491112345678",
                "message": "¿Qué planes de soporte ofrecen?",
                "conversation_history": None,
            }
        }


class SourceInfo(BaseModel):
    """Información de fuente de un chunk"""

    file: str = Field(..., description="Archivo fuente")
    section: str = Field(default="", description="Sección del documento")
    score: float = Field(..., description="Score de similitud")


class QueryResponse(BaseModel):
    """Response del procesamiento de una query"""

    success: bool = Field(..., description="Si la query fue procesada exitosamente")
    response: str = Field(..., description="Respuesta generada")
    intent: str = Field(..., description="Intención clasificada")
    intent_confidence: Optional[float] = Field(
        None, description="Confianza de la clasificación"
    )
    sources: Optional[List[SourceInfo]] = Field(None, description="Fuentes usadas")
    tokens_used: Optional[int] = Field(None, description="Tokens consumidos")
    processing_time: Optional[float] = Field(
        None, description="Tiempo de procesamiento en segundos"
    )
    error: Optional[str] = Field(None, description="Mensaje de error si falla")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "response": "KnowLigo ofrece tres planes: Basic ($199/mes), Professional ($499/mes) y Enterprise (personalizado).",
                "intent": "planes",
                "intent_confidence": 0.95,
                "sources": [{"file": "plans.md", "section": "Planes", "score": 0.23}],
                "tokens_used": 150,
                "processing_time": 1.25,
                "error": None,
            }
        }


class HealthResponse(BaseModel):
    """Response del health check"""

    status: str = Field(..., description="Estado del servicio")
    version: str = Field(..., description="Versión de la API")
    components: Dict[str, str] = Field(..., description="Estado de componentes")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "components": {"database": "ok", "faiss_index": "ok", "groq_api": "ok"},
            }
        }
