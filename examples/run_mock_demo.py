"""Demo script that runs the full workflow with MockProvider (no API keys)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from ai_data_narrative.llm import MockProvider
from ai_data_narrative.models import AgentInput
from ai_data_narrative.workflow.workflow_engine import WorkflowEngine


def main():
    llm = MockProvider()
    engine = WorkflowEngine(llm=llm)

    df = pd.DataFrame({
        "product": ["A", "B", "C", "D"],
        "sales": [120, 200, 150, 300],
        "profit": [30, 50, 20, 80],
    })

    inp = AgentInput(
        user_request="Analyze sales performance and tell a compelling story",
        background="Q3 internal review",
        audience="executive team",
        data=df,
        data_description={"shape": df.shape, "columns": list(df.columns)},
    )

    result = engine.run(inp)
    print("=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(result.final_report)
    print("=" * 60)
    if result.evaluation:
        print(f"Overall score: {result.evaluation.overall_score}")
        print(f"Grade: {result.evaluation.grade}")
        print(f"Passed: {result.evaluation.passed}")
        print(f"Output dir: {result.output_dir}")


if __name__ == "__main__":
    main()
