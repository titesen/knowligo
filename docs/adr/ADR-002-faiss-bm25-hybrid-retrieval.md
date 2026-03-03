# ADR-002: Retrieval Híbrido FAISS + BM25 con RRF Fusion

**Estado**: Aceptada  
**Autores**: Facundo  

---

## Contexto

El sistema RAG necesita recuperar chunks relevantes de la base de conocimiento para alimentar al LLM. Las opciones evaluadas fueron:

1. **Solo FAISS (dense retrieval)** — Búsqueda por similitud semántica de embeddings
2. **Solo BM25 (sparse retrieval)** — Búsqueda léxica por frecuencia de términos
3. **Híbrido FAISS + BM25 con Reciprocal Rank Fusion** — Combinar ambos enfoques

El contenido de KnowLigo incluye documentos con **terminología técnica específica** (nombres de planes "Básico/Profesional/Empresarial", SLAs con horas numéricas, precios en ARS) donde la búsqueda léxica es fuerte, junto con **consultas en lenguaje natural** donde la búsqueda semántica supera.

## Decisión

**Usamos retrieval híbrido**: FAISS (dense) + BM25 (sparse) combinados con **Reciprocal Rank Fusion (RRF)**, seguido de **Cross-Encoder reranking** para re-evaluar los candidatos.

## Consecuencias

### Beneficios
- **Cobertura complementaria**: BM25 captura matches exactos (ej: "Plan Profesional $499.000") que los embeddings pueden perder; FAISS captura similitud semántica (ej: "soporte presencial" ≈ "visita in-situ")
- **RRF es parameter-free**: No requiere calibrar pesos α/β entre dense y sparse — usa rankings, no scores
- **Cross-Encoder como safety net**: Re-evalúa los top-15 candidatos con análisis (query, chunk) pair para máxima precisión
- **Graceful degradation**: Si `rank_bm25` no está instalada, cae a dense-only sin romper

### Trade-offs aceptados
- **Latencia adicional**: ~200ms extra por BM25 + reranking sobre dense-only. Aceptable dado que la latencia total es ~1.5s (dominada por LLM call)
- **Memoria**: BM25 mantiene corpus tokenizado en RAM (~5MB para nuestros docs). Aceptable
- **Dependencia adicional**: `rank-bm25>=0.2.2`, `cross-encoder/ms-marco-MiniLM-L-6-v2`

### Implementación
```
HybridRetriever (rag/query/retriever.py)
  ├── FAISSRetriever.search()  →  dense_results (score)
  ├── BM25.get_scores()        →  sparse_results (score)
  └── _rrf_fusion()            →  merged_results (rank-based)
      └── CrossEncoderReranker.rerank()  →  final top-5
```

### Beneficio esperado
- Dense-only tiene limitaciones con términos técnicos exactos y códigos
- Hybrid + RRF + reranking mejora significativamente la cobertura léxica + semántica
