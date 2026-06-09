"""VisualizationDesignAgent: Step 5 - Generate publication-ready chart in one pass."""
from __future__ import annotations

import json
from typing import Any, Dict

from ai_data_narrative.agents.base import Agent
from ai_data_narrative.llm.prompts import VISUALIZATION_SYSTEM
from ai_data_narrative.models import AgentOutput, AgentPlan, SkillPlan, SkillOutput


class VisualizationDesignAgent(Agent):
    name = "visualization_design"
    role = "data visualization designer"
    system_prompt = VISUALIZATION_SYSTEM

    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        return AgentPlan(
            agent_name=self.name,
            goal="生成融合去杂乱、聚焦、设计原则的最终可视化图表",
            steps=["分析数据洞察", "选择图表类型", "生成 matplotlib 代码", "渲染图表"],
            expected_output={"chart_type": "string", "title": "string", "rationale": "string", "accessibility_notes": "string", "code": "string"},
        )

    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        prev = context.get("previous_output", {})
        insights = prev.get("insights", [])
        findings = prev.get("findings", [])

        # Pick the highest-priority insight to visualize
        primary_insight = None
        supporting_data = None
        if insights:
            # Sort by priority: high > medium > low
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_insights = sorted(insights, key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
            primary_insight = sorted_insights[0]
            supporting_data = primary_insight.get("supporting_data", {})

        data_summary = self._summarize_data(context.get("data"), context.get("data_description", {}))

        # Build prompt based on whether we have structured supporting_data
        if supporting_data:
            viz_type = supporting_data.get("viz_type", "bar")
            prompt = f"""可视化任务。

【核心洞察】：
标题: {primary_insight.get('title', '')}
描述: {primary_insight.get('description', '')}
类型: {primary_insight.get('insight_type', '')}

【支撑数据】（图表必须基于这些真实数据绘制）：
{json.dumps(supporting_data, ensure_ascii=False, indent=2, default=str)}

【数据结构摘要】：
{data_summary}

重要约束：
1. 图表必须直接基于上面的【支撑数据】来绘制，禁止编造数据。
2. 生成的 Python 代码必须使用注入的 `supporting_data` 变量来获取绘图数据。
3. 图表标题和标签请使用中文，并反映洞察的含义。
4. 代码必须将图表保存到 `OUTPUT_DIR + '/chart.png'`。
5. 使用 matplotlib，并在代码开头设置中文字体支持：
   plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans SC']
   plt.rcParams['axes.unicode_minus'] = False
6. 如果支撑数据是 network 类型（包含 nodes 和 edges），请使用 networkx 绘制关系网络图。

请返回符合指令要求的结构化 JSON。"""
        else:
            # Fallback to using raw findings
            prompt = f"""可视化任务。

【数据分析发现】（图表必须体现这些发现）：
{json.dumps(findings, ensure_ascii=False, indent=2, default=str)}

【数据结构摘要】：
{data_summary}

重要约束：
1. 图表必须直接反映上述数据分析发现，标题、坐标轴、图例都要围绕发现来设计。
2. 生成的 Python 代码必须使用注入的 `data` 变量来获取数据，禁止从文件读取。
3. 代码中使用的列名/键名必须来自上面【数据结构摘要】中列出的实际列名，禁止编造不存在的列名。
4. 如果需要的列不存在，请使用实际存在的列生成一个相关的图表，而不是画一个无关的示例图。
5. 图表标题和标签请使用中文。
6. 代码必须将图表保存到 `OUTPUT_DIR + '/chart.png'`。
7. 使用 matplotlib，并在代码开头设置中文字体支持：
   plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans SC']
   plt.rcParams['axes.unicode_minus'] = False
8. 如果数据是网络图（包含 nodes 和 edges），请使用 networkx 绘制关系网络图。

请返回符合指令要求的结构化 JSON。"""

        result = self._ask_json(prompt)
        code = result.get("code", "")
        files: list[str] = []
        skill_exec_info: Dict[str, Any] = {}

        if code:
            skill = self.get_skill("data_viz")
            if skill:
                sp = SkillPlan(
                    skill_name="data_viz",
                    intent="final chart",
                    code=code,
                    parameters={},
                )
                # Inject both data and supporting_data so the code can use whichever is referenced
                skill_context = {
                    "data": context.get("data"),
                    "supporting_data": supporting_data,
                    "findings": findings,
                    "data_description": context.get("data_description", {}),
                }
                skill_result: SkillOutput = skill.execute(sp, skill_context)
                files = skill_result.files
                skill_exec_info = {
                    "success": skill_result.success,
                    "stdout": skill_result.stdout,
                    "stderr": skill_result.stderr,
                    "files": skill_result.files,
                }

                # Retry with LLM fix if execution failed
                if not skill_result.success:
                    fixed = self._fix_code(code, skill_result.stderr or skill_result.stdout, data_summary)
                    if fixed:
                        sp2 = SkillPlan(
                            skill_name="data_viz",
                            intent="fixed chart",
                            code=fixed,
                            parameters={},
                        )
                        skill_result2: SkillOutput = skill.execute(sp2, skill_context)
                        if skill_result2.success:
                            files = skill_result2.files
                            code = fixed
                            skill_exec_info = {
                                "success": True,
                                "stdout": skill_result2.stdout,
                                "stderr": skill_result2.stderr,
                                "files": skill_result2.files,
                                "retried": True,
                            }
                        else:
                            skill_exec_info["retried"] = True
                            skill_exec_info["retry_stderr"] = skill_result2.stderr

                result["skill_execution"] = skill_exec_info

        return AgentOutput(
            agent_name=self.name,
            artifacts={
                **result,
                "code": code,
                "files": files,
                "primary_insight": primary_insight,
                "supporting_data": supporting_data,
            },
            reasoning="已基于数据洞察生成最终可视化图表（融合去杂乱、聚焦、设计原则）。",
        )

    def _fix_code(self, code: str, error: str, data_summary: str) -> str | None:
        """Ask LLM to fix failing visualization code."""
        prompt = f"""之前生成的 matplotlib 可视化代码执行失败了，请修复它。

【执行错误信息】：
{error}

【数据结构】：
{data_summary}

【原始代码】：
```python
{code}
```

修复要求：
1. 错误很可能是因为使用了不存在的列名/键名。请根据数据结构摘要使用实际存在的列名。
2. 保持图表围绕数据分析发现来设计。
3. 代码必须使用注入的 `data` 或 `supporting_data` 变量，保存到 `OUTPUT_DIR + '/chart.png'`。
4. 设置中文字体支持。

请只返回修复后的 Python 代码（在 Markdown python 代码块中）。"""
        try:
            from ai_data_narrative.utils.code_extractor import first_python_code
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]
            result = self.llm.complete(messages, json_mode=False, temperature=0.2, max_tokens=4000)
            text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
            fixed = first_python_code(text)
            if fixed:
                return fixed
            if isinstance(result, dict):
                return result.get("code", text)
            return text
        except Exception:
            return None

    @staticmethod
    def _summarize_data(data: Any, data_description: Dict[str, Any]) -> str:
        if data is None:
            return "未提供数据。"
        try:
            import pandas as pd

            if isinstance(data, pd.DataFrame):
                summary = {
                    "type": "DataFrame",
                    "shape": data.shape,
                    "columns": list(data.columns),
                    "dtypes": {c: str(t) for c, t in data.dtypes.items()},
                    "head": data.head(3).to_dict(orient="records"),
                    "metadata": data_description or {},
                }
                return json.dumps(summary, ensure_ascii=False, indent=2, default=str)
            if isinstance(data, dict) and "nodes" in data and "edges" in data:
                return json.dumps(
                    {"type": "network", "node_count": len(data["nodes"]), "edge_count": len(data["edges"])},
                    ensure_ascii=False,
                )
            if isinstance(data, list):
                return json.dumps({"type": "array", "length": len(data), "sample": data[:2]}, ensure_ascii=False, default=str)
            return f"数据类型: {type(data).__name__}"
        except Exception as exc:
            return f"无法汇总数据: {exc}"
