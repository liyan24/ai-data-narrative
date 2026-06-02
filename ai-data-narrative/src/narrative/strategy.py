"""
叙事策略层 — 根据数据特征自动选择叙事策略和生成故事线
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass


class NarrativeType(Enum):
    """叙事类型枚举"""
    COMPARISON = "comparison"      # 对比型
    TREND = "trend"                # 趋势型
    DISTRIBUTION = "distribution"  # 分布型
    RELATIONSHIP = "relationship"  # 关系型
    COMPOSITION = "composition"    # 构成型
    RANKING = "ranking"            # 排名型
    GEOGRAPHIC = "geographic"      # 地理型


@dataclass
class StoryArc:
    """故事弧线（起承转合）"""
    setup: str          # 起：背景/问题引入
    conflict: str       # 承：数据中的发现/矛盾
    climax: str         # 转：核心洞察/转折点
    resolution: str     # 合：结论/建议


@dataclass
class NarrativeStrategy:
    """叙事策略"""
    narrative_type: NarrativeType
    confidence: float
    title: str
    subtitle: str
    key_points: List[str]
    story_arc: StoryArc
    recommended_charts: List[str]
    audience_level: str  # "beginner" | "intermediate" | "expert"


class NarrativeStrategyEngine:
    """叙事策略引擎"""
    
    # 叙事类型与数据特征的匹配规则
    MATCHING_RULES = {
        NarrativeType.TREND: {
            "required": ["datetime"],
            "preferred": ["numeric"],
            "score_boost": 1.0
        },
        NarrativeType.COMPARISON: {
            "required": ["categorical", "numeric"],
            "preferred": [],
            "score_boost": 0.9
        },
        NarrativeType.DISTRIBUTION: {
            "required": ["numeric"],
            "preferred": [],
            "score_boost": 0.8
        },
        NarrativeType.RELATIONSHIP: {
            "required": ["numeric"],
            "preferred": ["numeric"],
            "score_boost": 0.8
        },
        NarrativeType.COMPOSITION: {
            "required": ["categorical", "numeric"],
            "preferred": [],
            "score_boost": 0.7
        },
        NarrativeType.RANKING: {
            "required": ["categorical", "numeric"],
            "preferred": [],
            "score_boost": 0.7
        },
    }
    
    @classmethod
    def analyze(cls, column_types: Dict[str, str], statistics: Optional[Dict] = None) -> List[NarrativeStrategy]:
        """
        根据数据特征分析并推荐叙事策略
        
        Args:
            column_types: {列名: 类型} 映射
            statistics: 统计数据（可选）
            
        Returns:
            按置信度排序的叙事策略列表
        """
        type_counts = {}
        for t in column_types.values():
            type_counts[t] = type_counts.get(t, 0) + 1
        
        strategies = []
        
        for narrative_type, rules in cls.MATCHING_RULES.items():
            score = 0.0
            matched = True
            
            # 检查必需类型
            for req in rules["required"]:
                if req not in type_counts or type_counts[req] == 0:
                    matched = False
                    break
            
            if not matched:
                continue
            
            # 基础分
            score = rules["score_boost"]
            
            # 加分项
            for pref in rules["preferred"]:
                if pref in type_counts:
                    score += 0.1 * min(type_counts[pref], 3)
            
            # 统计加分
            if statistics:
                score = cls._apply_statistical_bonus(score, narrative_type, statistics)
            
            strategies.append(cls._build_strategy(narrative_type, score, column_types, statistics))
        
        # 按置信度排序
        strategies.sort(key=lambda x: x.confidence, reverse=True)
        return strategies
    
    @staticmethod
    def _apply_statistical_bonus(score: float, narrative_type: NarrativeType, statistics: Dict) -> float:
        """根据统计特征增加分数"""
        if narrative_type == NarrativeType.RELATIONSHIP and "correlations" in statistics:
            corr = statistics["correlations"]
            if corr.get("available") and corr.get("pair_count", 0) > 0:
                score += 0.2 * min(corr["pair_count"] / 3, 1)
        
        elif narrative_type == NarrativeType.TREND and "datetime" in str(statistics):
            if any("span_days" in v for v in statistics.get("datetime", {}).values()):
                score += 0.15
        
        elif narrative_type == NarrativeType.DISTRIBUTION and "numeric" in statistics:
            numeric_stats = statistics.get("numeric", {})
            for col_stat in numeric_stats.values():
                if abs(col_stat.get("skewness", 0)) > 1:
                    score += 0.1
                    break
        
        return min(score, 1.0)
    
    @classmethod
    def _build_strategy(cls, narrative_type: NarrativeType, score: float, column_types: Dict, statistics: Optional[Dict]) -> NarrativeStrategy:
        """构建叙事策略对象"""
        
        templates = {
            NarrativeType.TREND: {
                "title": "数据趋势洞察",
                "subtitle": "随时间变化的关键指标分析",
                "charts": ["line_chart", "area_chart", "calendar_heatmap"]
            },
            NarrativeType.COMPARISON: {
                "title": "数据对比分析",
                "subtitle": "不同维度间的差异与特征",
                "charts": ["bar_chart", "grouped_bar", "radar_chart"]
            },
            NarrativeType.DISTRIBUTION: {
                "title": "数据分布探索",
                "subtitle": "数值特征的分布规律与特征",
                "charts": ["histogram", "box_plot", "density_plot"]
            },
            NarrativeType.RELATIONSHIP: {
                "title": "变量关系分析",
                "subtitle": "多变量间的相关性与关联模式",
                "charts": ["scatter_plot", "correlation_matrix", "bubble_chart"]
            },
            NarrativeType.COMPOSITION: {
                "title": "构成结构分析",
                "subtitle": "整体与部分的占比关系",
                "charts": ["pie_chart", "stacked_bar", "treemap"]
            },
            NarrativeType.RANKING: {
                "title": "排名与排序",
                "subtitle": "Top N 与排序特征",
                "charts": ["horizontal_bar", "lollipop_chart", "word_cloud"]
            },
        }
        
        template = templates.get(narrative_type, {
            "title": "数据洞察",
            "subtitle": "基于数据特征的自动分析",
            "charts": ["table", "bar_chart"]
        })
        
        # 生成关键洞察点
        key_points = cls._generate_key_points(narrative_type, column_types, statistics)
        
        # 构建故事弧线
        story_arc = cls._generate_story_arc(narrative_type, key_points)
        
        return NarrativeStrategy(
            narrative_type=narrative_type,
            confidence=round(score, 2),
            title=template["title"],
            subtitle=template["subtitle"],
            key_points=key_points,
            story_arc=story_arc,
            recommended_charts=template["charts"],
            audience_level="beginner"
        )
    
    @staticmethod
    def _generate_key_points(narrative_type: NarrativeType, column_types: Dict, statistics: Optional[Dict]) -> List[str]:
        """生成关键洞察点"""
        points = []
        
        if narrative_type == NarrativeType.TREND:
            dt_cols = [c for c, t in column_types.items() if t == "datetime"]
            num_cols = [c for c, t in column_types.items() if t == "numeric"]
            points.append(f"包含 {len(dt_cols)} 个时间列，可追踪 {len(num_cols)} 个指标的变化趋势")
        
        elif narrative_type == NarrativeType.COMPARISON:
            cat_cols = [c for c, t in column_types.items() if t == "categorical"]
            points.append(f"可在 {len(cat_cols)} 个维度上进行分组对比")
        
        elif narrative_type == NarrativeType.DISTRIBUTION:
            num_cols = [c for c, t in column_types.items() if t == "numeric"]
            points.append(f"有 {len(num_cols)} 个数值列，可分析其分布特征")
        
        elif narrative_type == NarrativeType.RELATIONSHIP:
            num_cols = [c for c, t in column_types.items() if t == "numeric"]
            if statistics and "correlations" in statistics:
                corr = statistics["correlations"]
                if corr.get("available"):
                    points.append(f"发现 {corr.get('pair_count', 0)} 对强相关变量")
            points.append(f"共有 {len(num_cols)} 个数值变量可分析相互关系")
        
        elif narrative_type == NarrativeType.COMPOSITION:
            cat_cols = [c for c, t in column_types.items() if t == "categorical"]
            points.append(f"可通过 {len(cat_cols)} 个类别维度分析构成比例")
        
        return points
    
    @staticmethod
    def _generate_story_arc(narrative_type: NarrativeType, key_points: List[str]) -> StoryArc:
        """生成故事弧线"""
        arcs = {
            NarrativeType.TREND: StoryArc(
                setup="我们有一组时间序列数据，需要了解其发展轨迹",
                conflict="数据中可能存在波动、季节性或异常变化",
                climax="关键转折点出现在...",
                resolution="基于趋势分析，给出预测和行动建议"
            ),
            NarrativeType.COMPARISON: StoryArc(
                setup="数据包含多个类别或维度，需要了解它们的差异",
                conflict="某些维度表现异常，与其他维度差距显著",
                climax="发现最具代表性的差异点...",
                resolution="明确各维度特征，指导分类策略"
            ),
            NarrativeType.DISTRIBUTION: StoryArc(
                setup="数据中存在多个数值指标，需要了解其分布规律",
                conflict="数据分布可能存在偏态、多峰或异常值",
                climax="核心发现是...",
                resolution="总结分布特征，指导后续建模或分析"
            ),
            NarrativeType.RELATIONSHIP: StoryArc(
                setup="数据中有多个变量，需要了解它们之间的关联",
                conflict="某些变量关系复杂，可能存在非线性关系",
                climax="最强关联出现在...",
                resolution="明确变量关系网络，指导决策"
            ),
            NarrativeType.COMPOSITION: StoryArc(
                setup="数据需要展示整体中各部分的占比",
                conflict="某些部分占比异常，可能揭示结构性问题",
                climax="关键构成变化是...",
                resolution="优化资源配置或业务策略"
            ),
            NarrativeType.RANKING: StoryArc(
                setup="需要从数据中找出最重要的项或最佳表现者",
                conflict="排名结果可能与预期不符",
                climax="Top 1 是...",
                resolution="聚焦重点，优先投入资源"
            ),
        }
        
        return arcs.get(narrative_type, StoryArc(
            setup="我们有一组数据，需要从中提取洞察",
            conflict="数据中可能存在异常或有趣的规律",
            climax="核心发现是...",
            resolution="基于数据给出建议"
        ))
