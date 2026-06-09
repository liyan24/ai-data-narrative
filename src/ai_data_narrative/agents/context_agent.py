"""ContextAnalysisAgent: Step 1 - Understand audience and context."""
from __future__ import annotations

from typing import Any, Dict

from ai_data_narrative.agents.base import Agent
from ai_data_narrative.llm.prompts import CONTEXT_ANALYSIS_SYSTEM
from ai_data_narrative.models import AgentOutput, AgentPlan


class ContextAnalysisAgent(Agent):
    name = "context_analysis"
    role = "background and strategy analyst"
    system_prompt = CONTEXT_ANALYSIS_SYSTEM

    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        user = context.get("input", {})
        return AgentPlan(
            agent_name=self.name,
            goal=f"分析背景与受众策略: {user.get('user_request', '')[:120]}",
            steps=[" summarize audience", "formulate communication strategy", "summarize context"],
            expected_output={"context_brief": "object"},
        )

    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        user = context.get("input", {})
        prompt = f"""背景分析任务。

用户请求: {user.get('user_request', '')}
背景信息: {user.get('background', '')}
目标受众: {user.get('audience', '')}
数据描述: {user.get('data_description', {})}

请返回符合指令要求的结构化 JSON。"""
        result = self._ask_json(prompt)
        return AgentOutput(
            agent_name=self.name,
            artifacts={
                "context_brief": result.get("context_brief", {}),
                "plan": plan.model_dump(),
            },
            reasoning="已分析受众画像和沟通策略。",
        )
