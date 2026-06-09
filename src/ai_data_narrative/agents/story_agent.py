"""StorytellingAgent: Step 5 - Build final narrative report with text and charts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from ai_data_narrative.agents.base import Agent
from ai_data_narrative.llm.prompts import STORYTELLING_SYSTEM
from ai_data_narrative.models import AgentOutput, AgentPlan


class StorytellingAgent(Agent):
    name = "storytelling"
    role = "data storyteller"
    system_prompt = STORYTELLING_SYSTEM

    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        return AgentPlan(
            agent_name=self.name,
            goal="编译最终数据叙事报告（文本 + 图表）",
            steps=["提取故事构思", "提取可视化图表", "起草三幕结构", "嵌入图表", "输出完整报告"],
            expected_output={
                "big_idea": "string",
                "elevator_pitch": "string",
                "act1_setup": "string",
                "act2_conflict": "string",
                "act3_resolution": "string",
                "report": "string",
                "key_takeaways": "array",
            },
        )

    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        ideation = context.get("story_ideation_output", {})
        viz = context.get("visualization_output", {})

        # Extract story ideation artifacts
        big_idea = ideation.get("big_idea", "")
        elevator_pitch = ideation.get("elevator_pitch", "")
        storyboard = ideation.get("storyboard", [])
        findings = ideation.get("findings_used", [])

        # Extract visualization artifacts
        viz_files = viz.get("files", []) or []
        chart_type = viz.get("chart_type", "")
        chart_title = viz.get("title", "")
        viz_findings = viz.get("findings_used", [])

        # Build a clear instruction about chart files
        file_instructions = ""
        if viz_files:
            file_instructions = (
                "\n【图表文件路径】（必须在报告中使用 Markdown 图片语法嵌入）：\n"
                + "\n".join(f'- 在适当位置插入: ![{Path(f).name}]({f})' for f in viz_files)
                + "\n\n强制要求：report 字段中必须至少包含一次 ![](path) 形式的图片引用。"
            )

        prompt = f"""叙事构建任务：请基于故事构思和可视化图表，编写最终的数据叙事报告。

【核心观点】：
{big_idea}

【三分钟故事（电梯演讲）】：
{elevator_pitch}

【故事板】：
{json.dumps(storyboard, ensure_ascii=False, indent=2, default=str)}

【数据分析发现】：
{json.dumps(viz_findings or findings, ensure_ascii=False, indent=2, default=str)}

【可视化图表信息】：
- 类型: {chart_type}
- 标题: {chart_title}
{file_instructions}

重要要求：
1. 报告内容必须基于上面的真实分析结果，不能编造数据。
2. 使用三幕叙事结构（铺垫 → 冲突 → 解决）。
3. 使用 Markdown 格式。
4. 所有内容请使用中文。
5. 报告应包含：核心观点（开头突出显示）、三分钟故事、完整叙事正文、关键要点。
6. 报告正文中必须嵌入可视化图表，使用 Markdown 图片语法 ![](path)。

请返回符合指令要求的结构化 JSON。"""
        result = self._ask_json(prompt)

        report = result.get("report", "")

        # Force image embedding if LLM forgot
        report = self._ensure_images_embedded(report, viz_files)

        return AgentOutput(
            agent_name=self.name,
            artifacts={
                "big_idea": result.get("big_idea", big_idea),
                "elevator_pitch": result.get("elevator_pitch", elevator_pitch),
                "act1_setup": result.get("act1_setup", ""),
                "act2_conflict": result.get("act2_conflict", ""),
                "act3_resolution": result.get("act3_resolution", ""),
                "report": report,
                "key_takeaways": result.get("key_takeaways", []),
                "embedded_files": viz_files,
            },
            reasoning="基于故事构思和可视化图表编译了最终叙事报告。",
        )

    @staticmethod
    def _ensure_images_embedded(report: str, viz_files: list[str]) -> str:
        """If report doesn't contain image markdown, append charts at the end."""
        if not viz_files:
            return report
        # Check if report already contains markdown image tags
        if re.search(r"!\[.*?\]\(.+?\)", report):
            return report
        # Append charts to report
        appendix = "\n\n---\n\n## 可视化图表\n\n"
        for f in viz_files:
            appendix += f"![{Path(f).name}]({f})\n\n"
        return report + appendix
