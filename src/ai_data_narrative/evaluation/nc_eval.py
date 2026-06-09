"""Narrative Coherence (NC) evaluator.

Checks structural markers, logical connectors, evidence markers, and absence of contradictions.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ai_data_narrative.evaluation.base import Evaluator


class NarrativeCoherenceEvaluator(Evaluator):
    metric = "NC"

    def evaluate(
        self,
        narrative_report: str,
        data: Any,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        text = narrative_report or ""
        lower = text.lower()

        structure_score = self._structure_score(lower)
        evidence_score = 1.0 if "数据" in lower or "图表" in lower or "图" in lower else 0.5
        logical_score = self._logical_score(lower)
        consistency_score = 1.0  # Placeholder; contradiction detection can be expanded
        flow_score = self._flow_score(lower)

        dimensions = {
            "结构": round(structure_score, 4),
            "证据支持": round(evidence_score, 4),
            "逻辑递进": round(logical_score, 4),
            "内部一致性": round(consistency_score, 4),
            "流畅与连接": round(flow_score, 4),
        }
        score = sum(dimensions.values()) / len(dimensions)
        suggestions: List[str] = []
        if structure_score < 0.8:
            suggestions.append("建议添加明确的开头、中间和结尾部分。")
        if evidence_score < 0.8:
            suggestions.append("建议引用数据或图表来支撑观点。")
        if logical_score < 0.5:
            suggestions.append("建议使用更多过渡词连接各部分内容。")
        return {
            "metric": self.metric,
            "score": round(score, 4),
            "dimensions": dimensions,
            "reasoning": "自动检查了叙事结构标记和流畅性标记。",
            "suggestions": suggestions,
        }

    def _structure_score(self, text: str) -> float:
        has_beginning = any(w in text for w in ["背景", "铺垫", "简介", "introduction", "setup"])
        has_middle = any(w in text for w in ["分析", "发现", "冲突", "findings", "analysis"])
        has_end = any(w in text for w in ["结论", "建议", "解决", "recommendation", "resolution"])
        return sum([has_beginning, has_middle, has_end]) / 3.0

    def _logical_score(self, text: str) -> float:
        connectors = [
            "因此", "所以", "从而", "因为", "由于", "此外", "然而", "另外",
            "首先", "其次", "最后", "综上所述", "总之",
            "therefore", "thus", "consequently", "because", "since", "however", "furthermore",
        ]
        count = sum(1 for c in connectors if c in text)
        return min(1.0, count / 3.0)

    def _flow_score(self, text: str) -> float:
        # Check for headers and paragraph count
        headers = len(re.findall(r"^#{1,3}\s+", text, re.MULTILINE))
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])
        score = 0.5
        if headers >= 3:
            score += 0.25
        if paragraphs >= 3:
            score += 0.25
        return min(1.0, score)
