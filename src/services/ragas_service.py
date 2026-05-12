import asyncio
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from datasets import Dataset
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from fastapi import HTTPException, status

from src.services.vectordb_service import vectordb_service
from src.services.chat_service import chat_service
from src.setting.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class RagasEvaluationService:

    def __init__(self):
        self.llm = LangchainLLMWrapper(
            ChatGroq(model=config.JUDGE_LLM_MODEL, api_key=config.GROQ_API_KEY, timeout=120)
        )
        self.embeddings = LangchainEmbeddingsWrapper(
            HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)
        )
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ]

    async def evaluate_single(self, query: str, ground_truth: str, user_id: int) -> dict:

        logger.info(f"Starting RAGAS evaluation | user_id={user_id} | query='{query}'")

        try:
            result = await chat_service.ask(query=query, user_id=user_id)
        except Exception as e:
            logger.error(f"Chat pipeline failed during evaluation: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="RAG pipeline failed during evaluation"
            )

        answer = result["answer"]
        sources = result["sources"]

        if not sources:
            logger.warning("No sources retrieved — skipping RAGAS evaluation")
            return {
                "query": query,
                "answer": answer,
                "ground_truth": ground_truth,
                "scores": None,
                "warning": "No documents were retrieved. Upload relevant documents before evaluating."
            }

        contexts = [s["content"] for s in sources]

        eval_dataset = Dataset.from_dict({
            "question":   [query],
            "answer":     [answer],
            "contexts":   [contexts],
            "ground_truth": [ground_truth],
        })

        logger.info("Running RAGAS metrics")
        try:
            ragas_result = await asyncio.to_thread(
                self._run_ragas, eval_dataset
            )
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"RAGAS evaluation error: {str(e)}"
            )

        scores_df = ragas_result.to_pandas()
        scores = {
            "faithfulness":      self._safe_score(scores_df, "faithfulness"),
            "answer_relevancy":  self._safe_score(scores_df, "answer_relevancy"),
            "context_precision": self._safe_score(scores_df, "context_precision"),
            "context_recall":    self._safe_score(scores_df, "context_recall"),
        }

        valid_scores = [v for v in scores.values() if v is not None]
        scores["composite"] = round(sum(valid_scores) / len(valid_scores), 4) if valid_scores else None

        logger.info(f"RAGAS evaluation complete | scores={scores}")

        return {
            "query":        query,
            "answer":       answer,
            "ground_truth": ground_truth,
            "contexts_used": len(contexts),
            "scores":       scores,
        }

    def _run_ragas(self, dataset: Dataset):
        return evaluate(
            dataset=dataset,
            metrics=self.metrics,
            llm=self.llm,
            embeddings=self.embeddings,
        )

    def _safe_score(self, df, metric_name: str):
        import math
        if metric_name in df.columns:
            val = df[metric_name].iloc[0]
            if val is None:
                return None
            float_val = float(val)
            if math.isnan(float_val) or math.isinf(float_val):
                return None
            return round(float_val, 4)
        return None

    async def evaluate_batch(self, samples: list[dict], user_id: int) -> dict:

        if not samples:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="samples list cannot be empty"
            )

        logger.info(f"Sequential RAGAS evaluation | user_id={user_id} | samples={len(samples)}")

        results = []
        for i, sample in enumerate(samples):
            logger.info(f"Evaluating sample {i + 1}/{len(samples)}")
            try:
                result = await self.evaluate_single(
                    query=sample["query"],
                    ground_truth=sample["ground_truth"],
                    user_id=user_id,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Sample {i + 1} failed: {str(e)}")
                results.append({
                    "query": sample["query"],
                    "ground_truth": sample["ground_truth"],
                    "error": str(e),
                    "scores": None,
                })

        metric_keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "composite"]
        averages = {}
        for key in metric_keys:
            vals = [
                r["scores"][key]
                for r in results
                if r.get("scores") and r["scores"].get(key) is not None
            ]
            averages[key] = round(sum(vals) / len(vals), 4) if vals else None

        successful = sum(1 for r in results if r.get("scores") is not None)
        failed = len(results) - successful

        logger.info(f"Batch complete | successful={successful} | failed={failed} | averages={averages}")

        return {
            "total_samples": len(results),
            "successful": successful,
            "failed": failed,
            "averages": averages,
            "results": results,
        }


ragas_evaluation_service = RagasEvaluationService()



