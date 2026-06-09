"""Comprehensibility (CP) evaluator.

Heuristic readability: sentence length, jargon density, visual labels.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ai_data_narrative.evaluation.base import Evaluator


class ComprehensibilityEvaluator(Evaluator):
    metric = "CP"

    def evaluate(
        self,
        narrative_report: str,
        data: Any,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        text = narrative_report or ""
        sentences = re.split(r"[.!?。！？]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Sentence complexity
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        sentence_score = 1.0 if 10 <= avg_len <= 25 else max(0.0, 1.0 - abs(avg_len - 17) / 20)

        # Jargon density (simple proxy: long words > 12 chars)
        words = re.findall(r"\b\w+\b", text)
        long_words = [w for w in words if len(w) > 12]
        jargon_score = max(0.0, 1.0 - len(long_words) / max(len(words), 1) * 5)

        # Visual accessibility
        viz_score = 1.0 if "![" in text or "图表" in text or "图" in text else 0.5

        # Structure aids
        structure_score = 1.0 if len(re.findall(r"^#{1,3}\s+", text, re.MULTILINE)) >= 3 else 0.5

        # Term definitions (simple proxy: parentheses or quotes)
        term_score = 1.0 if "(" in text else 0.6

        # Assumed knowledge (simple proxy: no heavy acronyms)
        acronym_count = len(re.findall(r"\b[A-Z]{3,}\b", text))
        knowledge_score = max(0.0, 1.0 - acronym_count / 10)

        dimensions = {
            "术语处理": round(term_score, 4),
            "句子复杂度": round(sentence_score, 4),
            "概念解释": round(jargon_score, 4),
            "可视化可及性": round(viz_score, 4),
            "先决知识": round(knowledge_score, 4),
            "结构辅助": round(structure_score, 4),
        }
        score = sum(dimensions.values()) / len(dimensions)
        suggestions: List[str] = []
        if sentence_score < 0.7:
            suggestions.append("建议缩短句子以提升可读性。")
        if jargon_score < 0.7:
            suggestions.append("建议解释或替换专业术语。")
        if viz_score < 0.8:
            suggestions.append("建议添加可视化图表。")
        return {
            "metric": self.metric,
            "score": round(score, 4),
            "dimensions": dimensions,
            "reasoning": f"平均句长 {avg_len:.1f} 词；发现 {len(long_words)} 个长词。",
            "suggestions": suggestions,
        }
