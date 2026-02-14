"""
Reranker - Reordena chunks usando un Cross-Encoder multilingüe.

Este módulo implementa reranking semántico:
1. Recibe candidatos del retriever (búsqueda vectorial rápida)
2. Los re-evalúa con un Cross-Encoder más preciso (query, chunk) pairs
3. Retorna los top-N chunks según relevancia real

El Cross-Encoder analiza la relación directa entre query y cada chunk,
ofreciendo mayor precisión que la búsqueda vectorial por similitud coseno.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Modelo cross-encoder por defecto
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    """Reranker basado en Cross-Encoder para mejorar la precisión del retrieval."""

    def __init__(self, model_name: str = None, top_n: int = None):
        """
        Inicializa el Cross-Encoder reranker.

        Args:
            model_name: Modelo de cross-encoder
            top_n: Cantidad de chunks a retornar después del reranking
        """
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            raise ImportError(
                "sentence-transformers es requerido para reranking. "
                "Ejecuta: pip install sentence-transformers"
            )

        # Modelo: parámetro > default
        if model_name is None:
            model_name = DEFAULT_RERANK_MODEL

        # Top-N: parámetro > default 5
        if top_n is None:
            top_n = 5

        self.top_n = top_n
        self.model_name = model_name

        logger.info(f"Cargando Cross-Encoder: {model_name}")
        self.model = CrossEncoder(model_name)
        logger.info(f"Cross-Encoder cargado (top_n={self.top_n})")

    def rerank(self, query: str, chunks: List[Dict], top_n: int = None) -> List[Dict]:
        """
        Reordena chunks según relevancia real usando Cross-Encoder.

        Args:
            query: Pregunta del usuario
            chunks: Lista de chunks del retriever (cada uno con 'text', 'score', 'metadata')
            top_n: Override del número de chunks a retornar

        Returns:
            Lista de chunks reordenados con score actualizado
        """
        if not chunks:
            return []

        top_n = top_n or self.top_n

        # Preparar pares (query, chunk_text) para el cross-encoder
        pairs = [(query, chunk["text"]) for chunk in chunks]

        # Obtener scores del cross-encoder
        scores = self.model.predict(pairs)

        # Asignar scores y ordenar
        reranked = []
        for i, chunk in enumerate(chunks):
            reranked_chunk = chunk.copy()
            reranked_chunk["rerank_score"] = float(scores[i])
            reranked_chunk["original_score"] = chunk.get("score", 0.0)
            reranked.append(reranked_chunk)

        # Ordenar por rerank_score descendente (mayor = más relevante)
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Retornar solo top_n
        result = reranked[:top_n]

        # Actualizar score principal con el rerank_score normalizado
        if result:
            max_score = max(c["rerank_score"] for c in result)
            min_score = min(c["rerank_score"] for c in result)
            score_range = max_score - min_score if max_score != min_score else 1.0

            for chunk in result:
                # Normalizar score a [0, 1]
                chunk["score"] = (chunk["rerank_score"] - min_score) / score_range

        return result
