"""用户需求理解层

通过 LLM 分析用户角色、意图和数据价值，为数据叙事提供个性化基础。
"""

from src.user_intent.models import (
    UserProfile, UserIntent, ValueMatrix, NarrativeConstraint,
    IntentType, ExpertiseLevel, DecisionScope
)
from src.user_intent.profile import UserProfileGenerator
from src.user_intent.engine import IntentEngine
from src.user_intent.assessor import ValueAssessor

__all__ = [
    # 模型
    "UserProfile", "UserIntent", "ValueMatrix", "NarrativeConstraint",
    "IntentType", "ExpertiseLevel", "DecisionScope",
    # 引擎
    "UserProfileGenerator", "IntentEngine", "ValueAssessor",
]