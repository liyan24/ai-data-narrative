"""Multi-LLM judge that routes evaluation prompts to several providers."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ai_data_narrative.interfaces import BaseLLMProvider
from ai_data_narrative.llm.router import LLMRouter
from ai_data_narrative.models import AggregatedScore, JudgeScore


class MultiLLMJudge:
    """Evaluate a single metric using multiple LLM providers and aggregate results."""

    def __init__(self, providers: List[BaseLLMProvider], router: LLMRouter | None = None):
        self.providers = providers
        self.router = router or LLMRouter(providers)

    def score_metric(
        self,
        metric: str,
        narrative_report: str,
        prompt_template: str,
        aggregation: str = "weighted",
    ) -> AggregatedScore:
        messages = [
            {"role": "system", "content": "You are an expert evaluator. Respond with valid JSON only."},
            {"role": "user", "content": prompt_template.format(report=narrative_report, metric=metric)},
        ]
        results = self.router.call_all(messages, json_mode=True)
        judge_scores: List[JudgeScore] = []
        for provider in self.providers:
            result = results.get(provider.name)
            if isinstance(result, dict) and "error" not in result:
                score = float(result.get("score", 0.0))
                reasoning = result.get("reasoning", "")
                judge_scores.append(
                    JudgeScore(provider=provider.name, weight=provider.weight, score=score, reasoning=reasoning)
                )
        if not judge_scores:
            # Fallback single mock-like score when no providers respond
            judge_scores.append(JudgeScore(provider="fallback", weight=1.0, score=0.5, reasoning="No provider responses"))
        return LLMRouter.aggregate(metric, judge_scores, method=aggregation)
