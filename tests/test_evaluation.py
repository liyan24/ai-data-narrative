"""Tests for evaluation framework."""
import pytest

from ai_data_narrative.evaluation import (
    ComprehensibilityEvaluator,
    EvaluationReportBuilder,
    FactualAccuracyEvaluator,
    InformationCompletenessEvaluator,
    MultiLLMJudge,
    NarrativeCoherenceEvaluator,
    StructuralFidelityEvaluator,
)
from ai_data_narrative.llm import MockProvider


SAMPLE_REPORT = """
# Revenue Analysis

## Introduction
We analyzed customer revenue data for Q3.

## Method
We segmented customers by revenue contribution.

## Findings
The top 20% of customers generate 78% of revenue.

## Conclusion
We recommend targeted retention programs.
"""


def test_ic_evaluator():
    ev = InformationCompletenessEvaluator()
    raw = ev.evaluate(SAMPLE_REPORT, None)
    assert raw["score"] > 0.7
    assert raw["dimensions"]["背景"] == 1.0


def test_fa_evaluator():
    ev = FactualAccuracyEvaluator()
    raw = ev.evaluate("Total revenue is 100. The top share is 78%.", None)
    assert 0.0 <= raw["score"] <= 1.0
    assert raw["dimensions"]["claims_count"] >= 1


def test_nc_evaluator():
    ev = NarrativeCoherenceEvaluator()
    raw = ev.evaluate(SAMPLE_REPORT, None)
    assert raw["score"] > 0.5


def test_cp_evaluator():
    ev = ComprehensibilityEvaluator()
    raw = ev.evaluate(SAMPLE_REPORT, None)
    assert 0.0 <= raw["score"] <= 1.0


def test_sf_evaluator():
    ev = StructuralFidelityEvaluator()
    raw = ev.evaluate(SAMPLE_REPORT, None)
    assert 0.0 <= raw["score"] <= 1.0


def test_multi_llm_judge():
    providers = [MockProvider()]
    judge = MultiLLMJudge(providers)
    agg = judge.score_metric("IC", SAMPLE_REPORT, "Evaluate completeness for {metric}.\n{report}")
    assert 0.0 <= agg.weighted <= 1.0
    assert agg.judge_scores


def test_report_builder():
    providers = [MockProvider()]
    judge = MultiLLMJudge(providers)
    metrics = {
        "IC": judge.score_metric("IC", SAMPLE_REPORT, "Score {metric}.\n{report}"),
        "FA": judge.score_metric("FA", SAMPLE_REPORT, "Score {metric}.\n{report}"),
        "NC": judge.score_metric("NC", SAMPLE_REPORT, "Score {metric}.\n{report}"),
        "CP": judge.score_metric("CP", SAMPLE_REPORT, "Score {metric}.\n{report}"),
        "SF": judge.score_metric("SF", SAMPLE_REPORT, "Score {metric}.\n{report}"),
    }
    builder = EvaluationReportBuilder(pass_threshold=0.60)
    report = builder.build(metrics)
    assert report.overall_score >= 0.0
    assert report.grade
    md = builder.to_markdown(report)
    assert "综合得分" in md
