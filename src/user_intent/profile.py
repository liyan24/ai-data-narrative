"""用户画像生成器 — 通过 LLM 分析用户输入生成结构化用户画像

输入: 用户角色描述（可选）+ 需求描述（可选）+ 数据文件信息
输出: UserProfile 对象
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

from src.user_intent.models import UserProfile, ExpertiseLevel, DecisionScope
from src.llm_client import LLMClient, get_llm_client


# 提示词模板（从文件读取，支持覆盖）
_DEFAULT_USER_PROFILE_PROMPT = """你是数据叙事系统的用户画像分析师。

请根据以下信息分析用户特征，生成结构化的用户画像。

【用户输入】
{user_input}

【数据文件】
文件名: {file_name}
数据样本（前3行）:
{data_sample}

请分析：
1. 用户的角色（如电商运营、产品经理、数据分析师、财务、HR等）
2. 用户所在行业（如零售、金融、教育、互联网、制造业等）
3. 用户的核心目标（一句话描述用户想用这份数据做什么）
4. 用户的专业水平（新手/中级/专家）
5. 用户的时效偏好（实时/近期/长期趋势）
6. 用户的决策范围（战略/战术/执行）
7. 用户最可能的2-3个痛点
8. 用户最关注的2-3个成功指标
9. 其他值得注意的特征

请用中文输出 JSON 格式，字段名如下:
- role: str
- industry: str  
- goal: str
- expertise_level: str ("novice"|"intermediate"|"expert")
- time_sensitivity: str ("实时"|"近期"|"长期趋势")
- decision_scope: str ("strategic"|"tactical"|"operational")
- pain_points: List[str]
- success_metrics: List[str]
- additional_notes: str

注意：如果用户没有提供角色信息，请从数据文件名和数据内容推断最可能的用户角色。
如果数据样本无法推断，使用通用默认值。
"""


class UserProfileGenerator:
    """用户画像生成器 — LLM驱动"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, 
                 prompt_template: Optional[str] = None):
        self.llm = llm_client or get_llm_client()
        self.prompt_template = prompt_template or _DEFAULT_USER_PROFILE_PROMPT
    
    def generate(self, 
                 user_input: str = "",
                 file_path: Optional[Path] = None,
                 data_sample: str = "",
                 max_sample_rows: int = 3) -> UserProfile:
        """
        生成用户画像
        
        Args:
            user_input: 用户的自然语言输入（角色/需求描述）
            file_path: 数据文件路径（用于获取文件名）
            data_sample: 数据样本字符串（可选，如已预读取）
            max_sample_rows: 最大采样行数
            
        Returns:
            UserProfile 对象
        """
        file_name = file_path.name if file_path else "unknown"
        
        # 构建 prompt
        prompt = self.prompt_template.format(
            user_input=user_input or "（用户未提供具体描述）",
            file_name=file_name,
            data_sample=data_sample or "（未提供数据样本）"
        )
        
        # 调用 LLM
        if not self.llm or not self.llm.api_key:
            # LLM 不可用，使用规则推断
            return self._fallback_generate(user_input, file_name)
        
        try:
            response = self.llm.chat([
                {"role": "system", "content": "你是一个数据叙事系统的用户画像分析师。请严格输出 JSON 格式。"},
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            # 解析 JSON
            profile_data = self._extract_json(response)
            return self._parse_profile(profile_data)
            
        except Exception as e:
            # LLM 失败时降级到规则推断
            return self._fallback_generate(user_input, file_name)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从 LLM 响应中提取 JSON"""
        text = text.strip()
        # 清理 markdown 代码块
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    
    def _parse_profile(self, data: Dict[str, Any]) -> UserProfile:
        """将字典解析为 UserProfile"""
        return UserProfile(
            role=data.get("role", ""),
            industry=data.get("industry", ""),
            goal=data.get("goal", ""),
            expertise_level=ExpertiseLevel(data.get("expertise_level", "intermediate")),
            time_sensitivity=data.get("time_sensitivity", ""),
            decision_scope=DecisionScope(data.get("decision_scope", "tactical")),
            pain_points=data.get("pain_points", []),
            success_metrics=data.get("success_metrics", []),
            additional_notes=data.get("additional_notes", ""),
        )
    
    def _fallback_generate(self, user_input: str, file_name: str) -> UserProfile:
        """LLM 不可用时的降级策略 — 基于规则推断"""
        import re
        
        input_lower = (user_input + " " + file_name).lower()
        
        # 角色推断
        role = ""
        if any(k in input_lower for k in ["运营", "电商", "销售"]):
            role = "电商运营"
        elif any(k in input_lower for k in ["产品", "pm", "产品经理"]):
            role = "产品经理"
        elif any(k in input_lower for k in ["财务", "会计", "成本"]):
            role = "财务分析师"
        elif any(k in input_lower for k in ["人力", "hr", "员工", "薪酬"]):
            role = "HR"
        elif any(k in input_lower for k in ["数据", "分析", "分析师"]):
            role = "数据分析师"
        
        # 行业推断
        industry = ""
        if any(k in input_lower for k in ["电商", "零售", "订单", "商品"]):
            industry = "零售/电商"
        elif any(k in input_lower for k in ["金融", "银行", "投资"]):
            industry = "金融"
        elif any(k in input_lower for k in ["教育", "学生", "课程"]):
            industry = "教育"
        
        # 目标推断
        goal = "分析数据并获取业务洞察"
        if "为什么" in user_input or "下降" in user_input or "问题" in user_input:
            goal = "诊断业务问题"
        elif "预测" in user_input or "未来" in user_input:
            goal = "预测未来趋势"
        elif "对比" in user_input or "哪个" in user_input:
            goal = "对比分析"
        
        return UserProfile(
            role=role or "业务人员",
            industry=industry or "未知行业",
            goal=goal,
            expertise_level=ExpertiseLevel.INTERMEDIATE,
            time_sensitivity="近期",
            decision_scope=DecisionScope.TACTICAL,
            pain_points=["数据解读困难", "缺少分析方向"],
            success_metrics=["业务增长", "效率提升"],
            additional_notes="（由规则引擎推断，精度有限）",
        )
