"""用户需求理解层 — 数据模型定义

包含用户画像、意图识别、价值评估相关的核心数据类
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    """用户意图类型"""
    EXPLORATORY = "exploratory"       # "我想了解一下数据"
    DIAGNOSTIC = "diagnostic"         # "为什么转化率下降了"
    PREDICTIVE = "predictive"         # "下个月业绩会怎样"
    COMPARATIVE = "comparative"       # "A和B渠道哪个好"
    MONITORING = "monitoring"         # "日常数据监控"
    PRESENTATION = "presentation"     # "给老板汇报用"
    UNKNOWN = "unknown"               # 未识别


class ExpertiseLevel(Enum):
    """用户专业水平"""
    NOVICE = "novice"          # 新手
    INTERMEDIATE = "intermediate"  # 中级
    EXPERT = "expert"          # 专家


class DecisionScope(Enum):
    """决策范围"""
    STRATEGIC = "strategic"    # 战略层
    TACTICAL = "tactical"      # 战术层
    OPERATIONAL = "operational"  # 执行层


@dataclass
class UserProfile:
    """用户画像 — 由 LLM 分析用户输入生成"""
    
    role: str = ""                           # 角色: "电商运营" | "产品经理" | ...
    industry: str = ""                     # 行业: "零售" | "金融" | "教育" | ...
    goal: str = ""                         # 核心目标: "提升转化率" | "了解用户行为"
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    time_sensitivity: str = ""               # 时效偏好: "实时" | "近期" | "长期趋势"
    decision_scope: DecisionScope = DecisionScope.TACTICAL
    pain_points: List[str] = field(default_factory=list)      # 痛点列表
    success_metrics: List[str] = field(default_factory=list)  # 成功指标
    additional_notes: str = ""             # LLM 推断的其他信息
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "role": self.role,
            "industry": self.industry,
            "goal": self.goal,
            "expertise_level": self.expertise_level.value,
            "time_sensitivity": self.time_sensitivity,
            "decision_scope": self.decision_scope.value,
            "pain_points": self.pain_points,
            "success_metrics": self.success_metrics,
            "additional_notes": self.additional_notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """从字典反序列化"""
        return cls(
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


@dataclass
class UserIntent:
    """用户意图 — 由 IntentEngine 分析生成"""
    
    intent_type: IntentType = IntentType.UNKNOWN
    intent_confidence: float = 0.0           # 意图识别置信度 0-1
    key_metrics: List[str] = field(default_factory=list)     # 用户关注的关键指标
    expected_output: str = ""                # 期望输出类型
    raw_input: str = ""                      # 原始用户输入
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "intent_confidence": self.intent_confidence,
            "key_metrics": self.key_metrics,
            "expected_output": self.expected_output,
            "raw_input": self.raw_input,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserIntent":
        return cls(
            intent_type=IntentType(data.get("intent_type", "unknown")),
            intent_confidence=data.get("intent_confidence", 0.0),
            key_metrics=data.get("key_metrics", []),
            expected_output=data.get("expected_output", ""),
            raw_input=data.get("raw_input", ""),
        )


@dataclass
class ValueMatrix:
    """价值权重矩阵 — 评估数据各元素对用户的价值"""
    
    field_values: Dict[str, float] = field(default_factory=dict)     # 字段价值 {字段名: 0-1}
    insight_type_values: Dict[str, float] = field(default_factory=dict)  # 洞察类型价值
    chart_type_values: Dict[str, float] = field(default_factory=dict)    # 图表类型价值
    rationale: str = ""                  # 评估理由（LLM 生成）
    
    # 默认阈值
    DEFAULT_THRESHOLD: float = 0.3
    NOVICE_THRESHOLD: float = 0.2        # 新手降低阈值，保留更多解释性内容
    
    def get_field_value(self, field_name: str) -> float:
        """获取字段价值，默认 0.5"""
        return self.field_values.get(field_name, 0.5)
    
    def get_insight_value(self, insight_type: str) -> float:
        """获取洞察类型价值"""
        return self.insight_type_values.get(insight_type, 0.5)
    
    def get_chart_value(self, chart_type: str) -> float:
        """获取图表类型价值"""
        return self.chart_type_values.get(chart_type, 0.5)
    
    def get_threshold(self, user_profile: Optional[UserProfile] = None) -> float:
        """根据用户画像获取合适的过滤阈值"""
        if user_profile and user_profile.expertise_level == ExpertiseLevel.NOVICE:
            return self.NOVICE_THRESHOLD
        return self.DEFAULT_THRESHOLD
    
    def is_field_valuable(self, field_name: str, 
                          user_profile: Optional[UserProfile] = None) -> bool:
        """判断字段是否有价值"""
        return self.get_field_value(field_name) >= self.get_threshold(user_profile)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_values": self.field_values,
            "insight_type_values": self.insight_type_values,
            "chart_type_values": self.chart_type_values,
            "rationale": self.rationale,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValueMatrix":
        return cls(
            field_values=data.get("field_values", {}),
            insight_type_values=data.get("insight_type_values", {}),
            chart_type_values=data.get("chart_type_values", {}),
            rationale=data.get("rationale", ""),
        )


@dataclass
class NarrativeConstraint:
    """叙事约束条件 — 由用户意图推导的叙事要求"""
    
    tone: str = "professional"           # 语调: professional | casual | dramatic | data-driven
    max_length: int = 2000                # 最大长度（字数）
    focus_areas: List[str] = field(default_factory=list)   # 重点关注的领域
    exclude_areas: List[str] = field(default_factory=list) # 需要回避的领域
    depth_level: str = "medium"           # 深度: shallow | medium | deep
    include_recommendations: bool = True   # 是否包含行动建议
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tone": self.tone,
            "max_length": self.max_length,
            "focus_areas": self.focus_areas,
            "exclude_areas": self.exclude_areas,
            "depth_level": self.depth_level,
            "include_recommendations": self.include_recommendations,
        }


# 导出所有模型
__all__ = [
    "IntentType", "ExpertiseLevel", "DecisionScope",
    "UserProfile", "UserIntent", "ValueMatrix", "NarrativeConstraint",
]