"""Base agent implementation."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ai_data_narrative.interfaces import BaseAgent, BaseLLMProvider, BaseSkill
from ai_data_narrative.models import AgentOutput, AgentPlan, ReportFragment, ReviewResult


class Agent(BaseAgent):
    """Concrete base agent with JSON-mode LLM helpers."""

    name = "agent"
    role = "base"
    system_prompt = "You are a helpful assistant."

    def _ask_json(
        self,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = self.llm.complete(messages, json_mode=True, temperature=temperature, max_tokens=max_tokens)
        if isinstance(result, dict):
            return result
        try:
            return json.loads(result)
        except Exception:
            return {"raw": result}

    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        return AgentPlan(agent_name=self.name, goal="", steps=[], expected_output={})

    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        raise NotImplementedError

    def review(self, output: AgentOutput) -> ReviewResult:
        # Default naive review
        return ReviewResult(passed=output.status.value != "FAILED", score=0.8)

    def report(self, output: AgentOutput) -> ReportFragment:
        return ReportFragment(
            title=self.name,
            content=json.dumps(output.artifacts, ensure_ascii=False, indent=2),
            kind="json",
        )
