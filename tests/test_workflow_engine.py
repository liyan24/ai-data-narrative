"""Integration test for the workflow engine with mock LLM."""
import os

import pandas as pd

from ai_data_narrative.llm import MockProvider
from ai_data_narrative.models import AgentInput
from ai_data_narrative.workflow.workflow_engine import WorkflowEngine


def test_workflow_engine_end_to_end(tmp_path):
    llm = MockProvider()
    engine = WorkflowEngine(llm=llm, output_dir=str(tmp_path))
    df = pd.DataFrame({"customer": ["A", "B", "C"], "revenue": [100, 200, 300]})
    inp = AgentInput(
        user_request="Analyze revenue by customer",
        background="Sample data",
        audience="executives",
        data=df,
        data_description={"columns": ["customer", "revenue"]},
    )
    result = engine.run(inp)
    assert result.output_dir
    assert result.final_report
    assert any(t.status.value == "COMPLETED" for t in result.tasks)
    assert os.path.exists(os.path.join(result.output_dir, "report.md"))
