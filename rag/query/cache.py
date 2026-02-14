"""
Semantic Cache - Caché inteligente basado en similitud semántica.

Este módulo implementa:
1. Cache en memoria usando embeddings + FAISS para lookup rápido
2. Búsqueda por similitud semántica (no exact-match)
3. TTL (Time-To-Live) configurable para expiración automática
4. Límite de tamaño con eviction LRU

Si una query nueva es semánticamente similar (>= threshold) a una
query cacheada, retorna la respuesta cacheada sin pasar por el pipeline.
"""

import os
import time
from pathlib import Path
from typing import Dict, Optional
import numpy as np
from dotenv import load_dotenv

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    print("⚠️  Dependencias no instaladas para cache semántico.")

# Cargar .env
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class SemanticCache:
    """Cache semántico en memoria con búsqueda por similitud vectorial."""

    def __init__(
        self,
        model: SentenceTransformer = None,
        threshold: float = None,
        ttl_seconds: int = None,
        max_size: int = None,
    ):
        """
        Inicializa el cache semántico.

        Args:
            model: Modelo de embeddings (reutiliza el del retriever para eficiencia)
            threshold: Umbral de similitud coseno para considerar un cache hit [0-1]
            ttl_seconds: Tiempo de vida de cada entrada en segundos
            max_size: Número máximo de entradas en cache
        """
        # Config desde env con defaults sensatos
        if threshold is None:
            threshold = float(os.getenv("CACHE_THRESHOLD", "0.92"))
        if ttl_seconds is None:
            ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        if max_size is None:
            max_size = int(os.getenv("CACHE_MAX_SIZE", "100"))

        self.threshold = threshold
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.model = model

        # Almacenamiento interno
        self._entries: list[Dict] = []  # Lista ordenada por tiempo de acceso
        self._index: Optional[faiss.IndexFlatIP] = None  # Inner Product para coseno
        self._dimension: Optional[int] = None

        # Stats
        self.hits = 0
        self.misses = 0

        print(
            f"🗄️  Cache semántico inicializado "
            f"(threshold={self.threshold}, ttl={self.ttl_seconds}s, max={self.max_size})"
        )

    def _ensure_model(self):
        """Carga el modelo de embeddings si no fue proporcionado."""
        if self.model is None:
            from .retriever import FAISSRetriever

            # Reutilizar el singleton del retriever
            retriever = FAISSRetriever()
            self.model = retriever.model

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """Normaliza vectores para similitud coseno vía Inner Product."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Evitar div by zero
        return vectors / norms

    def _rebuild_index(self):
        """Reconstruye el índice FAISS desde las entradas actuales."""
        if not self._entries or self._dimension is None:
            self._index = None
            return

        embeddings = np.array(
            [entry["embedding"] for entry in self._entries], dtype=np.float32
        )
        embeddings = self._normalize(embeddings)

        self._index = faiss.IndexFlatIP(self._dimension)
        self._index.add(embeddings)

    def _evict_expired(self):
        """Elimina entradas expiradas por TTL."""
        now = time.time()
        original_count = len(self._entries)

        self._entries = [
            entry
            for entry in self._entries
            if (now - entry["timestamp"]) < self.ttl_seconds
        ]

        if len(self._entries) < original_count:
            self._rebuild_index()

    def _evict_lru(self):
        """Elimina la entrada menos recientemente usada si se excede max_size."""
        if len(self._entries) > self.max_size:
            # Ordenar por last_access y eliminar el más antiguo
            self._entries.sort(key=lambda x: x["last_access"])
            self._entries = self._entries[-self.max_size :]
            self._rebuild_index()

    def lookup(self, query: str) -> Optional[Dict]:
        """
        Busca una respuesta cacheada semánticamente similar a la query.

        Args:
            query: Pregunta del usuario

        Returns:
            Dict con la respuesta cacheada si hay hit, None si miss
        """
        if not self._entries or self._index is None:
            self.misses += 1
            return None

        # Limpiar entradas expiradas primero
        self._evict_expired()

        if not self._entries:
            self.misses += 1
            return None

        self._ensure_model()

        # Generar embedding de la query
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        query_embedding = self._normalize(query_embedding.astype(np.float32))

        # Buscar en el índice FAISS (Inner Product = cosine similarity con vectores normalizados)
        scores, indices = self._index.search(query_embedding, 1)

        best_score = float(scores[0][0])
        best_idx = int(indices[0][0])

        if best_score >= self.threshold and 0 <= best_idx < len(self._entries):
            # Cache HIT
            entry = self._entries[best_idx]
            entry["last_access"] = time.time()
            self.hits += 1

            return {
                "response": entry["response"],
                "intent": entry["intent"],
                "sources": entry["sources"],
                "cache_score": best_score,
                "cached_query": entry["query"],
            }

        # Cache MISS
        self.misses += 1
        return None

    def store(self, query: str, response: str, intent: str, sources: list):
        """
        Almacena una respuesta en el cache.

        Args:
            query: Pregunta original del usuario
            response: Respuesta generada por el LLM
            intent: Intención clasificada
            sources: Fuentes usadas
        """
        self._ensure_model()

        # Generar embedding
        embedding = self.model.encode([query], convert_to_numpy=True)[0]

        if self._dimension is None:
            self._dimension = len(embedding)

        now = time.time()

        entry = {
            "query": query,
            "response": response,
            "intent": intent,
            "sources": sources,
            "embedding": embedding,
            "timestamp": now,
            "last_access": now,
        }

        self._entries.append(entry)

        # Evict si es necesario
        self._evict_lru()

        # Reconstruir índice
        self._rebuild_index()

    def get_stats(self) -> Dict:
        """Retorna estadísticas del cache."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0

        return {
            "entries": len(self._entries),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "threshold": self.threshold,
            "ttl_seconds": self.ttl_seconds,
        }

    def clear(self):
        """Limpia todo el cache."""
        self._entries.clear()
        self._index = None
        self.hits = 0
        self.misses = 0
