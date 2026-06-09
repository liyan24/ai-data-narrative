"""Information Completeness (IC) evaluator.

Checks whether the report contains key sections: background, method, findings, conclusion.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ai_data_narrative.evaluation.base import Evaluator


class InformationCompletenessEvaluator(Evaluator):
    metric = "IC"

    # Auto-check keywords
    SECTION_KEYWORDS = {
        "背景": ["背景", "context", "introduction", "简介"],
        "方法": ["方法", "method", "methodology", "approach", "分析"],
        "发现": ["发现", "finding", "result", "insight", "关键驱动", "结论"],
        "结论": ["结论", "recommendation", "takeaway", "summary", "建议"],
    }

    def evaluate(
        self,
        narrative_report: str,
        data: Any,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        text = (narrative_report or "").lower()
        dimensions: Dict[str, float] = {}
        for section, keywords in self.SECTION_KEYWORDS.items():
            dimensions[section] = 1.0 if any(kw in text for kw in keywords) else 0.0
        score = sum(dimensions.values()) / len(dimensions)
        missing = [s for s, v in dimensions.items() if v < 0.5]
        suggestions: List[str] = []
        if missing:
            suggestions.append(f"建议补充以下章节：{', '.join(missing)}")
        return {
            "metric": self.metric,
            "score": round(score, 4),
            "dimensions": dimensions,
            "reasoning": f"检测到 {sum(dimensions.values())}/{len(dimensions)} 个关键章节。",
            "suggestions": suggestions,
        }
