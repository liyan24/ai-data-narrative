"""Tests for agents using mock LLM."""
import pytest

from ai_data_narrative.agents import (
    CodeReviewAgent,
    ContextAnalysisAgent,
    DataAnalysisAgent,
    StoryIdeationAgent,
    StorytellingAgent,
    VisualizationDesignAgent,
)
from ai_data_narrative.llm import MockProvider
from ai_data_narrative.models import AgentInput
from ai_data_narrative.skills import DataAnalysisSkill, DataStorytellingSkill, DataVisualizationSkill


@pytest.fixture
def mock_llm():
    return MockProvider()


def test_context_analysis_agent(mock_llm):
    agent = ContextAnalysisAgent(llm=mock_llm)
    inp = AgentInput(user_request="Tell a story about revenue", background="Q3 report", audience="executives")
    out = agent.run({"input": inp.model_dump()})
    assert "context_brief" in out.artifacts
    assert out.artifacts["context_brief"]


def test_data_analysis_agent(mock_llm):
    skill = DataAnalysisSkill(llm=mock_llm)
    agent = DataAnalysisAgent(llm=mock_llm, skills=[skill])
    out = agent.run({"data": None, "previous_output": {"big_idea": "Revenue story"}})
    assert "findings" in out.artifacts


def test_story_ideation_agent(mock_llm):
    agent = StoryIdeationAgent(llm=mock_llm)
    out = agent.run({"previous_output": {"findings": [{"metric": "x", "value": 1}]}, "data_description": {}})
    assert "big_idea" in out.artifacts
    assert "elevator_pitch" in out.artifacts
    assert "storyboard" in out.artifacts


def test_visualization_agent(mock_llm):
    skill = DataVisualizationSkill(llm=mock_llm)
    agent = VisualizationDesignAgent(llm=mock_llm, skills=[skill])
    out = agent.run({"data": None, "previous_output": {"findings": []}})
    assert "chart_type" in out.artifacts


def test_storytelling_agent(mock_llm):
    skill = DataStorytellingSkill(llm=mock_llm)
    agent = StorytellingAgent(llm=mock_llm, skills=[skill])
    ideation = {"big_idea": "x", "elevator_pitch": "y", "storyboard": []}
    viz = {"files": ["/tmp/chart.png"], "chart_type": "bar", "title": "test"}
    out = agent.run({"story_ideation_output": ideation, "visualization_output": viz})
    assert "report" in out.artifacts


def test_code_review_agent(mock_llm):
    agent = CodeReviewAgent(llm=mock_llm)
    out = agent.run({"code": "x = 1 + 2"})
    assert "passed" in out.artifacts
