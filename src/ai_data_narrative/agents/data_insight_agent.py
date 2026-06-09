"""DataInsightAgent: extracts actionable insights from analysis findings,
generates supporting data subsets for visualization and storytelling.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from ai_data_narrative.agents.base import Agent
from ai_data_narrative.models import AgentOutput, AgentPlan, SkillPlan


DATA_INSIGHT_SYSTEM = """你是一位资深数据洞察专家。你的任务是从数据分析结果中提炼出最有价值的故事线索，
并为每个洞察提取支撑该洞察的原始数据子集，确保后续可视化能直接基于这些数据绘制图表。

请用中文回复，并返回包含以下字段的合法 JSON：
- insights: 洞察数组，每项包含：
  - title: 洞察标题（一句话概括）
  - description: 洞察描述（2-4句话，解释为什么这个发现重要）
  - insight_type: 洞察类型（trend / distribution / correlation / comparison / anomaly / network_centrality / ranking）
  - supporting_data: 支撑数据对象，必须包含足够绘制图表的原始数据，结构如下：
    - viz_type: 推荐图表类型（line / bar / scatter / pie / network / heatmap）
    - x_label / y_label: 坐标轴标签
    - series / categories / values / nodes / edges 等：根据 viz_type 提供对应的结构化数据
  - recommended_chart: 推荐的图表类型
  - priority: 优先级（high / medium / low）
"""


class DataInsightAgent(Agent):
    name = "data_insight"
    role = "data insight extractor"
    system_prompt = DATA_INSIGHT_SYSTEM

    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        return AgentPlan(
            agent_name=self.name,
            goal="从分析结果中提取洞察并生成支撑数据",
            steps=["审阅分析发现", "提炼关键洞察", "提取支撑数据", "验证数据完整性"],
            expected_output={"insights": "array"},
        )

    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        prev = context.get("previous_output", {})
        findings = prev.get("findings", [])
        analysis_plan = prev.get("analysis_plan", {})
        data = context.get("data")
        data_desc = context.get("data_description", {})
        data_summary = self._summarize_data(data, data_desc)

        # Step 1: Ask LLM to identify insights and describe supporting data needs
        prompt = f"""数据洞察任务。

【数据分析发现】：
{json.dumps(findings, ensure_ascii=False, indent=2, default=str)}

【分析计划】：
{json.dumps(analysis_plan, ensure_ascii=False, indent=2, default=str)}

【数据结构摘要】：
{data_summary}

请基于以上分析结果，完成以下工作：
1. 从 findings 中选出 1-3 个最有价值的洞察
2. 为每个洞察描述需要什么样的支撑数据来绘制图表
3. 不要编造数据，支撑数据必须从原始数据中衍生

请返回 JSON，包含 insights 数组。每个洞察的 supporting_data 字段可以先描述需要的结构和字段名，具体数值留空（会在下一步通过代码填充）。"""

        result = self._ask_json(prompt)
        insights = result.get("insights", [])

        # Step 2: Generate code to extract supporting_data from raw data for each insight
        if insights and data is not None:
            code = self._build_extraction_code(insights, data, data_desc)
            if code:
                skill = self.get_skill("data_analysis")
                if skill:
                    sp = SkillPlan(skill_name="data_analysis", intent="extract supporting data", code=code, parameters={})
                    skill_result = skill.execute(sp, {"data": data})
                    if skill_result.success and skill_result.return_value is not None:
                        extracted = skill_result.return_value
                        if isinstance(extracted, dict) and "insights" in extracted:
                            insights = extracted["insights"]
                        result["skill_execution"] = {
                            "success": True,
                            "stdout": skill_result.stdout,
                            "stderr": skill_result.stderr,
                        }
                    else:
                        result["skill_execution"] = {
                            "success": False,
                            "stderr": skill_result.stderr,
                            "stdout": skill_result.stdout,
                        }

        return AgentOutput(
            agent_name=self.name,
            artifacts={
                "insights": insights,
                "findings_count": len(findings),
                "analysis_plan": analysis_plan,
            },
            reasoning=f"从 {len(findings)} 条发现中提炼了 {len(insights)} 个关键洞察，并提取了支撑数据。",
        )

    @staticmethod
    def _build_extraction_code(insights: list[dict], data: Any, data_desc: dict) -> str | None:
        """Generate Python code to extract supporting_data from raw data."""
        insights_json = json.dumps(insights, ensure_ascii=False, indent=2, default=str)

        return f"""import pandas as pd
import numpy as np
import json

data = data
result = {{"insights": []}}

insights_meta = {insights_json}

for idx, meta in enumerate(insights_meta):
    itype = meta.get("insight_type", "")
    viz = meta.get("supporting_data", {{}}).get("viz_type", "")
    insight = {{"title": meta.get("title", ""), "description": meta.get("description", ""), "insight_type": itype, "priority": meta.get("priority", "medium"), "supporting_data": {{"viz_type": viz}}}}
    
    try:
        if isinstance(data, pd.DataFrame):
            df = data
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            time_col = None
            for c in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[c]) or any(kw in str(c).lower() for kw in ['date', 'time', '日期', '时间']):
                    time_col = c
            
            if viz == "line" and time_col and numeric_cols:
                col = numeric_cols[0]
                sub = df[[time_col, col]].dropna().sort_values(time_col)
                insight["supporting_data"] = {{
                    "viz_type": "line",
                    "x_label": str(time_col),
                    "y_label": str(col),
                    "series": [{{"name": str(col), "x": sub[time_col].astype(str).tolist()[:50], "y": sub[col].tolist()[:50]}}]
                }}
            elif viz == "bar" and cat_cols and numeric_cols:
                cat = cat_cols[0]
                num = numeric_cols[0]
                grouped = df.groupby(cat)[num].sum().sort_values(ascending=False).head(10)
                insight["supporting_data"] = {{
                    "viz_type": "bar",
                    "x_label": str(cat),
                    "y_label": str(num),
                    "categories": grouped.index.tolist(),
                    "values": grouped.values.tolist(),
                }}
            elif viz == "scatter" and len(numeric_cols) >= 2:
                x, y = numeric_cols[0], numeric_cols[1]
                sub = df[[x, y]].dropna()
                insight["supporting_data"] = {{
                    "viz_type": "scatter",
                    "x_label": str(x),
                    "y_label": str(y),
                    "x_values": sub[x].tolist()[:100],
                    "y_values": sub[y].tolist()[:100],
                }}
            elif viz == "heatmap" and len(numeric_cols) >= 2:
                corr = df[numeric_cols].corr().round(4)
                insight["supporting_data"] = {{
                    "viz_type": "heatmap",
                    "x_label": "",
                    "y_label": "",
                    "labels": corr.columns.tolist(),
                    "matrix": corr.values.tolist(),
                }}
            else:
                # fallback: first numeric column distribution
                if numeric_cols:
                    col = numeric_cols[0]
                    vc = df[col].value_counts(bins=10).sort_index()
                    insight["supporting_data"] = {{
                        "viz_type": "bar",
                        "x_label": str(col) + " 区间",
                        "y_label": "频数",
                        "categories": [str(i) for i in vc.index.tolist()],
                        "values": vc.values.tolist(),
                    }}
        
        elif isinstance(data, dict) and "nodes" in data and "edges" in data:
            import networkx as nx
            nodes = data["nodes"]
            edges = data["edges"]
            G = nx.Graph()
            for n in nodes:
                G.add_node(n.get("id", n))
            for e in edges:
                G.add_edge(e["source"], e["target"])
            
            if viz in ("bar", "ranking"):
                dc = nx.degree_centrality(G)
                top = sorted(dc.items(), key=lambda x: -x[1])[:10]
                insight["supporting_data"] = {{
                    "viz_type": "bar",
                    "x_label": "节点",
                    "y_label": "度中心性",
                    "categories": [t[0] for t in top],
                    "values": [round(t[1], 4) for t in top],
                }}
            else:
                # network graph
                insight["supporting_data"] = {{
                    "viz_type": "network",
                    "nodes": [{{"id": n.get("id", i), "label": n.get("label", n.get("id", i)), "type": n.get("type", "")}} for i, n in enumerate(nodes[:30])],
                    "edges": [{{"source": e["source"], "target": e["target"], "type": e.get("type", "")}} for e in edges[:50]],
                }}
        
        elif isinstance(data, list):
            # JSON array
            if viz == "bar":
                # try to find a numeric field
                numeric_keys = set()
                for item in data[:50]:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if isinstance(v, (int, float)) and not isinstance(v, bool):
                                numeric_keys.add(k)
                if numeric_keys:
                    k = list(numeric_keys)[0]
                    values = [item.get(k, 0) for item in data if isinstance(item, dict)]
                    insight["supporting_data"] = {{
                        "viz_type": "bar",
                        "x_label": "记录序号",
                        "y_label": str(k),
                        "categories": [str(i) for i in range(min(len(values), 20))],
                        "values": values[:20],
                    }}
    except Exception as e:
        insight["supporting_data_error"] = str(e)
    
    result["insights"].append(insight)

print(json.dumps(result, ensure_ascii=False, indent=2))
"""

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
                    "sample": data.head(2).to_dict(orient="records"),
                }
                return json.dumps(summary, ensure_ascii=False, indent=2, default=str)
            if isinstance(data, dict) and "nodes" in data and "edges" in data:
                return json.dumps({
                    "type": "network",
                    "node_count": len(data["nodes"]),
                    "edge_count": len(data["edges"]),
                }, ensure_ascii=False)
            if isinstance(data, list):
                return json.dumps({"type": "array", "length": len(data), "sample": data[:1]}, ensure_ascii=False, default=str)
            return f"数据类型: {type(data).__name__}"
        except Exception as exc:
            return f"无法汇总数据: {exc}"
