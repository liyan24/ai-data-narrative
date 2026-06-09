"""Multi-LLM routing, aggregation, and consensus."""
from __future__ import annotations

import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from ai_data_narrative.interfaces import BaseLLMProvider
from ai_data_narrative.models import AggregatedScore, JudgeScore


class LLMRouter:
    """Route prompts to multiple providers and aggregate scores."""

    def __init__(self, providers: List[BaseLLMProvider]):
        self.providers = providers

    def call_all(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=len(self.providers)) as pool:
            future_to_name = {
                pool.submit(p.complete, messages, json_mode, **kwargs): p.name
                for p in self.providers
            }
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    results[name] = {"error": str(exc)}
        return results

    @staticmethod
    def aggregate(
        metric: str,
        scores: List[JudgeScore],
        method: str = "weighted",
    ) -> AggregatedScore:
        values = [js.score for js in scores]
        mean = statistics.mean(values) if values else 0.0
        median = statistics.median(values) if values else 0.0
        weighted = (
            sum(js.score * js.weight for js in scores) / sum(js.weight for js in scores)
            if scores and sum(js.weight for js in scores) > 0
            else 0.0
        )
        std = statistics.stdev(values) if len(values) > 1 else 0.0
        if std <= 0.15:
            consensus = "high"
        elif std <= 0.30:
            consensus = "medium"
        else:
            consensus = "low"

        aggregated = mean
        if method == "median":
            aggregated = median
        elif method == "weighted":
            aggregated = weighted

        return AggregatedScore(
            metric=metric,
            mean=round(mean, 4),
            median=round(median, 4),
            weighted=round(weighted, 4),
            std=round(std, 4),
            consensus=consensus,
            judge_scores=scores,
        )
