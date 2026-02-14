"""
Retriever - Recupera chunks relevantes del índice FAISS.

Este módulo:
1. Carga el índice FAISS y metadata de chunks
2. Genera embeddings para queries
3. Busca los chunks más similares
4. Retorna contexto relevante para el LLM
"""

import json
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    print("⚠️  Dependencias no instaladas. Ejecuta: pip install -r requirements.txt")
    exit(1)


# Modelo multilingüe por defecto (soporta español, inglés, y 50+ idiomas)
DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

logger = logging.getLogger(__name__)


class FAISSRetriever:
    """Recupera chunks relevantes usando búsqueda vectorial FAISS"""

    def __init__(
        self,
        index_path: str = None,
        metadata_path: str = None,
        model_name: str = None,
    ):
        """
        Inicializa el retriever con índice FAISS y modelo de embeddings.

        Args:
            index_path: Ruta al archivo .index de FAISS
            metadata_path: Ruta al JSON con metadata de chunks
            model_name: Modelo de sentence-transformers (default: multilingüe)
        """
        # Modelo de embeddings: parámetro > default
        if model_name is None:
            model_name = DEFAULT_EMBEDDING_MODEL

        # Rutas por defecto
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent

        if index_path is None or metadata_path is None:
            store_dir = project_root / "rag" / "store"

            if index_path is None:
                index_path = store_dir / "faiss.index"
            if metadata_path is None:
                metadata_path = store_dir / "metadata.json"

        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)

        # Cargar modelo de embeddings
        logger.info(f"Cargando modelo de embeddings: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

        # Cargar índice FAISS
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Índice FAISS no encontrado: {self.index_path}\n"
                "Ejecuta primero: python rag/ingest/build_index.py"
            )

        logger.info(f"Cargando índice FAISS desde: {self.index_path}")
        self.index = faiss.read_index(str(self.index_path))
        logger.info(f"Índice cargado ({self.index.ntotal} vectores)")

        # Cargar metadata de chunks desde pickle
        chunks_path = self.metadata_path.parent / "chunks.pkl"

        if not chunks_path.exists():
            raise FileNotFoundError(
                f"Chunks no encontrados: {chunks_path}\n"
                "Ejecuta primero: python rag/ingest/build_index.py"
            )

        with open(chunks_path, "rb") as f:
            self.chunks = pickle.load(f)

        if len(self.chunks) != self.index.ntotal:
            logger.warning(
                f"Número de chunks ({len(self.chunks)}) "
                f"no coincide con vectores en índice ({self.index.ntotal})"
            )
        else:
            logger.info(f"{len(self.chunks)} chunks cargados")

    def retrieve(
        self, query: str, top_k: int = 3, score_threshold: float = None
    ) -> List[Dict]:
        """
        Recupera los chunks más relevantes para una query.

        Args:
            query: Consulta del usuario
            top_k: Número de chunks a recuperar
            score_threshold: Umbral mínimo de similitud (opcional)

        Returns:
            Lista de diccionarios con:
            - text: texto del chunk
            - metadata: metadata original (source, section)
            - score: score de similitud (menor = más similar en L2)
        """
        # Generar embedding de la query
        query_embedding = self.model.encode([query], convert_to_numpy=True)

        # Buscar en FAISS
        distances, indices = self.index.search(query_embedding, top_k)

        # Construir resultados
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            # idx == -1 significa que no se encontró suficiente información
            if idx == -1:
                continue

            # Aplicar threshold si existe (menor distancia = mayor similitud)
            if score_threshold is not None and distance > score_threshold:
                continue

            # Obtener chunk
            if idx < len(self.chunks):
                chunk = self.chunks[idx]
                results.append(
                    {
                        "text": chunk.get("text", ""),
                        "metadata": chunk.get("metadata", {}),
                        "score": float(distance),
                        "rank": i + 1,
                    }
                )

        return results

    def format_context(self, results: List[Dict]) -> str:
        """
        Formatea los chunks recuperados en un contexto para el LLM.

        Args:
            results: Lista de chunks recuperados

        Returns:
            String formateado con el contexto
        """
        if not results:
            return "No se encontró información relevante en la base de conocimiento."

        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "documento")
            section = result["metadata"].get("section", "")
            text = result["text"]

            # Formato: [Fuente - Sección] Texto
            if section:
                context_parts.append(f"[{source} - {section}]\n{text}")
            else:
                context_parts.append(f"[{source}]\n{text}")

        return "\n\n".join(context_parts)
