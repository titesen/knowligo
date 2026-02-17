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


def chunk_text(text: str, chunk_size: int = 1024, overlap: int = 128) -> List[str]:
    """
    Divide un texto en chunks con overlap usando sliding window.

    Lógica especial:
    - Bloques de tabla markdown (líneas con ``|``) se mantienen como unidad atómica
      (hasta 2048 chars).
    - Bloques Q&A (### pregunta + respuesta) se mantienen juntos.

    Args:
        text: Texto a dividir
        chunk_size: Tamaño máximo de cada chunk en caracteres (default: 1024)
        overlap: Número de caracteres de overlap entre chunks (default: 128)

    Returns:
        Lista de chunks de texto
    """
    if not text or not text.strip():
        return []

    # Si el texto es más corto que chunk_size, retornar como está
    if len(text) <= chunk_size:
        return [text.strip()]

    # --- Paso 1: separar bloques atómicos (tablas) del texto normal ---
    blocks = _split_atomic_blocks(text)

    chunks: list[str] = []
    for block_text, is_atomic in blocks:
        block_text = block_text.strip()
        if not block_text:
            continue

        if is_atomic:
            # Tablas / bloques atómicos: no partir (hard cap = 2048)
            if len(block_text) <= 2048:
                chunks.append(block_text)
            else:
                # Excepcionalmente largo — usar sliding window con tamaño mayor
                chunks.extend(_sliding_window(block_text, 2048, overlap))
        else:
            # Texto normal: sliding window estándar
            chunks.extend(_sliding_window(block_text, chunk_size, overlap))

    return chunks


def _split_atomic_blocks(text: str) -> list[tuple[str, bool]]:
    """Separa el texto en bloques (texto, is_atomic).

    Un bloque atómico es una secuencia contigua de líneas de tabla markdown
    (empiezan con ``|``) incluyendo la línea de header inmediatamente anterior.
    """
    lines = text.split("\n")
    blocks: list[tuple[str, bool]] = []
    buf: list[str] = []
    in_table = False

    for line in lines:
        is_table_line = line.strip().startswith("|")
        if is_table_line and not in_table:
            # Empezó una tabla — la línea anterior probablemente sea el header
            header_line = ""
            if buf:
                header_line = buf.pop()  # quitar la última línea del buffer normal
                if buf:
                    blocks.append(("\n".join(buf), False))
                    buf = []
            in_table = True
            if header_line:
                buf.append(header_line)
            buf.append(line)
        elif is_table_line and in_table:
            buf.append(line)
        elif not is_table_line and in_table:
            # Terminó la tabla
            blocks.append(("\n".join(buf), True))
            buf = [line]
            in_table = False
        else:
            buf.append(line)

    if buf:
        blocks.append(("\n".join(buf), in_table))

    return blocks


def _sliding_window(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Sliding window clásico con corte en espacio/newline."""
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            search_start = max(start + chunk_size - 80, start)
            last_break = max(
                text.rfind(" ", search_start, end), text.rfind("\n", search_start, end)
            )
            if last_break > start:
                end = last_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap if end < len(text) else len(text)

    return chunks


def process_documents(
    docs_path: str = None, chunk_size: int = 1024, overlap: int = 128
) -> List[Dict]:
    """
    Procesa todos los documentos: carga, extrae secciones y chunking.

    Args:
        docs_path: Ruta al directorio de documentos
        chunk_size: Tamaño de chunks en caracteres (default: 1024)
        overlap: Overlap entre chunks (default: 128)

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
