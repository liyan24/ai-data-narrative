"""Build the final evaluation report from metric scores."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ai_data_narrative.config import grade_from_score
from ai_data_narrative.models import AggregatedScore, EvaluationReport


class EvaluationReportBuilder:
    """Aggregate metric scores and produce Markdown + JSON reports."""

    METRIC_WEIGHTS = {
        "IC": 0.20,
        "FA": 0.25,
        "NC": 0.20,
        "CP": 0.15,
        "SF": 0.20,
    }

    METRIC_NAMES = {
        "IC": "信息完整性",
        "FA": "事实准确性",
        "NC": "叙事连贯性",
        "CP": "可理解性",
        "SF": "结构保真度",
    }

    def __init__(self, pass_threshold: float = 0.60):
        self.pass_threshold = pass_threshold

    def build(
        self,
        metric_scores: Dict[str, AggregatedScore],
        strengths: List[str] | None = None,
        weaknesses: List[str] | None = None,
        improvements: List[str] | None = None,
    ) -> EvaluationReport:
        overall = sum(
            self.METRIC_WEIGHTS.get(m, 0.0) * s.weighted
            for m, s in metric_scores.items()
        )
        overall = round(overall, 4)
        grade = grade_from_score(overall)
        return EvaluationReport(
            overall_score=overall,
            grade=grade,
            passed=overall >= self.pass_threshold,
            pass_threshold=self.pass_threshold,
            metrics=metric_scores,
            strengths=strengths or [],
            weaknesses=weaknesses or [],
            improvements=improvements or [],
        )

    def to_markdown(self, report: EvaluationReport) -> str:
        lines = [
            "# 质量评估报告",
            "",
            f"**综合得分:** {report.overall_score:.2f}  ",
            f"**等级:** {report.grade}  ",
            f"**是否通过:** {'通过' if report.passed else '未通过'} (阈值 {report.pass_threshold})",
            "",
            "## 指标得分",
            "",
            "| 指标 | 得分 | 标准差 | 一致性 |",
            "|------|------|--------|--------|",
        ]
        for metric, agg in report.metrics.items():
            name = self.METRIC_NAMES.get(metric, metric)
            lines.append(f"| {name} ({metric}) | {agg.weighted:.2f} | {agg.std:.2f} | {agg.consensus} |")
        lines.extend(["", "## 优势", ""])
        for s in report.strengths or ["暂无"]:
            lines.append(f"- {s}")
        lines.extend(["", "## 劣势", ""])
        for w in report.weaknesses or ["暂无"]:
            lines.append(f"- {w}")
        lines.extend(["", "## 改进建议", ""])
        for i in report.improvements or ["暂无"]:
            lines.append(f"- {i}")
        return "\n".join(lines)

    def to_json(self, report: EvaluationReport) -> str:
        return json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
