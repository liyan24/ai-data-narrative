"""
基于价值矩阵的内容过滤器 — 在叙事前过滤低价值数据/洞察

核心理念：如果某个洞察对用户没有价值，就不应该出现在最终故事中。
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

from src.insights.engine import DataInsight, InsightCategory


@dataclass
class FilterLog:
    """过滤日志"""
    item_type: str       # "insight" | "field" | "chart"
    item_name: str
    score: float
    threshold: float
    reason: str


class ValueFilter:
    """价值过滤器 — 基于价值矩阵决定保留/舍弃内容"""
    
    DEFAULT_INSIGHT_THRESHOLD = 0.25
    DEFAULT_FIELD_THRESHOLD = 0.15
    DEFAULT_CHART_THRESHOLD = 0.20
    
    def __init__(self, 
                 insight_threshold: float = None,
                 field_threshold: float = None,
                 chart_threshold: float = None):
        self.insight_threshold = insight_threshold or self.DEFAULT_INSIGHT_THRESHOLD
        self.field_threshold = field_threshold or self.DEFAULT_FIELD_THRESHOLD
        self.chart_threshold = chart_threshold or self.DEFAULT_CHART_THRESHOLD
    
    # ───────────── 洞察过滤 ─────────────
    
    def filter_insights(self, insights: List[DataInsight], 
                       value_matrix: Optional[Dict[str, Any]]) -> Tuple[List[DataInsight], List[FilterLog]]:
        """
        过滤洞察列表，返回(高价值洞察, 过滤日志)
        """
        if not value_matrix:
            # 无价值矩阵时全部保留（价值评估技能未执行或失败）
            return insights, []
        
        high_value = []
        logs = []
        
        insight_scores = value_matrix.get("insights", {})
        category_scores = value_matrix.get("insight_categories", {})
        
        for insight in insights:
            title = getattr(insight, 'title', '')
            category = getattr(insight, 'category', None)
            category_key = category.value if category else 'unknown'
            
            # 综合评分：具体洞察评分 + 类别评分
            item_score = insight_scores.get(title, 0.5)
            cat_score = category_scores.get(category_key, 0.5)
            combined = max(item_score, cat_score)  # 取较高者更宽容
            
            if combined >= self.insight_threshold:
                high_value.append(insight)
            else:
                logs.append(FilterLog(
                    item_type="insight",
                    item_name=title,
                    score=combined,
                    threshold=self.insight_threshold,
                    reason=f"价值评分 {combined:.2f} < 阈值 {self.insight_threshold}"
                ))
        
        return high_value, logs
    
    def filter_fields(self, fields: List[str], 
                     value_matrix: Optional[Dict[str, Any]]) -> Tuple[List[str], List[FilterLog]]:
        """
        过滤字段列表（用于决定哪些字段出现在故事中）
        """
        if not value_matrix:
            return fields, []
        
        high_value = []
        logs = []
        field_scores = value_matrix.get("fields", {})
        
        for field in fields:
            score = field_scores.get(field, 0.5)
            if score >= self.field_threshold:
                high_value.append(field)
            else:
                logs.append(FilterLog(
                    item_type="field",
                    item_name=field,
                    score=score,
                    threshold=self.field_threshold,
                    reason=f"字段价值 {score:.2f} < 阈值 {self.field_threshold}"
                ))
        
        return high_value, logs
    
    def filter_charts(self, chart_recommendations: List[Dict[str, Any]],
                     value_matrix: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[FilterLog]]:
        """
        过滤图表推荐（基于图表价值评分）
        """
        if not value_matrix:
            return chart_recommendations, []
        
        high_value = []
        logs = []
        chart_scores = value_matrix.get("charts", {})
        
        for chart in chart_recommendations:
            chart_id = chart.get("id", chart.get("type", "unknown"))
            score = chart_scores.get(chart_id, 0.5)
            if score >= self.chart_threshold:
                high_value.append(chart)
            else:
                logs.append(FilterLog(
                    item_type="chart",
                    item_name=chart_id,
                    score=score,
                    threshold=self.chart_threshold,
                    reason=f"图表价值 {score:.2f} < 阈值 {self.chart_threshold}"
                ))
        
        return high_value, logs
    
    def get_filter_summary(self, logs: List[FilterLog]) -> Dict[str, Any]:
        """生成过滤摘要"""
        by_type = {}
        for log in logs:
            by_type.setdefault(log.item_type, []).append(log)
        
        return {
            "total_filtered": len(logs),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "details": [
                {"type": l.item_type, "name": l.item_name, "score": l.score, "reason": l.reason}
                for l in logs
            ]
        }


__all__ = ["ValueFilter", "FilterLog"]
