"""
Chunker - Módulo para procesar y dividir documentos markdown en chunks.

Este módulo se encarga de:
1. Cargar documentos markdown desde el directorio de knowledge
2. Dividir el texto en chunks con overlap para mantener contexto
3. Preservar metadata (archivo fuente, secciones)
"""

from pathlib import Path
from typing import List, Dict
import re


def load_documents(docs_path: str = None) -> List[Dict[str, str]]:
    """
    Carga todos los documentos markdown del directorio especificado.

    Args:
        docs_path: Ruta al directorio de documentos. Si es None, usa knowledge/documents/

    Returns:
        Lista de diccionarios con {filename, content}
    """
    if docs_path is None:
        # Ruta por defecto relativa al proyecto
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent
        docs_path = project_root / "knowledge" / "documents"
    else:
        docs_path = Path(docs_path)

    if not docs_path.exists():
        raise FileNotFoundError(f"Directorio no encontrado: {docs_path}")

    documents = []

    # Buscar todos los archivos .md
    for file_path in docs_path.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

                # Solo agregar si tiene contenido
                if content.strip():
                    documents.append(
                        {
                            "filename": file_path.name,
                            "filepath": str(file_path),
                            "content": content,
                        }
                    )
        except Exception as e:
            print(f"⚠️  Error leyendo {file_path.name}: {e}")
            continue

    print(f"✅ Cargados {len(documents)} documentos desde {docs_path}")
    return documents


def extract_sections(content: str, filename: str) -> List[Dict[str, str]]:
    """
    Extrae secciones del markdown basándose en headers (#, ##, ###).

    Args:
        content: Contenido markdown
        filename: Nombre del archivo fuente

    Returns:
        Lista de secciones con metadata
    """
    sections = []

    # Dividir por headers (# Title)
    # Pattern para detectar headers markdown
    header_pattern = r"^(#{1,3})\s+(.+)$"

    lines = content.split("\n")
    current_section = {
        "header": filename,  # Usar filename como header por defecto
        "level": 0,
        "content_lines": [],
    }

    for line in lines:
        header_match = re.match(header_pattern, line)

        if header_match:
            # Guardar sección anterior si tiene contenido
            if current_section["content_lines"]:
                sections.append(
                    {
                        "header": current_section["header"],
                        "level": current_section["level"],
                        "text": "\n".join(current_section["content_lines"]).strip(),
                        "source": filename,
                    }
                )

            # Iniciar nueva sección
            level = len(header_match.group(1))  # Número de #
            header_text = header_match.group(2).strip()

            current_section = {
                "header": header_text,
                "level": level,
                "content_lines": [],
            }
        else:
            # Agregar línea al contenido actual
            current_section["content_lines"].append(line)

    # Agregar última sección
    if current_section["content_lines"]:
        sections.append(
            {
                "header": current_section["header"],
                "level": current_section["level"],
                "text": "\n".join(current_section["content_lines"]).strip(),
                "source": filename,
            }
        )

    return sections


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Divide un texto en chunks con overlap usando sliding window.

    Args:
        text: Texto a dividir
        chunk_size: Tamaño máximo de cada chunk en caracteres
        overlap: Número de caracteres de overlap entre chunks

    Returns:
        Lista de chunks de texto
    """
    if not text or not text.strip():
        return []

    # Si el texto es más corto que chunk_size, retornar como está
    if len(text) <= chunk_size:
        return [text.strip()]

    chunks = []
    start = 0

    while start < len(text):
        # Definir fin del chunk
        end = start + chunk_size

        # Si no es el último chunk y hay más texto
        if end < len(text):
            # Intentar cortar en un espacio o salto de línea para no partir palabras
            # Buscar último espacio/salto dentro de los últimos 50 caracteres
            search_start = max(start + chunk_size - 50, start)
            last_break = max(
                text.rfind(" ", search_start, end), text.rfind("\n", search_start, end)
            )

            if last_break > start:
                end = last_break

        # Extraer chunk y limpiar
        chunk = text[start:end].strip()

        if chunk:  # Solo agregar si no está vacío
            chunks.append(chunk)

        # Mover start con overlap
        start = end - overlap if end < len(text) else len(text)

    return chunks


def process_documents(
    docs_path: str = None, chunk_size: int = 500, overlap: int = 50
) -> List[Dict]:
    """
    Procesa todos los documentos: carga, extrae secciones y chunking.

    Args:
        docs_path: Ruta al directorio de documentos
        chunk_size: Tamaño de chunks en caracteres
        overlap: Overlap entre chunks

    Returns:
        Lista de chunks con metadata completa
    """
    # Cargar documentos
    documents = load_documents(docs_path)

    all_chunks = []
    chunk_id = 0

    for doc in documents:
        # Extraer secciones del documento
        sections = extract_sections(doc["content"], doc["filename"])

        for section in sections:
            # Chunking del texto de cada sección
            text_chunks = chunk_text(section["text"], chunk_size, overlap)

            for i, chunk_content in enumerate(text_chunks):
                all_chunks.append(
                    {
                        "id": chunk_id,
                        "text": chunk_content,
                        "metadata": {
                            "source": section["source"],
                            "section": section["header"],
                            "section_level": section["level"],
                            "chunk_index": i,
                            "total_chunks_in_section": len(text_chunks),
                        },
                    }
                )
                chunk_id += 1

    print(f"✅ Procesados {len(all_chunks)} chunks desde {len(documents)} documentos")
    return all_chunks


if __name__ == "__main__":
    """Test del módulo"""
    print("🧪 Probando chunker.py...\n")

    # Procesar documentos
    chunks = process_documents()

    # Mostrar estadísticas
    print(f"\n📊 Estadísticas:")
    print(f"   Total de chunks: {len(chunks)}")

    # Agrupar por source
    sources = {}
    for chunk in chunks:
        source = chunk["metadata"]["source"]
        sources[source] = sources.get(source, 0) + 1

    print(f"   Chunks por documento:")
    for source, count in sources.items():
        print(f"      - {source}: {count} chunks")

    # Mostrar ejemplo de chunk
    if chunks:
        print(f"\n📄 Ejemplo de chunk:")
        example = chunks[0]
        print(f"   ID: {example['id']}")
        print(f"   Source: {example['metadata']['source']}")
        print(f"   Section: {example['metadata']['section']}")
        print(f"   Text preview: {example['text'][:100]}...")
