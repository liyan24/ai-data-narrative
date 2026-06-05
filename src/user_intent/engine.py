"""意图识别引擎 — 通过 LLM 分析用户输入识别分析意图

输入: 用户自然语言输入 + 数据画像
输出: UserIntent 对象
"""

import json
from typing import Dict, Any, Optional

from src.user_intent.models import UserIntent, IntentType, UserProfile
from src.llm_client import LLMClient, get_llm_client


_DEFAULT_INTENT_PROMPT = """你是数据叙事系统的意图识别专家。

请根据用户输入和数据特征，识别用户的分析意图。

【用户输入】
{user_input}

【用户画像】
角色: {role}
行业: {industry}
目标: {goal}
专业水平: {expertise_level}

【数据特征】
文件名: {file_name}
数据维度: {row_count} 行 × {column_count} 列
列名: {columns}

可能的意图类型:
- EXPLORATORY: 我想了解一下数据 → 全面概览型叙事
- DIAGNOSTIC: 为什么转化率下降了/出了什么问题 → 问题诊断型叙事
- PREDICTIVE: 下个月业绩会怎样/未来趋势 → 预测型叙事
- COMPARATIVE: A和B渠道哪个好/对比分析 → 对比型叙事
- MONITORING: 日常数据监控/看看数据 → 简报型叙事
- PRESENTATION: 给老板汇报用/做报告 → 汇报型叙事

请分析：
1. 最可能的意图类型
2. 置信度（0-1）
3. 用户关注的关键指标（2-4个）
4. 用户期望的输出形式

输出 JSON 格式:
{{
    "intent_type": "exploratory|diagnostic|predictive|comparative|monitoring|presentation",
    "intent_confidence": 0.95,
    "key_metrics": ["指标1", "指标2"],
    "expected_output": "用户期望的输出描述"
}}
"""


class IntentEngine:
    """意图识别引擎 — LLM驱动"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None,
                 prompt_template: Optional[str] = None):
        self.llm = llm_client or get_llm_client()
        self.prompt_template = prompt_template or _DEFAULT_INTENT_PROMPT
    
    def analyze(self, 
                user_input: str,
                user_profile: UserProfile,
                data_profile: Dict[str, Any]) -> UserIntent:
        """
        分析用户意图
        
        Args:
            user_input: 用户原始输入
            user_profile: 用户画像
            data_profile: 数据画像字典（含行数、列数、列名等）
            
        Returns:
            UserIntent 对象
        """
        # 构建 prompt
        prompt = self.prompt_template.format(
            user_input=user_input or "（用户未提供具体描述）",
            role=user_profile.role or "未知",
            industry=user_profile.industry or "未知",
            goal=user_profile.goal or "未知",
            expertise_level=user_profile.expertise_level.value,
            file_name=data_profile.get("source", "unknown"),
            row_count=data_profile.get("rows", 0),
            column_count=data_profile.get("columns", 0),
            columns=", ".join(data_profile.get("type_distribution", {}).keys())
        )
        
        # 调用 LLM
        if not self.llm or not self.llm.api_key:
            return self._fallback_analyze(user_input, user_profile)
        
        try:
            response = self.llm.chat([
                {"role": "system", "content": "你是一个数据叙事系统的意图识别专家。请严格输出 JSON 格式。"},
                {"role": "user", "content": prompt}
            ], temperature=0.2)
            
            intent_data = self._extract_json(response)
            return self._parse_intent(intent_data, user_input)
            
        except Exception as e:
            return self._fallback_analyze(user_input, user_profile)
    
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
    
    def _parse_intent(self, data: Dict[str, Any], raw_input: str) -> UserIntent:
        """将字典解析为 UserIntent"""
        intent_type_str = data.get("intent_type", "unknown").lower()
        
        # 映射到枚举
        intent_map = {
            "exploratory": IntentType.EXPLORATORY,
            "diagnostic": IntentType.DIAGNOSTIC,
            "predictive": IntentType.PREDICTIVE,
            "comparative": IntentType.COMPARATIVE,
            "monitoring": IntentType.MONITORING,
            "presentation": IntentType.PRESENTATION,
        }
        
        return UserIntent(
            intent_type=intent_map.get(intent_type_str, IntentType.UNKNOWN),
            intent_confidence=data.get("intent_confidence", 0.5),
            key_metrics=data.get("key_metrics", []),
            expected_output=data.get("expected_output", ""),
            raw_input=raw_input,
        )
    
    def _fallback_analyze(self, user_input: str, user_profile: UserProfile) -> UserIntent:
        """LLM 不可用时的降级策略"""
        import re
        
        input_lower = user_input.lower()
        
        # 基于关键词推断意图
        if any(k in input_lower for k in ["为什么", "问题", "下降", "异常", "诊断"]):
            intent_type = IntentType.DIAGNOSTIC
            confidence = 0.8
            key_metrics = ["异常指标", "问题根因"]
        elif any(k in input_lower for k in ["预测", "未来", "趋势", "下个月", "明年"]):
            intent_type = IntentType.PREDICTIVE
            confidence = 0.8
            key_metrics = ["趋势指标", "预测值"]
        elif any(k in input_lower for k in ["对比", "比较", "哪个", "vs", "versus"]):
            intent_type = IntentType.COMPARATIVE
            confidence = 0.8
            key_metrics = ["对比维度", "差异指标"]
        elif any(k in input_lower for k in ["汇报", "报告", "老板", "展示", "ppt"]):
            intent_type = IntentType.PRESENTATION
            confidence = 0.8
            key_metrics = ["核心指标", "关键发现"]
        elif any(k in input_lower for k in ["监控", "日常", "看看", "浏览"]):
            intent_type = IntentType.MONITORING
            confidence = 0.7
            key_metrics = ["关键指标", "状态概览"]
        else:
            intent_type = IntentType.EXPLORATORY
            confidence = 0.6
            key_metrics = ["数据概览", "关键指标"]
        
        return UserIntent(
            intent_type=intent_type,
            intent_confidence=confidence,
            key_metrics=key_metrics,
            expected_output="数据概览与洞察报告",
            raw_input=user_input,
        )
