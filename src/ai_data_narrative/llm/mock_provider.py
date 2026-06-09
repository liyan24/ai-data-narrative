"""Mock LLM provider for testing and offline demos."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ai_data_narrative.llm.base import LLMProvider


class MockProvider(LLMProvider):
    """Returns canned responses based on simple keyword matching.

    Useful for unit tests and when no API keys are available.
    """

    name: str = "mock"
    weight: float = 1.0

    def __init__(self, responses: Dict[str, Any] | None = None):
        self.responses = responses or {}

    def complete(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> str | Dict[str, Any]:
        prompt = "\n".join(m.get("content", "") for m in messages)
        lower = prompt.lower()

        # Simple keyword routing for demo / tests
        # Use explicit task prefixes to avoid collisions with embedded JSON keys.
        if "context analysis task" in lower or "背景分析任务" in lower:
            payload = {
                "context_brief": {
                    "audience_profile": "业务干系人",
                    "communication_strategy": "聚焦收入影响与关键驱动因素",
                    "context_summary": "分析客户细分数据以识别收入增长的关键驱动因素",
                },
            }
        elif "资深数据科学家" in lower or "充分思考该数据适合进行哪些分析" in lower:
            payload = {
                "analysis_plan": {
                    "data_type_detected": "table",
                    "rationale": "数据包含多个数值列和分类列，属于典型的多维表格结构",
                    "methods": [
                        {"method": "描述统计", "purpose": "计算各数值列的均值、标准差等基础统计量", "expected_output": "统计摘要表"},
                        {"method": "相关性分析", "purpose": "识别数值列之间的相关关系", "expected_output": "相关系数矩阵"},
                        {"method": "分组聚合", "purpose": "按分类维度汇总关键指标", "expected_output": "分组汇总表"},
                        {"method": "分布分析", "purpose": "分析各数值列的分布特征和异常值", "expected_output": "分布统计量"},
                        {"method": "异常检测", "purpose": "识别3-sigma和IQR异常值", "expected_output": "异常值列表"},
                        {"method": "缺失值分析", "purpose": "统计缺失值和重复值情况", "expected_output": "缺失值报告"},
                    ],
                },
            }
        elif "data analysis task" in lower or "数据分析任务" in lower:
            payload = {
                "findings": [
                    {"metric": "总收入", "value": 1234567, "description": "统计周期内的总收入"},
                    {"metric": "头部客户占比", "value": 0.78, "description": "前20%客户贡献的收入比例"},
                ],
                "code": (
                    "import pandas as pd\n"
                    "import numpy as np\n"
                    "try:\n"
                    "    df = data\n"
                    "except NameError:\n"
                    "    df = pd.DataFrame({'x':[1,2,3]})\n"
                    "result = {}\n"
                    "if hasattr(df, 'select_dtypes'):\n"
                    "    numeric = df.select_dtypes(include='number')\n"
                    "    for col in numeric.columns:\n"
                    "        result[f'{col}_总和'] = float(numeric[col].sum())\n"
                    "        result[f'{col}_均值'] = float(numeric[col].mean())\n"
                    "        result[f'{col}_标准差'] = float(numeric[col].std())\n"
                    "    cat = df.select_dtypes(exclude='number')\n"
                    "    for col in cat.columns[:3]:\n"
                    "        result[f'{col}_类别数'] = int(df[col].nunique())\n"
                    "else:\n"
                    "    result = {'rows': len(df)}\n"
                    "print(result)"
                ),
            }
        elif "data insight task" in lower or "数据洞察任务" in lower:
            payload = {
                "insights": [
                    {
                        "title": "少数客户驱动大部分收入",
                        "description": "前20%的客户贡献了80%的总收入，集中度极高，需关注留存风险",
                        "insight_type": "concentration",
                        "priority": "high",
                        "recommended_chart": "bar_chart",
                        "supporting_data": {
                            "viz_type": "bar_chart",
                            "categories": ["头部20%", "其他80%"],
                            "values": [0.80, 0.20],
                        },
                    },
                    {
                        "title": "新客户增长但收入停滞",
                        "description": "客户数量在增长，但总收入没有同步增长，说明新客户的质量或转化率存在问题",
                        "insight_type": "trend",
                        "priority": "medium",
                        "recommended_chart": "line_chart",
                        "supporting_data": {
                            "viz_type": "line_chart",
                            "series": [
                                {"name": "客户数", "values": [100, 120, 150, 180, 200]},
                                {"name": "总收入", "values": [500, 510, 520, 525, 530]},
                            ],
                        },
                    },
                ],
            }
        elif "story ideation task" in lower or "故事构思任务" in lower:
            payload = {
                "big_idea": "收入增长由一小部分高价值客户驱动。",
                "elevator_pitch": "我们分析了客户细分数据，发现前20%的客户贡献了80%的收入。建议将资源集中投入到高价值客户的留存计划中，这将带来显著的收入增长。",
                "storyboard": [
                    {"page": 1, "title": "现状概览", "content": "收入分布的总体情况"},
                    {"page": 2, "title": "关键驱动", "content": "前20%客户驱动80%收入"},
                    {"page": 3, "title": "行动建议", "content": "投资高价值客户留存计划"},
                    {"page": 4, "title": "风险分析", "content": "若失去头部客户对收入的影响"},
                    {"page": 5, "title": "实施方案", "content": "三步走执行计划"},
                    {"page": 6, "title": "预期收益", "content": "留存率提升后的收入模拟"},
                    {"page": 7, "title": "下一步", "content": "立即开始试点的关键动作"},
                ],
            }
        elif "visualization task" in lower or "可视化任务" in lower:
            payload = {
                "chart_type": "horizontal_bar",
                "title": "收入分布",
                "rationale": "使用水平条形图清晰展示各客户群体的收入贡献",
                "accessibility_notes": "使用高对比度配色，标签清晰可读",
                "code": (
                    "import matplotlib\n"
                    "matplotlib.use('Agg')\n"
                    "import matplotlib.pyplot as plt\n"
                    "import pandas as pd\n"
                    "plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans SC', 'DejaVu Sans']\n"
                    "plt.rcParams['axes.unicode_minus'] = False\n"
                    "try:\n"
                    "    df = data\n"
                    "except NameError:\n"
                    "    df = pd.DataFrame({'customer':['A','B','C'],'revenue':[100,200,150]})\n"
                    "fig, ax = plt.subplots(figsize=(6,4))\n"
                    "if hasattr(df, 'plot') and 'customer' in df.columns and 'revenue' in df.columns:\n"
                    "    df.set_index('customer')['revenue'].plot(kind='barh', ax=ax, color='#2E5C8A')\n"
                    "else:\n"
                    "    ax.barh(['A','B','C'], [100,200,150], color='#2E5C8A')\n"
                    "ax.set_title('收入分布')\n"
                    "ax.spines['top'].set_visible(False)\n"
                    "ax.spines['right'].set_visible(False)\n"
                    "out_path = OUTPUT_DIR + '/chart.png'\n"
                    "plt.tight_layout()\n"
                    "fig.savefig(out_path, dpi=100)\n"
                    "print('已保存', out_path)"
                ),
            }
        elif "storytelling task" in lower or "叙事构建任务" in lower or "故事讲述" in lower:
            payload = {
                "big_idea": "收入增长由一小部分高价值客户驱动。",
                "elevator_pitch": "我们分析了客户细分数据，发现前20%的客户贡献了80%的收入。建议将资源集中投入到高价值客户的留存计划中。",
                "act1_setup": "尽管客户数量在增长，但收入已陷入停滞。",
                "act2_conflict": "少数客户承担了绝大部分收入，集中度风险高。",
                "act3_resolution": "通过针对性留存计划，可稳定并提升收入。",
                "report": "# 收入叙事报告\n\n## 💡 核心观点\n\n收入增长由一小部分高价值客户驱动。\n\n## 🎤 三分钟故事\n\n我们分析了客户细分数据，发现前20%的客户贡献了80%的收入。建议将资源集中投入到高价值客户的留存计划中。\n\n## 现状\n尽管客户数量在增长，但收入已陷入停滞。\n\n## 冲突\n少数客户承担了绝大部分收入，集中度风险高。\n\n## 解决方案\n通过针对性留存计划，可稳定并提升收入。\n\n## 关键发现\n- 前20%客户贡献80%收入\n- 留存率每提升5%，收入增长约12%\n",
                "key_takeaways": [
                    "客户集中度是高风险也是高机会",
                    "留存比获客更具成本效益",
                    "建议优先启动头部客户关怀计划",
                ],
            }
        elif "score" in lower and any(m in lower.upper() for m in ("IC", "FA", "NC", "CP", "SF")):
            payload = {"score": 0.85, "reasoning": "结构良好，证据充分，逻辑清晰。"}
        else:
            payload = {"response": "mock response", "prompt_preview": prompt[:200]}

        if json_mode:
            return payload
        # For non-JSON mode (e.g. skill code generation), wrap report-like content in a Markdown block
        if "storytelling" in lower and "narrative" in lower:
            return (
                "```markdown\n"
                "# 收入叙事报告\n\n"
                "尽管客户数量在增长，但收入已陷入停滞。 "
                "少数客户承担了绝大部分收入，集中度风险高。 "
                "通过针对性留存计划，可稳定并提升收入。\n"
                "```"
            )
        return json.dumps(payload, ensure_ascii=False)
