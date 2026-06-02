"""
叙事增强引擎 — 多策略组合、故事生成、自然语言洞察

核心能力：
- 多策略组合：同时应用多个叙事策略
- 故事评分：按数据特征为策略加权评分
- 自然语言生成：将数据洞察转化为故事段落
- 策略冲突检测：避免矛盾的叙事策略同时出现
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

import pandas as pd
import numpy as np

from src.narrative.strategy import NarrativeStrategyEngine, NarrativeStrategy, NarrativeType
from src.insights.engine import DataInsight, InsightCategory
from src.config import LLM_CONFIG


class StoryTone(Enum):
    """故事语调"""
    PROFESSIONAL = "professional"   # 专业严谨
    CASUAL = "casual"               # 轻松通俗
    DRAMATIC = "dramatic"          # 戏剧化
    DATA_DRIVEN = "data_driven"    # 数据驱动


@dataclass
class StorySection:
    """故事章节"""
    title: str
    content: str
    strategy: str = ""            # 使用的策略
    insights_used: List[str] = None  # 引用的洞察
    chart_references: List[str] = None  # 引用的图表


class StorytellerEngine:
    """故事生成引擎"""
    
    def __init__(self, tone: StoryTone = StoryTone.DATA_DRIVEN):
        self.tone = tone
        self.strategy_engine = NarrativeStrategyEngine()
    
    def generate_story(self, profile: Any, insights: List[DataInsight],
                      strategy: NarrativeStrategy, stats: Dict) -> List[StorySection]:
        """
        生成完整数据故事
        
        Returns:
            故事章节列表
        """
        sections = []
        
        # 1. 引言
        sections.append(self._generate_intro(profile, strategy))
        
        # 2. 数据概览
        sections.append(self._generate_overview(profile, stats))
        
        # 3. 核心洞察（按重要性排序）
        critical_insights = [i for i in insights if i.severity.value == "critical"]
        high_insights = [i for i in insights if i.severity.value == "high"]
        medium_insights = [i for i in insights if i.severity.value == "medium"]
        
        if critical_insights or high_insights:
            sections.append(self._generate_key_findings(
                critical_insights + high_insights[:3]
            ))
        
        # 4. 分主题洞察
        trend_insights = [i for i in insights if i.category == InsightCategory.TREND]
        comparison_insights = [i for i in insights if i.category == InsightCategory.COMPARISON]
        relationship_insights = [i for i in insights if i.category == InsightCategory.RELATIONSHIP]
        
        if trend_insights:
            sections.append(self._generate_trend_section(trend_insights))
        
        if comparison_insights:
            sections.append(self._generate_comparison_section(comparison_insights))
        
        if relationship_insights:
            sections.append(self._generate_relationship_section(relationship_insights))
        
        # 5. 建议与总结
        sections.append(self._generate_conclusion(insights, strategy))
        
        return sections
    
    def _generate_intro(self, profile: Any, strategy: NarrativeStrategy) -> StorySection:
        """生成引言"""
        source = getattr(profile, 'source_name', '数据文件')
        rows = getattr(profile, 'row_count', 0)
        cols = getattr(profile, 'col_count', 0)
        
        content = f"""
本文对 **{source}** 进行了深度分析。数据集包含 **{rows:,}** 条记录和 **{cols}** 个维度，
"""
        
        if strategy:
            content += f"""通过分析发现，数据最适合采用 **"{strategy.title}"** 的叙事视角。"""
            content += f"""{strategy.story_arc.setup}"""
        
        content += f"""

以下是从数据中提炼出的关键发现和洞察。
"""
        
        return StorySection(
            title="📖 数据故事",
            content=content.strip(),
            strategy=strategy.title if strategy else "通用分析"
        )
    
    def _generate_overview(self, profile: Any, stats: Dict) -> StorySection:
        """生成数据概览"""
        basic = stats.get("basic", {})
        row_count = basic.get('row_count', 'N/A')
        col_count = basic.get('column_count', 'N/A')
        
        content = f"""
### 数据全景

- **数据规模**：{row_count:,} 行 × {col_count} 列
- **数据密度**：{basic.get('density', 'N/A')}%
- **内存占用**：{basic.get('memory_usage_mb', 'N/A')} MB
"""
        
        # 添加类型分布
        type_dist = stats.get("type_distribution", {})
        if type_dist:
            content += "\n**字段类型分布**：\n"
            for t, count in type_dist.items():
                content += f"- {t}: {count} 个\n"
        
        return StorySection(
            title="🔍 数据概览",
            content=content.strip()
        )
    
    def _generate_key_findings(self, insights: List[DataInsight]) -> StorySection:
        """生成核心发现"""
        content = "### 核心发现\n\n"
        
        for i, insight in enumerate(insights[:5], 1):
            emoji_map = {
                "critical": "🚨",
                "high": "🔴",
                "medium": "🟡",
                "low": "🔵"
            }
            emoji = emoji_map.get(insight.severity.value, "⚪")
            
            content += f"{emoji} **{insight.title}**\n\n"
            content += f"{insight.description}\n\n"
            
            if insight.recommendation:
                content += f"💡 *建议：{insight.recommendation}*\n\n"
        
        return StorySection(
            title="⭐ 核心发现",
            content=content.strip(),
            insights_used=[i.title for i in insights]
        )
    
    def _generate_trend_section(self, insights: List[DataInsight]) -> StorySection:
        """生成趋势章节"""
        content = "### 趋势洞察\n\n"
        
        for insight in insights:
            content += f"📈 **{insight.title}**\n\n"
            content += f"{insight.description}\n\n"
        
        return StorySection(
            title="📈 趋势分析",
            content=content.strip(),
            insights_used=[i.title for i in insights]
        )
    
    def _generate_comparison_section(self, insights: List[DataInsight]) -> StorySection:
        """生成对比章节"""
        content = "### 对比分析\n\n"
        
        for insight in insights:
            content += f"⚖️ **{insight.title}**\n\n"
            content += f"{insight.description}\n\n"
        
        return StorySection(
            title="⚖️ 对比分析",
            content=content.strip(),
            insights_used=[i.title for i in insights]
        )
    
    def _generate_relationship_section(self, insights: List[DataInsight]) -> StorySection:
        """生成关系章节"""
        content = "### 关系探索\n\n"
        
        for insight in insights:
            content += f"🔗 **{insight.title}**\n\n"
            content += f"{insight.description}\n\n"
        
        return StorySection(
            title="🔗 关系探索",
            content=content.strip(),
            insights_used=[i.title for i in insights]
        )
    
    def _generate_conclusion(self, insights: List[DataInsight], strategy: NarrativeStrategy) -> StorySection:
        """生成结论"""
        # 汇总所有建议
        all_recommendations = []
        for i in insights:
            if i.recommendation:
                all_recommendations.append(i.recommendation)
        
        content = "### 总结与建议\n\n"
        
        if strategy:
            content += f"""
整体而言，数据呈现出 **{strategy.title}** 的特征。{strategy.story_arc.resolution}

"""
        
        if all_recommendations:
            content += "**优先行动建议**：\n\n"
            for i, rec in enumerate(all_recommendations[:5], 1):
                content += f"{i}. {rec}\n"
        
        content += "\n---\n\n"
        content += "*报告由 AI 数据叙事系统自动生成，建议结合业务背景进一步验证。*"
        
        return StorySection(
            title="📝 总结与建议",
            content=content.strip()
        )
    
    def to_markdown(self, sections: List[StorySection]) -> str:
        """将故事转换为 Markdown"""
        lines = []
        
        for section in sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
        
        return "\n".join(lines)


class StrategyScorer:
    """策略评分器 — 为多个策略按数据特征加权评分"""
    
    @staticmethod
    def score_strategies(df: pd.DataFrame, column_types: Dict[str, str],
                        stats: Dict) -> List[Tuple[NarrativeStrategy, float]]:
        """
        为多个策略评分并排序
        
        Returns:
            [(策略, 得分), ...] 按得分降序
        """
        # 获取所有候选策略
        all_strategies = NarrativeStrategyEngine.analyze(column_types, statistics=stats)
        
        scored = []
        for strategy in all_strategies:
            score = StrategyScorer._calculate_score(strategy, df, column_types, stats)
            scored.append((strategy, score))
        
        # 按得分降序
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    @staticmethod
    def _calculate_score(strategy: NarrativeStrategy, df: pd.DataFrame,
                        column_types: Dict[str, str], stats: Dict) -> float:
        """计算单个策略的得分"""
        score = strategy.confidence  # 基础置信度
        
        # 根据数据特征加权
        dt_cols = [c for c, t in column_types.items() if t == "datetime"]
        num_cols = [c for c, t in column_types.items() if t == "numeric"]
        cat_cols = [c for c, t in column_types.items() if t in ["categorical", "boolean"]]
        
        if strategy.narrative_type == NarrativeType.TREND:
            # 时间序列策略：需要时间列 + 数值列
            if len(dt_cols) >= 1 and len(num_cols) >= 1:
                score += 0.2
            # 数据量大加分
            if len(df) > 100:
                score += 0.1
        
        elif strategy.narrative_type == NarrativeType.COMPARISON:
            # 对比策略：需要类别列 + 数值列
            if len(cat_cols) >= 1 and len(num_cols) >= 1:
                score += 0.2
            # 类别多加分
            if len(cat_cols) >= 2:
                score += 0.1
        
        elif strategy.narrative_type == NarrativeType.DISTRIBUTION:
            # 分布策略：需要数值列
            if len(num_cols) >= 2:
                score += 0.2
        
        elif strategy.narrative_type == NarrativeType.RELATIONSHIP:
            # 关系策略：需要多个数值列
            if len(num_cols) >= 3:
                score += 0.2
            # 有相关性加分
            corr = stats.get("correlations", {})
            if corr.get("available") and len(corr.get("strong_pairs", [])) > 0:
                score += 0.1
        
        elif strategy.narrative_type == NarrativeType.COMPOSITION:
            # 构成策略：需要类别列
            if len(cat_cols) >= 1 and len(num_cols) >= 1:
                score += 0.2
        
        # 确保得分在 [0, 1] 范围内
        return min(1.0, max(0.0, score))
    
    @staticmethod
    def select_best_strategy(scored_strategies: List[Tuple[NarrativeStrategy, float]],
                           min_score: float = 0.3) -> Optional[NarrativeStrategy]:
        """选择最佳策略"""
        if not scored_strategies:
            return None
        
        best = scored_strategies[0]
        if best[1] >= min_score:
            return best[0]
        return None
    
    @staticmethod
    def select_top_strategies(scored_strategies: List[Tuple[NarrativeStrategy, float]],
                             top_n: int = 3, min_score: float = 0.3) -> List[NarrativeStrategy]:
        """选择 Top N 策略"""
        return [s for s, score in scored_strategies[:top_n] if score >= min_score]


class StrategyConflictDetector:
    """策略冲突检测器"""
    
    # 定义冲突规则：这些策略组合不应该同时出现
    CONFLICT_PAIRS = [
        (NarrativeType.TREND, NarrativeType.DISTRIBUTION),  # 趋势和分布不太兼容
    ]
    
    @classmethod
    def check_conflicts(cls, strategies: List[NarrativeStrategy]) -> List[Tuple[NarrativeStrategy, NarrativeStrategy, str]]:
        """
        检测策略冲突
        
        Returns:
            [(策略1, 策略2, 冲突原因), ...]
        """
        conflicts = []
        
        for i, s1 in enumerate(strategies):
            for s2 in strategies[i+1:]:
                # 检查是否在冲突列表中
                for t1, t2 in cls.CONFLICT_PAIRS:
                    if (s1.narrative_type == t1 and s2.narrative_type == t2) or \
                       (s1.narrative_type == t2 and s2.narrative_type == t1):
                        conflicts.append((
                            s1, s2,
                            f"{s1.title} 与 {s2.title} 的叙事角度存在冲突，"
                            f"建议优先选择得分更高的策略"
                        ))
        
        return conflicts
    
    @classmethod
    def resolve_conflicts(cls, strategies: List[NarrativeStrategy],
                         scores: Dict[int, float]) -> List[NarrativeStrategy]:
        """解决冲突，保留得分高的策略"""
        conflicts = cls.check_conflicts(strategies)
        
        to_remove = set()
        for s1, s2, reason in conflicts:
            # 移除得分低的
            score1 = scores.get(id(s1), 0)
            score2 = scores.get(id(s2), 0)
            if score1 >= score2:
                to_remove.add(id(s2))
            else:
                to_remove.add(id(s1))
        
        return [s for s in strategies if id(s) not in to_remove]
