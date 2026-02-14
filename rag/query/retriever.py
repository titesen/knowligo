"""
Retriever - Recupera chunks relevantes del índice FAISS.

Este módulo:
1. Carga el índice FAISS y metadata de chunks
2. Genera embeddings para queries
3. Busca los chunks más similares
4. Retorna contexto relevante para el LLM
"""

import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
from dotenv import load_dotenv

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    print("⚠️  Dependencias no instaladas. Ejecuta: pip install -r requirements.txt")
    exit(1)


# Modelo multilingüe por defecto (soporta español, inglés, y 50+ idiomas)
DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


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
            model_name: Modelo de sentence-transformers para embeddings (lee de EMBEDDING_MODEL env var)
        """
        # Cargar .env
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        # Modelo de embeddings: parámetro > env > default multilingüe
        if model_name is None:
            model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

        # Rutas por defecto
        if index_path is None or metadata_path is None:
            store_dir = project_root / "rag" / "store"

            if index_path is None:
                index_path = store_dir / "faiss.index"
            if metadata_path is None:
                metadata_path = store_dir / "metadata.json"

        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)

        # Cargar modelo de embeddings
        print(f"📥 Cargando modelo de embeddings: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

        # Cargar índice FAISS
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Índice FAISS no encontrado: {self.index_path}\n"
                "Ejecuta primero: python rag/ingest/build_index.py"
            )

        print(f"📥 Cargando índice FAISS desde: {self.index_path}")
        self.index = faiss.read_index(str(self.index_path))
        print(f"✅ Índice cargado ({self.index.ntotal} vectores)")

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
            print(
                f"⚠️  Warning: Número de chunks ({len(self.chunks)}) "
                f"no coincide con vectores en índice ({self.index.ntotal})"
            )
        else:
            print(f"✅ {len(self.chunks)} chunks cargados")

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


# Instancia singleton
_retriever_instance = None


def get_retriever() -> FAISSRetriever:
    """Obtiene una instancia singleton del retriever"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = FAISSRetriever()
    return _retriever_instance


def retrieve_context(query: str, top_k: int = 3) -> Tuple[List[Dict], str]:
    """
    Función de conveniencia para recuperar contexto.

    Args:
        query: Consulta del usuario
        top_k: Número de chunks a recuperar

    Returns:
        Tuple de (results: List[Dict], formatted_context: str)
    """
    retriever = get_retriever()
    results = retriever.retrieve(query, top_k=top_k)
    context = retriever.format_context(results)
    return results, context


# Script de prueba
if __name__ == "__main__":
    print("🔍 Testing FAISS Retriever\n")

    try:
        retriever = FAISSRetriever()

        test_queries = [
            "¿Qué planes de soporte ofrecen?",
            "¿Cuál es el SLA para tickets High?",
            "¿Hacen mantenimiento preventivo?",
        ]

        for query in test_queries:
            print(f"\n{'=' * 60}")
            print(f"Query: {query}")
            print("=" * 60)

            results = retriever.retrieve(query, top_k=3)

            if results:
                print(f"\n✅ Encontrados {len(results)} chunks relevantes:\n")
                for result in results:
                    print(f"Rank: {result['rank']} | Score: {result['score']:.4f}")
                    print(f"Source: {result['metadata'].get('source', 'N/A')}")
                    print(f"Text: {result['text'][:200]}...")
                    print()

                print("\n📝 Contexto formateado:")
                print("-" * 60)
                context = retriever.format_context(results)
                print(context[:500] + "..." if len(context) > 500 else context)
            else:
                print("❌ No se encontraron chunks relevantes")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\n💡 Ejecuta primero: python rag/ingest/build_index.py")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
