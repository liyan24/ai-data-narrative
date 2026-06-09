"""Structural Fidelity (SF) evaluator.

Checks that the narrative aligns with data-derived facts (placeholder dimensions).
"""
from __future__ import annotations

from typing import Any, Dict, List

from ai_data_narrative.evaluation.base import Evaluator


class StructuralFidelityEvaluator(Evaluator):
    metric = "SF"

    def evaluate(
        self,
        narrative_report: str,
        data: Any,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        text = narrative_report or ""
        lower = text.lower()

        # Heuristic dimensions
        data_mentioned = 1.0 if "数据" in lower or "dataset" in lower or "分析" in lower else 0.5
        conclusions_present = 1.0 if "结论" in lower or "建议" in lower or "recommend" in lower else 0.5
        no_overclaim = 1.0  # placeholder
        aligned_metrics = 1.0 if "收入" in lower or "客户" in lower or "数据" in lower else 0.7
        scope_clear = 1.0 if "背景" in lower else 0.7
        limitations = 1.0 if "局限" in lower or "不足" in lower or "caveat" in lower else 0.6

        dimensions = {
            "数据基础": round(data_mentioned, 4),
            "结论有效性": round(conclusions_present, 4),
            "无夸大": round(no_overclaim, 4),
            "指标对齐": round(aligned_metrics, 4),
            "范围清晰": round(scope_clear, 4),
            "局限性声明": round(limitations, 4),
        }
        score = sum(dimensions.values()) / len(dimensions)
        suggestions: List[str] = []
        if data_mentioned < 0.8:
            suggestions.append("建议明确引用所分析的数据集。")
        if conclusions_present < 0.8:
            suggestions.append("建议添加明确的结论或建议部分。")
        return {
            "metric": self.metric,
            "score": round(score, 4),
            "dimensions": dimensions,
            "reasoning": "评估了叙事对数据和范围的忠实程度。",
            "suggestions": suggestions,
        }
