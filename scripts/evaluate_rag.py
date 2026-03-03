"""
Evaluador RAG - Evaluación automatizada del sistema RAG de KnowLigo.

Implementa métricas inspiradas en RAGAS (Retrieval-Augmented Generation Assessment):
1. Faithfulness: ¿La respuesta se basa en el contexto recuperado?
2. Answer Relevancy: ¿La respuesta es relevante a la pregunta?
3. Context Precision: ¿Los chunks recuperados son relevantes?

Usa Groq como LLM-judge para evaluar cada métrica.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Agregar raíz del proyecto al path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from groq import Groq


# Configuración
EVAL_DATASET_PATH = Path(__file__).parent / "eval_dataset.json"
RESULTS_DIR = Path(__file__).parent / "eval_results"

# LLM Judge
GROQ_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# LLM Judge


class LLMJudge:
    """Usa Groq LLM como juez para evaluar respuestas del RAG."""

    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY no configurada en .env")
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = GROQ_MODEL

    def _call_llm(self, prompt: str) -> str:
        """Llama al LLM judge con rate limiting."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un evaluador experto de sistemas RAG. "
                            "Evalúa de forma objetiva y precisa. "
                            "Responde SOLO con el JSON solicitado, sin texto adicional."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  ⚠️  Error LLM judge: {e}")
            return '{"score": 0.5, "reason": "Error evaluando"}'

    def evaluate_faithfulness(
        self, question: str, answer: str, contexts: List[str]
    ) -> Dict:
        """
        Faithfulness: ¿La respuesta se basa fielmente en el contexto?

        Score 1.0 = completamente basada en el contexto
        Score 0.0 = completamente inventada / alucinación
        """
        context_text = "\n---\n".join(contexts[:5])

        prompt = f"""Evalúa si la respuesta se basa fielmente en el contexto proporcionado.

PREGUNTA: {question}

CONTEXTO RECUPERADO:
{context_text}

RESPUESTA DEL SISTEMA:
{answer}

Evalúa del 0.0 al 1.0:
- 1.0: Toda la información en la respuesta proviene del contexto
- 0.7: La mayoría de la información está en el contexto, con mínimas adiciones
- 0.5: Mezcla de información del contexto e información no presente
- 0.3: La mayoría de la información NO está en el contexto
- 0.0: La respuesta contradice o ignora completamente el contexto

Responde SOLO con JSON: {{"score": float, "reason": "explicación breve"}}"""

        result = self._call_llm(prompt)
        return self._parse_score(result)

    def evaluate_relevancy(self, question: str, answer: str) -> Dict:
        """
        Answer Relevancy: ¿La respuesta es relevante a la pregunta?

        Score 1.0 = perfectamente relevante
        Score 0.0 = completamente irrelevante
        """
        prompt = f"""Evalúa si la respuesta es relevante y útil para la pregunta del usuario.

PREGUNTA: {question}

RESPUESTA DEL SISTEMA:
{answer}

Evalúa del 0.0 al 1.0:
- 1.0: La respuesta aborda directa y completamente la pregunta
- 0.7: La respuesta es relevante pero podría ser más completa
- 0.5: La respuesta es parcialmente relevante
- 0.3: La respuesta apenas toca el tema de la pregunta
- 0.0: La respuesta es completamente irrelevante

Responde SOLO con JSON: {{"score": float, "reason": "explicación breve"}}"""

        result = self._call_llm(prompt)
        return self._parse_score(result)

    def evaluate_context_precision(self, question: str, contexts: List[str]) -> Dict:
        """
        Context Precision: ¿Los chunks recuperados son relevantes a la pregunta?

        Score 1.0 = todos los chunks son relevantes
        Score 0.0 = ningún chunk es relevante
        """
        context_items = ""
        for i, ctx in enumerate(contexts[:5], 1):
            context_items += f"\nCHUNK {i}:\n{ctx[:300]}...\n"

        prompt = f"""Evalúa cuántos de los chunks recuperados son relevantes para responder la pregunta.

PREGUNTA: {question}

CHUNKS RECUPERADOS:
{context_items}

Evalúa del 0.0 al 1.0:
- 1.0: Todos los chunks contienen información directamente relevante
- 0.7: La mayoría de chunks son relevantes
- 0.5: Aproximadamente la mitad son relevantes
- 0.3: Solo uno o dos chunks son relevantes
- 0.0: Ningún chunk es relevante para la pregunta

Responde SOLO con JSON: {{"score": float, "reason": "explicación breve"}}"""

        result = self._call_llm(prompt)
        return self._parse_score(result)

    def _parse_score(self, result: str) -> Dict:
        """Parsea la respuesta JSON del LLM judge."""
        try:
            # Limpiar posible markdown wrapping
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1]
                result = result.rsplit("```", 1)[0]

            parsed = json.loads(result)
            return {
                "score": float(parsed.get("score", 0.5)),
                "reason": parsed.get("reason", "Sin razón proporcionada"),
            }
        except (json.JSONDecodeError, ValueError):
            return {"score": 0.5, "reason": f"Error parseando: {result[:100]}"}


# Evaluador Principal


class RAGEvaluator:
    """Ejecuta la evaluación completa del sistema RAG."""

    def __init__(self):
        self.judge = LLMJudge()

        # Importar pipeline
        from rag.query.pipeline import RAGPipeline

        print("⏳ Cargando RAG Pipeline para evaluación...")
        self.pipeline = RAGPipeline()
        print("✅ Pipeline cargado\n")

    def load_dataset(self, path: Path = None) -> List[Dict]:
        """Carga el dataset de evaluación."""
        path = path or EVAL_DATASET_PATH
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate_single(self, item: Dict, index: int) -> Dict:
        """Evalúa una sola pregunta del dataset."""
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"\n{'=' * 60}")
        print(f"📝 [{index}] {question}")
        print(f"{'=' * 60}")

        # 1. Obtener respuesta del RAG
        result = self.pipeline.process_query(user_query=question, user_id="evaluator")

        answer = result.get("response", "Sin respuesta")
        sources = result.get("sources", [])
        contexts = [s.get("section", "") for s in sources if s.get("section")]

        # Si no hay contextos de las sources, intentar recuperar directamente
        if not contexts:
            retrieved = self.pipeline.retriever.retrieve(question, top_k=5)
            contexts = [c["text"] for c in retrieved]

        print(f"💬 Respuesta: {answer[:150]}...")

        # 2. Evaluar con LLM judge (con rate limiting entre llamadas)
        print("📊 Evaluando faithfulness...")
        faithfulness = self.judge.evaluate_faithfulness(question, answer, contexts)
        time.sleep(1)  # Rate limiting para Groq

        print("📊 Evaluando relevancy...")
        relevancy = self.judge.evaluate_relevancy(question, answer)
        time.sleep(1)

        print("📊 Evaluando context precision...")
        context_precision = self.judge.evaluate_context_precision(question, contexts)
        time.sleep(1)

        scores = {
            "faithfulness": faithfulness["score"],
            "relevancy": relevancy["score"],
            "context_precision": context_precision["score"],
        }

        print(
            f"  📈 Faithfulness: {scores['faithfulness']:.2f} | "
            f"Relevancy: {scores['relevancy']:.2f} | "
            f"Context Precision: {scores['context_precision']:.2f}"
        )

        return {
            "question": question,
            "ground_truth": ground_truth,
            "answer": answer,
            "intent": result.get("intent", "unknown"),
            "cached": result.get("cached", False),
            "processing_time": result.get("processing_time", 0),
            "scores": scores,
            "details": {
                "faithfulness": faithfulness,
                "relevancy": relevancy,
                "context_precision": context_precision,
            },
            "num_contexts": len(contexts),
        }

    def evaluate_all(self, dataset: List[Dict] = None) -> Dict:
        """Ejecuta la evaluación completa del dataset."""
        if dataset is None:
            dataset = self.load_dataset()

        print(f"🚀 Iniciando evaluación de {len(dataset)} preguntas")
        print(f"📋 Modelo judge: {GROQ_MODEL}")
        print(f"{'=' * 60}\n")

        results = []
        for i, item in enumerate(dataset, 1):
            try:
                result = self.evaluate_single(item, i)
                results.append(result)
            except Exception as e:
                print(f"❌ Error evaluando pregunta {i}: {e}")
                results.append(
                    {
                        "question": item["question"],
                        "error": str(e),
                        "scores": {
                            "faithfulness": 0,
                            "relevancy": 0,
                            "context_precision": 0,
                        },
                    }
                )

        # Calcular métricas agregadas
        metrics = self._calculate_aggregate_metrics(results)

        # Generar reporte
        report = {
            "timestamp": datetime.now().isoformat(),
            "model": GROQ_MODEL,
            "num_questions": len(dataset),
            "aggregate_metrics": metrics,
            "results": results,
        }

        # Guardar resultados
        self._save_report(report)

        # Mostrar resumen
        self._print_summary(metrics, results)

        return report

    def _calculate_aggregate_metrics(self, results: List[Dict]) -> Dict:
        """Calcula métricas promedio."""
        valid_results = [r for r in results if "error" not in r]

        if not valid_results:
            return {
                "faithfulness": 0,
                "relevancy": 0,
                "context_precision": 0,
                "overall": 0,
            }

        n = len(valid_results)
        faithfulness_avg = sum(r["scores"]["faithfulness"] for r in valid_results) / n
        relevancy_avg = sum(r["scores"]["relevancy"] for r in valid_results) / n
        context_avg = sum(r["scores"]["context_precision"] for r in valid_results) / n
        overall = (faithfulness_avg + relevancy_avg + context_avg) / 3

        return {
            "faithfulness": round(faithfulness_avg, 3),
            "relevancy": round(relevancy_avg, 3),
            "context_precision": round(context_avg, 3),
            "overall": round(overall, 3),
            "evaluated": n,
            "errors": len(results) - n,
        }

    def _save_report(self, report: Dict):
        """Guarda el reporte en un archivo JSON."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = RESULTS_DIR / f"eval_{timestamp}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Reporte guardado en: {filepath}")

    def _print_summary(self, metrics: Dict, results: List[Dict]):
        """Muestra un resumen visual de los resultados."""
        print(f"\n{'=' * 60}")
        print("📊 RESUMEN DE EVALUACIÓN RAG")
        print(f"{'=' * 60}")

        # Barras visuales para cada métrica
        for metric_name in ["faithfulness", "relevancy", "context_precision"]:
            score = metrics[metric_name]
            bar_len = int(score * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            label = metric_name.replace("_", " ").title()
            quality = self._score_quality(score)
            print(f"  {label:>20}: [{bar}] {score:.3f} {quality}")

        overall = metrics["overall"]
        bar_len = int(overall * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        quality = self._score_quality(overall)
        print(f"  {'─' * 50}")
        print(f"  {'OVERALL':>20}: [{bar}] {overall:.3f} {quality}")

        print(f"\n  Preguntas evaluadas: {metrics.get('evaluated', 0)}")
        print(f"  Errores: {metrics.get('errors', 0)}")

        # Análisis de resultados individuales
        valid_results = [r for r in results if "error" not in r]
        if valid_results:
            avg_time = sum(r.get("processing_time", 0) for r in valid_results) / len(
                valid_results
            )
            cached = sum(1 for r in valid_results if r.get("cached", False))
            print(f"  Tiempo promedio: {avg_time:.2f}s")
            print(f"  Cache hits: {cached}/{len(valid_results)}")

        # Preguntas con peor rendimiento
        if valid_results:
            worst = sorted(
                valid_results,
                key=lambda r: sum(r["scores"].values()) / 3,
            )[:3]

            if worst and sum(worst[0]["scores"].values()) / 3 < 0.7:
                print("\n  ⚠️  Preguntas con menor rendimiento:")
                for r in worst:
                    avg = sum(r["scores"].values()) / 3
                    print(f"    - [{avg:.2f}] {r['question'][:60]}...")

        print(f"{'=' * 60}\n")

    def _score_quality(self, score: float) -> str:
        """Devuelve un indicador de calidad para un score."""
        if score >= 0.8:
            return "✅ Excelente"
        elif score >= 0.6:
            return "🟡 Bueno"
        elif score >= 0.4:
            return "🟠 Regular"
        else:
            return "🔴 Bajo"


# Main
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluador RAG de KnowLigo")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(EVAL_DATASET_PATH),
        help="Ruta al dataset de evaluación (JSON)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limitar número de preguntas a evaluar",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🔬 KnowLigo RAG Evaluator")
    print("=" * 60)
    print()

    evaluator = RAGEvaluator()

    dataset = evaluator.load_dataset(Path(args.dataset))
    if args.limit:
        dataset = dataset[: args.limit]

    report = evaluator.evaluate_all(dataset)
