"""
Retriever - Recupera chunks relevantes usando búsqueda vectorial y léxica.

Este módulo:
1. FAISSRetriever: búsqueda densa (embeddings) con FAISS
2. HybridRetriever: combina FAISS (denso) + BM25 (léxico) con RRF fusion
3. Retorna contexto relevante para el LLM
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

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None  # graceful degradation — hybrid falls back to dense-only


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


# Tokenización simple para BM25


def _tokenize_es(text: str) -> list[str]:
    """Tokenización simple para español — lowercase + split en no-alfanuméricos."""
    import re

    return re.findall(r"[a-záéíóúüñ0-9]+", text.lower())


# HybridRetriever  — Dense (FAISS) + Sparse (BM25) con RRF fusion


class HybridRetriever:
    """Combina FAISSRetriever (denso) con BM25 (léxico) usando Reciprocal Rank Fusion.

    Si ``rank_bm25`` no está instalado, funciona como proxy de FAISSRetriever.
    """

    def __init__(
        self,
        index_path: str = None,
        metadata_path: str = None,
        model_name: str = None,
        rrf_k: int = 60,
    ):
        # Inicializar retriever denso
        self.dense = FAISSRetriever(
            index_path=index_path,
            metadata_path=metadata_path,
            model_name=model_name,
        )

        # Exponer atributos que el pipeline usa
        self.model = self.dense.model
        self.model_name = self.dense.model_name
        self.chunks = self.dense.chunks

        self.rrf_k = rrf_k

        # Construir índice BM25 sobre los textos de los chunks
        if BM25Okapi is not None:
            corpus = [_tokenize_es(c.get("text", "")) for c in self.chunks]
            self.bm25 = BM25Okapi(corpus)
            logger.info(f"BM25 index construido ({len(corpus)} documentos)")
        else:
            self.bm25 = None
            logger.warning(
                "rank_bm25 no instalado — HybridRetriever opera solo en modo denso. "
                "Instalá con: pip install rank_bm25"
            )

    # retrieve

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = None,
        dense_query: str | None = None,
    ) -> List[Dict]:
        """Recupera chunks combinando FAISS + BM25.

        Args:
            query: Consulta original del usuario (se usa para BM25).
            top_k: Cantidad final de chunks a devolver.
            score_threshold: Umbral opcional para resultados densos.
            dense_query: Si se provee, se usa como query para la búsqueda densa
                (útil cuando hay query-rewriting / HyDE).
        """
        # Query para la búsqueda densa (podría ser la reescritura)
        dq = dense_query or query

        # Búsqueda densa — pedimos el doble de candidatos para RRF
        dense_results = self.dense.retrieve(
            dq, top_k=top_k * 2, score_threshold=score_threshold
        )

        if self.bm25 is None:
            # Sin BM25 → devolver solo denso, truncado a top_k
            return dense_results[:top_k]

        # Búsqueda BM25
        tokenized_query = _tokenize_es(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_top_indices = np.argsort(bm25_scores)[::-1][: top_k * 2]

        bm25_results = []
        for rank, idx in enumerate(bm25_top_indices):
            idx = int(idx)
            if bm25_scores[idx] <= 0:
                break
            chunk = self.chunks[idx]
            bm25_results.append(
                {
                    "text": chunk.get("text", ""),
                    "metadata": chunk.get("metadata", {}),
                    "score": float(bm25_scores[idx]),
                    "rank": rank + 1,
                    "_idx": idx,
                }
            )

        # Mapear dense_results a _idx para RRF
        # (no tenemos _idx nativo, así que buscamos por texto)
        dense_text_to_rank: dict[str, int] = {}
        for r in dense_results:
            dense_text_to_rank[r["text"]] = r["rank"]

        bm25_text_to_rank: dict[str, int] = {}
        for r in bm25_results:
            bm25_text_to_rank[r["text"]] = r["rank"]

        # Unión de todos los textos vistos
        all_texts = set(dense_text_to_rank.keys()) | set(bm25_text_to_rank.keys())

        # RRF fusion
        k = self.rrf_k
        scored: list[tuple[str, float]] = []
        for text in all_texts:
            rrf_score = 0.0
            if text in dense_text_to_rank:
                rrf_score += 1.0 / (k + dense_text_to_rank[text])
            if text in bm25_text_to_rank:
                rrf_score += 1.0 / (k + bm25_text_to_rank[text])
            scored.append((text, rrf_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Construir resultados finales
        # Lookup rápido de metadata
        text_to_meta: dict[str, dict] = {}
        for r in dense_results + bm25_results:
            if r["text"] not in text_to_meta:
                text_to_meta[r["text"]] = r["metadata"]

        final: list[dict] = []
        for rank, (text, rrf_score) in enumerate(scored[:top_k], 1):
            final.append(
                {
                    "text": text,
                    "metadata": text_to_meta.get(text, {}),
                    "score": rrf_score,
                    "rank": rank,
                }
            )

        logger.info(
            f"Hybrid retrieve: {len(dense_results)} dense + "
            f"{len(bm25_results)} BM25 → {len(final)} RRF-fused"
        )
        return final

    def format_context(self, results: List[Dict]) -> str:
        """Proxy a FAISSRetriever.format_context."""
        return self.dense.format_context(results)
