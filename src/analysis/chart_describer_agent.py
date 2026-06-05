"""
图表描述智能体 — 用大模型根据图表数据生成描述和意义

生成两段文字：
1. 描述：对图表及数据的基本描述（用数字说话）
2. 意义：数据体现什么，对用户有什么用
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import pandas as pd
import numpy as np

from src.llm_client import LLMClient, get_llm_client


_DEFAULT_CHART_DESCRIPTION_PROMPT = """你是数据可视化分析师。请根据图表数据生成两段说明文字。

【图表信息】
类型: {chart_type}
标题: {title}
使用列: {columns}

【数据摘要】
{data_summary}

【用户背景】
角色: {user_role}
目标: {user_goal}

请输出两段文字（每段不超过80字）：

1. 描述：用简洁的语言描述图表展示了什么数据，包含关键数字（如最大值、最小值、平均值、占比等）。
2. 意义：数据体现什么业务规律或趋势，对用户有什么用，建议采取什么行动。

要求：
- 禁止空洞修辞（如"令人振奋""非常重要"）
- 用具体数字说话
- 直接给出结论，不要含糊
- 中文撰写，通俗易懂

输出格式：
{{
    "description": "第一段描述文字",
    "meaning": "第二段意义文字"
}}
"""


@dataclass
class ChartDescription:
    """图表描述结果"""
    description: str
    meaning: str


class ChartDescriberAgent:
    """图表描述智能体 — LLM驱动"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()
    
    def describe(self, chart_type: str, title: str, columns: List[str],
                 df: pd.DataFrame, user_profile: Any = None,
                 extra_data: Dict[str, Any] = None) -> ChartDescription:
        """
        用 LLM 生成图表描述
        
        如果 LLM 不可用，使用规则生成
        """
        # 构建数据摘要
        data_summary = self._build_data_summary(df, columns, extra_data)
        
        user_role = ""
        user_goal = ""
        if user_profile:
            user_role = getattr(user_profile, 'role', '') or ''
            user_goal = getattr(user_profile, 'goal', '') or ''
        
        # LLM 生成
        if self.llm and self.llm.api_key:
            try:
                prompt = _DEFAULT_CHART_DESCRIPTION_PROMPT.format(
                    chart_type=chart_type,
                    title=title,
                    columns=", ".join(columns),
                    data_summary=data_summary,
                    user_role=user_role or "未指定",
                    user_goal=user_goal or "未指定",
                )
                
                response = self.llm.chat([
                    {"role": "system", "content": "你是数据可视化分析师。请严格输出 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ], temperature=0.3)
                
                data = self._extract_json(response)
                return ChartDescription(
                    description=data.get("description", ""),
                    meaning=data.get("meaning", ""),
                )
            except Exception as e:
                pass
        
        # LLM 不可用，回退到规则生成
        return self._rule_based_describe(chart_type, title, columns, df, extra_data)
    
    def _build_data_summary(self, df: pd.DataFrame, columns: List[str],
                            extra_data: Dict[str, Any] = None) -> str:
        """构建数据摘要"""
        parts = []
        
        # 数值列统计
        for col in columns:
            if col in df.columns and np.issubdtype(df[col].dtype, np.number):
                stats = df[col].describe()
                parts.append(f"{col}: 均值 {stats['mean']:.2f}, 最大 {stats['max']:.2f}, 最小 {stats['min']:.2f}")
        
        # 分类列统计
        for col in columns:
            if col in df.columns and df[col].dtype == object:
                unique = df[col].nunique()
                top = df[col].value_counts().head(3)
                top_str = ", ".join([f"{k}({v}条)" for k, v in top.items()])
                parts.append(f"{col}: 共 {unique} 个类别, 前三: {top_str}")
        
        # 额外数据
        if extra_data:
            for k, v in extra_data.items():
                if isinstance(v, (int, float, str)):
                    parts.append(f"{k}: {v}")
        
        return "\n".join(parts) if parts else "无可用统计摘要"
    
    def _rule_based_describe(self, chart_type: str, title: str, columns: List[str],
                             df: pd.DataFrame, extra_data: Dict[str, Any] = None) -> ChartDescription:
        """规则生成的描述（LLM 不可用时回退）"""
        # 简单的规则生成
        cat_cols = [c for c in columns if c in df.columns and df[c].dtype == object]
        num_cols = [c for c in columns if c in df.columns and np.issubdtype(df[c].dtype, np.number)]
        
        if num_cols and cat_cols:
            num_col = num_cols[0]
            cat_col = cat_cols[0]
            data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
            max_val = data.max() if len(data) > 0 else 0
            top_cat = data.index[0] if len(data) > 0 else "N/A"
            total = data.sum()
            
            description = f"该图表展示了各{cat_col}的{num_col}分布，共 {len(data)} 个类别。{top_cat}最高，达到 {max_val:.1f}，总计 {total:.1f}。"
            meaning = f"{top_cat}是核心贡献者，建议重点关注该领域以优化资源分配。"
        elif len(num_cols) >= 2:
            corr = df[num_cols[0]].corr(df[num_cols[1]]) if len(num_cols) >= 2 else 0
            description = f"该图表展示了{num_cols[0]}与{num_cols[1]}的关系，共 {len(df)} 个数据点，相关系数 {corr:.2f}。"
            meaning = f"两者相关性 {'强' if abs(corr) > 0.7 else '中等' if abs(corr) > 0.3 else '弱'}，{'可构建预测模型' if abs(corr) > 0.7 else '独立分析即可'}。"
        else:
            description = f"该图表展示了{'、'.join(columns)}的数据分布。"
            meaning = "通过可视化可快速识别数据模式和异常值。"
        
        return ChartDescription(description=description, meaning=meaning)
    
    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())


__all__ = ["ChartDescriberAgent", "ChartDescription"]
