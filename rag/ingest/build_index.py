"""
Build Index - Construye el índice FAISS para el sistema RAG.

Este módulo:
1. Carga documentos y los procesa en chunks (usando chunker.py)
2. Genera embeddings usando sentence-transformers
3. Crea índice FAISS y lo guarda
4. Guarda metadata de chunks para recuperación
"""

import os
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    print("⚠️  Dependencias no instaladas. Ejecuta: pip install -r requirements.txt")
    exit(1)

from chunker import process_documents

# Intentar importar el generador de docs desde DB
try:
    from db_to_docs import generate_db_docs
except ImportError:
    generate_db_docs = None


class IndexBuilder:
    """Clase para construir y guardar el índice FAISS"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa el builder con el modelo de embeddings.

        Args:
            model_name: Nombre del modelo de sentence-transformers
        """
        print(f"📥 Cargando modelo de embeddings: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"✅ Modelo cargado (dimensión: {self.dimension})")

    def generate_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        """
        Genera embeddings para todos los chunks.

        Args:
            chunks: Lista de chunks con texto y metadata

        Returns:
            Array numpy con embeddings (n_chunks x dimension)
        """
        print(f"🔢 Generando embeddings para {len(chunks)} chunks...")

        # Extraer solo el texto de cada chunk
        texts = [chunk["text"] for chunk in chunks]

        # Generar embeddings (batch processing es más eficiente)
        embeddings = self.model.encode(
            texts, show_progress_bar=True, convert_to_numpy=True, batch_size=32
        )

        print(f"✅ Embeddings generados: {embeddings.shape}")
        return embeddings

    def build_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Construye el índice FAISS.

        Args:
            embeddings: Array de embeddings

        Returns:
            Índice FAISS
        """
        print(f"🏗️  Construyendo índice FAISS...")

        # Usar IndexFlatL2 para búsqueda exacta (mejor para datasets pequeños)
        # Si el dataset fuera grande, podría usar IndexIVFFlat o IndexHNSW
        index = faiss.IndexFlatL2(self.dimension)

        # Agregar vectores al índice
        index.add(embeddings.astype("float32"))

        print(f"✅ Índice construido con {index.ntotal} vectores")
        return index

    def save_index(
        self, index: faiss.Index, chunks: List[Dict], output_dir: str = None
    ):
        """
        Guarda el índice FAISS y metadata de chunks.

        Args:
            index: Índice FAISS a guardar
            chunks: Lista de chunks con metadata
            output_dir: Directorio de salida (default: rag/store/)
        """
        if output_dir is None:
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent.parent
            output_dir = project_root / "rag" / "store"
        else:
            output_dir = Path(output_dir)

        # Crear directorio si no existe
        output_dir.mkdir(parents=True, exist_ok=True)

        # Guardar índice FAISS
        index_path = output_dir / "faiss.index"
        faiss.write_index(index, str(index_path))
        print(f"💾 Índice FAISS guardado en: {index_path}")

        # Guardar chunks con metadata (usando pickle para preservar estructura)
        chunks_path = output_dir / "chunks.pkl"
        with open(chunks_path, "wb") as f:
            pickle.dump(chunks, f)
        print(f"💾 Chunks guardados en: {chunks_path}")

        # Guardar metadata legible en JSON
        metadata = {
            "version": "v1.0.0",
            "created_at": datetime.now().isoformat(),
            "model_name": self.model_name,
            "embedding_dimension": self.dimension,
            "total_chunks": len(chunks),
            "total_vectors": index.ntotal,
            "documents_indexed": list(
                set(chunk["metadata"]["source"] for chunk in chunks)
            ),
            "index_type": "IndexFlatL2",
        }

        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"💾 Metadata guardada en: {metadata_path}")

        print(f"\n🎉 Índice completado exitosamente!")
        return metadata


def build_knowledge_base(
    chunk_size: int = 500, overlap: int = 50, model_name: str = "all-MiniLM-L6-v2"
):
    """
    Función principal para construir la base de conocimiento completa.

    Args:
        chunk_size: Tamaño de chunks en caracteres
        overlap: Overlap entre chunks
        model_name: Modelo de sentence-transformers
    """
    print("=" * 60)
    print("🚀 Construyendo Base de Conocimiento de KnowLigo")
    print("=" * 60 + "\n")

    # Paso 0: Generar documentos desde la DB (datos públicos)
    if generate_db_docs is not None:
        print("PASO 0: Generando documentos desde la base de datos")
        print("-" * 60)
        try:
            generate_db_docs()
        except Exception as e:
            print(f"⚠️  Error generando docs desde DB (continuando sin ellos): {e}")
        print(f"\n{'=' * 60}\n")
    else:
        print("ℹ️  db_to_docs no disponible, solo se indexarán documentos estáticos\n")

    # Paso 1: Procesar documentos en chunks (directorio principal)
    print("PASO 1: Procesamiento de documentos")
    print("-" * 60)
    chunks = process_documents(chunk_size=chunk_size, overlap=overlap)

    # Paso 1b: Procesar también documentos generados desde la DB
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    db_docs_dir = project_root / "knowledge" / "documents" / "db_generated"
    if db_docs_dir.exists() and any(db_docs_dir.glob("*.md")):
        print(f"\n📂 Procesando documentos generados desde DB...")
        db_chunks = process_documents(
            docs_path=str(db_docs_dir), chunk_size=chunk_size, overlap=overlap
        )
        # Reasignar IDs para que sean consecutivos
        offset = len(chunks)
        for chunk in db_chunks:
            chunk["id"] = chunk["id"] + offset
        chunks.extend(db_chunks)
        print(f"✅ Total combinado: {len(chunks)} chunks")
    else:
        print("ℹ️  No hay documentos generados desde DB")

    if not chunks:
        print("❌ No se encontraron chunks para indexar")
        return

    print(f"\n{'=' * 60}\n")

    # Paso 2: Generar embeddings y construir índice
    print("PASO 2: Generación de embeddings e índice")
    print("-" * 60)
    builder = IndexBuilder(model_name=model_name)

    embeddings = builder.generate_embeddings(chunks)
    index = builder.build_index(embeddings)

    print(f"\n{'=' * 60}\n")

    # Paso 3: Guardar índice y metadata
    print("PASO 3: Guardando índice y metadata")
    print("-" * 60)
    metadata = builder.save_index(index, chunks)

    print(f"\n{'=' * 60}")
    print("✅ Base de conocimiento construida exitosamente")
    print("=" * 60)
    print(f"\n📊 Resumen:")
    print(f"   - Documentos indexados: {len(metadata['documents_indexed'])}")
    print(f"   - Total de chunks: {metadata['total_chunks']}")
    print(f"   - Dimensión de embeddings: {metadata['embedding_dimension']}")
    print(f"   - Modelo usado: {metadata['model_name']}")
    print(f"\n💡 Ahora puedes probar el sistema de query con retriever.py")


if __name__ == "__main__":
    """Ejecutar construcción del índice"""
    import sys

    # Permitir pasar parámetros desde línea de comandos
    chunk_size = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    overlap = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    model = sys.argv[3] if len(sys.argv) > 3 else "all-MiniLM-L6-v2"

    build_knowledge_base(chunk_size=chunk_size, overlap=overlap, model_name=model)
