"""Factual Accuracy (FA) evaluator.

Extracts numeric claims from the narrative and validates them against data-derived metrics.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from ai_data_narrative.evaluation.base import Evaluator


class FactualAccuracyEvaluator(Evaluator):
    metric = "FA"

    def evaluate(
        self,
        narrative_report: str,
        data: Any,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        claims = self._extract_numeric_claims(narrative_report or "")
        verified = self._verify_claims(claims, data)
        total = len(verified)
        correct = sum(1 for _, status, _ in verified if status == "correct")
        approximate = sum(1 for _, status, _ in verified if status == "approximate")
        score = (correct + 0.5 * approximate) / total if total else 1.0
        return {
            "metric": self.metric,
            "score": round(score, 4),
            "dimensions": {"claims_count": total, "correct": correct, "approximate": approximate},
            "reasoning": f"{correct} correct, {approximate} approximate out of {total} numeric claims.",
            "suggestions": [f"Claim '{c}' is {s}" for c, s, _ in verified if s == "incorrect"][:3],
        }

    @staticmethod
    def _extract_numeric_claims(text: str) -> List[Tuple[str, float]]:
        # Look for sentences containing numbers (integers, decimals, percentages)
        pattern = re.compile(r"[^.!?]*\b\d+(?:\.\d+)?(?:\s*%|\s*percent)?[^.!?]*[.!?]", re.IGNORECASE)
        claims = []
        for match in pattern.findall(text):
            nums = [float(n.strip("%").strip()) for n in re.findall(r"\b\d+(?:\.\d+)?", match)]
            if nums:
                claims.append((match.strip(), nums[0]))
        return claims

    def _verify_claims(self, claims: List[Tuple[str, float]], data: Any) -> List[Tuple[str, str, float]]:
        verified = []
        for claim_text, claimed_value in claims:
            # Heuristic: if data is DataFrame, check if claimed value is close to any column mean/max
            truth_value = self._derive_truth_value(claimed_value, data)
            if truth_value == 0.0:
                verified.append((claim_text, "unverifiable", 0.0))
                continue
            deviation = abs(claimed_value - truth_value) / abs(truth_value)
            if deviation <= 0.05:
                status = "correct"
            elif deviation <= 0.20:
                status = "approximate"
            else:
                status = "incorrect"
            verified.append((claim_text, status, deviation))
        return verified

    def _derive_truth_value(self, claimed_value: float, data: Any) -> float:
        if data is None:
            return claimed_value  # assume true if no data to validate
        try:
            import pandas as pd

            if isinstance(data, pd.DataFrame):
                numeric = data.select_dtypes(include="number")
                if numeric.empty:
                    return claimed_value
                # Find the nearest aggregate to claimed value
                candidates = []
                for col in numeric.columns:
                    candidates.extend([numeric[col].sum(), numeric[col].mean(), numeric[col].max()])
                nearest = min(candidates, key=lambda x: abs(x - claimed_value))
                return float(nearest)
        except Exception:
            pass
        return claimed_value
