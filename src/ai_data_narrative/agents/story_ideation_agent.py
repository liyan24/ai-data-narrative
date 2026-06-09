"""StoryIdeationAgent: Step 4 - Craft narrative framework from data insights."""
from __future__ import annotations

import json
from typing import Any, Dict

from ai_data_narrative.agents.base import Agent
from ai_data_narrative.llm.prompts import STORY_IDEATION_SYSTEM
from ai_data_narrative.models import AgentOutput, AgentPlan


class StoryIdeationAgent(Agent):
    name = "story_ideation"
    role = "data story ideation expert"
    system_prompt = STORY_IDEATION_SYSTEM

    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        return AgentPlan(
            agent_name=self.name,
            goal="基于数据洞察提炼叙事框架",
            steps=["提取关键洞察", "提炼核心观点", "构建故事板"],
            expected_output={
                "big_idea": "string",
                "elevator_pitch": "string",
                "storyboard": "array",
            },
        )

    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        prev = context.get("previous_output", {})
        insights = prev.get("insights", [])
        findings = prev.get("findings", 0)
        data_desc = context.get("data_description", {})

        prompt = f"""故事构思任务。

【数据洞察】（从中提炼叙事核心）：
{json.dumps(insights, ensure_ascii=False, indent=2, default=str)}

【数据描述】：
{json.dumps(data_desc, ensure_ascii=False, indent=2, default=str)}

请基于以上数据洞察，提炼出最有力的叙事框架。
核心观点必须基于数据洞察，不能编造数据。

请返回符合指令要求的结构化 JSON。"""
        result = self._ask_json(prompt)
        return AgentOutput(
            agent_name=self.name,
            artifacts={
                "big_idea": result.get("big_idea", ""),
                "elevator_pitch": result.get("elevator_pitch", ""),
                "storyboard": result.get("storyboard", []),
                "insights_used": insights,
            },
            reasoning="已基于数据洞察提炼出叙事框架。",
        )
