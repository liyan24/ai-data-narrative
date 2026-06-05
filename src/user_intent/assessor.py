"""价值评估引擎 — 通过 LLM 评估数据中各元素对用户的价值

输入: 用户画像 + 数据画像 + 字段语义信息
输出: ValueMatrix 对象
"""

import json
from typing import Dict, Any, Optional

from src.user_intent.models import ValueMatrix, UserProfile
from src.llm_client import LLMClient, get_llm_client


_DEFAULT_VALUE_PROMPT = """你是数据价值评估专家。

请根据用户画像和数据字段信息，评估每个字段对用户的价值（0-1）。

【用户画像】
角色: {role}
行业: {industry}
目标: {goal}
专业水平: {expertise_level}
痛点: {pain_points}
关注指标: {success_metrics}

【数据字段】
{fields_info}

评估标准:
1. 该字段与用户目标的相关性（越高越好）
2. 该字段的信息量（是否有分析价值）
3. 对用户痛点的针对性（能否帮助解决痛点）
4. 用户专业水平（新手需要更多解释性字段）

输出 JSON 格式:
{{
    "field_values": {{
        "字段名1": 0.95,
        "字段名2": 0.3,
        ...
    }},
    "insight_type_values": {{
        "trend": 0.9,
        "distribution": 0.7,
        "comparison": 0.8,
        "relationship": 0.6,
        "composition": 0.7,
        "anomaly": 0.85
    }},
    "chart_type_values": {{
        "line": 0.9,
        "bar": 0.8,
        "pie": 0.5,
        "scatter": 0.6,
        "heatmap": 0.7
    }},
    "rationale": "评估理由的简要说明"
}}

注意:
- ID字段、序号字段通常价值很低（0.1-0.2）
- 与用户目标直接相关的核心指标字段价值应很高（0.8-1.0）
- 时间字段通常价值中等（0.5-0.7），但如果用户关注趋势则更高
- 新手用户需要更多解释性字段，不应过度过滤
"""


class ValueAssessor:
    """价值评估引擎 — LLM驱动"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None,
                 prompt_template: Optional[str] = None):
        self.llm = llm_client or get_llm_client()
        self.prompt_template = prompt_template or _DEFAULT_VALUE_PROMPT
    
    def assess(self, 
               user_profile: UserProfile,
               fields_info: str,
               data_profile: Optional[Dict[str, Any]] = None) -> ValueMatrix:
        """
        评估数据价值
        
        Args:
            user_profile: 用户画像
            fields_info: 字段信息描述文本（由 SchemaEngine 生成）
            data_profile: 可选的数据画像
            
        Returns:
            ValueMatrix 对象
        """
        # 构建 prompt
        prompt = self.prompt_template.format(
            role=user_profile.role or "未知",
            industry=user_profile.industry or "未知",
            goal=user_profile.goal or "未知",
            expertise_level=user_profile.expertise_level.value,
            pain_points=", ".join(user_profile.pain_points) if user_profile.pain_points else "未明确",
            success_metrics=", ".join(user_profile.success_metrics) if user_profile.success_metrics else "未明确",
            fields_info=fields_info or "（未提供字段信息）"
        )
        
        # 调用 LLM
        if not self.llm or not self.llm.api_key:
            return self._fallback_assess(user_profile, fields_info)
        
        try:
            response = self.llm.chat([
                {"role": "system", "content": "你是一个数据价值评估专家。请严格输出 JSON 格式。"},
                {"role": "user", "content": prompt}
            ], temperature=0.2)
            
            value_data = self._extract_json(response)
            return self._parse_value_matrix(value_data)
            
        except Exception as e:
            return self._fallback_assess(user_profile, fields_info)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从 LLM 响应中提取 JSON"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    
    def _parse_value_matrix(self, data: Dict[str, Any]) -> ValueMatrix:
        """将字典解析为 ValueMatrix"""
        return ValueMatrix(
            field_values=data.get("field_values", {}),
            insight_type_values=data.get("insight_type_values", {}),
            chart_type_values=data.get("chart_type_values", {}),
            rationale=data.get("rationale", ""),
        )
    
    def _fallback_assess(self, user_profile: UserProfile, fields_info: str) -> ValueMatrix:
        """LLM 不可用时的降级策略 — 基于规则的简单价值评估"""
        import re
        
        # 简单的关键词匹配评估
        field_values = {}
        
        # 从 fields_info 中提取字段名（简单解析）
        field_names = re.findall(r'["\'](\w+)["\']\s*:', fields_info)
        if not field_names:
            field_names = re.findall(r'-?\s*(\w+)\s*[:\(]', fields_info)
        
        user_lower = (user_profile.role + user_profile.goal + 
                      " ".join(user_profile.success_metrics)).lower()
        
        for field in field_names:
            field_lower = field.lower()
            
            # 默认价值
            value = 0.5
            
            # ID/序号类字段价值低
            if any(k in field_lower for k in ["id", "序号", "编号", "no", "index"]):
                value = 0.1
            # 用户目标相关字段价值高
            elif any(k in user_lower for k in [field_lower, field_lower.replace("_", ""), field_lower.replace("-", "")]):
                value = 0.9
            # 金额/数量类字段通常有价值
            elif any(k in field_lower for k in ["amount", "金额", "price", "价格", "sales", "销售", "revenue", "收入"]):
                value = 0.85
            # 时间字段中等价值
            elif any(k in field_lower for k in ["date", "time", "日期", "时间"]):
                value = 0.6
            # 类别/状态字段中等价值
            elif any(k in field_lower for k in ["category", "type", "status", "类别", "类型", "状态"]):
                value = 0.6
            # 名称/描述字段低价值（通常用于分组，不是分析核心）
            elif any(k in field_lower for k in ["name", "描述", "备注", "note", "comment"]):
                value = 0.3
            
            field_values[field] = value
        
        return ValueMatrix(
            field_values=field_values,
            insight_type_values={
                "trend": 0.8, "distribution": 0.6, "comparison": 0.7,
                "relationship": 0.6, "composition": 0.6, "anomaly": 0.75
            },
            chart_type_values={
                "line": 0.8, "bar": 0.7, "pie": 0.5, "scatter": 0.5, "heatmap": 0.6
            },
            rationale="（由规则引擎评估，精度有限）",
        )
