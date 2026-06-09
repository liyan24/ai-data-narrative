"""Base evaluator interface."""
from __future__ import annotations

from typing import Any, Dict

from ai_data_narrative.interfaces import BaseEvaluator
from ai_data_narrative.models import ScoreDetails


class Evaluator(BaseEvaluator):
    """Convenience base with result normalization."""

    metric: str = "base"

    def _to_score_details(self, raw: Dict[str, Any]) -> ScoreDetails:
        return ScoreDetails(
            metric=raw.get("metric", self.metric),
            score=float(raw.get("score", 0.0)),
            dimensions=raw.get("dimensions", {}),
            reasoning=raw.get("reasoning", ""),
            suggestions=raw.get("suggestions", []),
        )
