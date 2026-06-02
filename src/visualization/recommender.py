"""
图表智能推荐引擎 — 数据类型 → 最佳图表类型
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ChartType(Enum):
    """图表类型枚举"""
    # 基础图表
    BAR = "bar_chart"
    LINE = "line_chart"
    PIE = "pie_chart"
    SCATTER = "scatter_plot"
    HISTOGRAM = "histogram"
    BOX = "box_plot"
    HEATMAP = "heatmap"
    AREA = "area_chart"
    
    # 高级图表
    GROUPED_BAR = "grouped_bar"
    STACKED_BAR = "stacked_bar"
    HORIZONTAL_BAR = "horizontal_bar"
    BUBBLE = "bubble_chart"
    TREEMAP = "treemap"
    RADAR = "radar_chart"
    LOLLIPOP = "lollipop_chart"
    DENSITY = "density_plot"
    CORR_MATRIX = "correlation_matrix"
    CALENDAR = "calendar_heatmap"
    WORD_CLOUD = "word_cloud"


@dataclass
class ChartRecommendation:
    """图表推荐结果"""
    chart_type: ChartType
    confidence: float
    columns: List[str]
    title: str
    description: str
    why: str


class ChartRecommender:
    """图表推荐器"""
    
    # 图表适用规则
    RULES = {
        ChartType.LINE: {
            "required": [("datetime", "numeric")],
            "score": 1.0,
            "description": "折线图适合展示时间序列趋势"
        },
        ChartType.BAR: {
            "required": [("categorical", "numeric")],
            "score": 0.95,
            "description": "柱状图适合类别对比"
        },
        ChartType.HISTOGRAM: {
            "required": [("numeric",)],
            "score": 0.9,
            "description": "直方图展示数值分布"
        },
        ChartType.SCATTER: {
            "required": [("numeric", "numeric")],
            "score": 0.9,
            "description": "散点图展示两个数值变量的关系"
        },
        ChartType.PIE: {
            "required": [("categorical", "numeric")],
            "score": 0.7,
            "description": "饼图展示构成比例（建议类别数 < 6）"
        },
        ChartType.BOX: {
            "required": [("numeric",)],
            "score": 0.85,
            "description": "箱线图展示分布和异常值"
        },
        ChartType.HEATMAP: {
            "required": [("categorical", "categorical", "numeric")],
            "score": 0.8,
            "description": "热力图展示矩阵式数据"
        },
        ChartType.GROUPED_BAR: {
            "required": [("categorical", "categorical", "numeric")],
            "score": 0.85,
            "description": "分组柱状图展示多维度对比"
        },
        ChartType.STACKED_BAR: {
            "required": [("categorical", "categorical", "numeric")],
            "score": 0.8,
            "description": "堆叠柱状图展示构成与对比"
        },
        ChartType.HORIZONTAL_BAR: {
            "required": [("categorical", "numeric")],
            "score": 0.85,
            "description": "水平柱状图适合类别名称较长时"
        },
        ChartType.AREA: {
            "required": [("datetime", "numeric")],
            "score": 0.85,
            "description": "面积图强调数量累积"
        },
        ChartType.BUBBLE: {
            "required": [("numeric", "numeric", "numeric")],
            "score": 0.75,
            "description": "气泡图展示三维关系"
        },
        ChartType.TREEMAP: {
            "required": [("categorical", "numeric")],
            "score": 0.7,
            "description": "矩形树图展示层级构成"
        },
        ChartType.CORR_MATRIX: {
            "required": [("numeric", "numeric")],
            "score": 0.85,
            "description": "相关性矩阵展示多变量关系"
        },
        ChartType.LOLLIPOP: {
            "required": [("categorical", "numeric")],
            "score": 0.75,
            "description": "棒棒糖图展示排名"
        },
    }
    
    @classmethod
    def recommend(cls, column_types: Dict[str, str], 
                  statistics: Optional[Dict] = None,
                  top_k: int = 5) -> List[ChartRecommendation]:
        """
        根据数据类型推荐图表
        
        Args:
            column_types: {列名: 类型} 映射
            statistics: 统计数据
            top_k: 返回前 K 个推荐
            
        Returns:
            图表推荐列表
        """
        columns = list(column_types.keys())
        type_list = list(column_types.values())
        
        recommendations = []
        
        for chart_type, rules in cls.RULES.items():
            for required_combo in rules["required"]:
                matched_cols = cls._match_columns(type_list, required_combo)
                
                for matched in matched_cols:
                    col_names = [columns[i] for i in matched]
                    score = rules["score"]
                    
                    # 调整分数
                    score = cls._adjust_score(score, chart_type, col_names, column_types, statistics)
                    
                    recommendations.append(ChartRecommendation(
                        chart_type=chart_type,
                        confidence=round(score, 2),
                        columns=col_names,
                        title=cls._generate_title(chart_type, col_names),
                        description=rules["description"],
                        why=cls._generate_why(chart_type, col_names, column_types)
                    ))
        
        # 去重并排序
        recommendations = cls._deduplicate(recommendations)
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return recommendations[:top_k]
    
    @staticmethod
    def _match_columns(type_list: List[str], required_combo: Tuple[str, ...]) -> List[List[int]]:
        """匹配满足类型组合的列索引"""
        from itertools import permutations, combinations
        
        results = []
        n = len(type_list)
        k = len(required_combo)
        
        if k == 1:
            # 单类型：返回所有匹配的索引
            for i, t in enumerate(type_list):
                if t == required_combo[0] or (required_combo[0] == "numeric" and t in ["numeric", "integer", "float"]):
                    results.append([i])
        elif n >= k:
            # 多类型：尝试所有排列
            for perm in permutations(range(n), k):
                matched = True
                for i, req_type in enumerate(required_combo):
                    actual = type_list[perm[i]]
                    if req_type in ["numeric", "integer", "float"]:
                        if actual not in ["numeric", "integer", "float"]:
                            matched = False
                            break
                    elif actual != req_type:
                        matched = False
                        break
                
                if matched:
                    results.append(list(perm))
        
        return results
    
    @staticmethod
    def _adjust_score(score: float, chart_type: ChartType, columns: List[str], 
                      column_types: Dict[str, str], statistics: Optional[Dict]) -> float:
        """根据具体特征调整分数"""
        
        # 饼图类别数限制
        if chart_type == ChartType.PIE:
            cat_col = [c for c in columns if column_types[c] == "categorical"][0]
            # 假设类别数过多时降低分数
            score -= 0.1  # 保守调整
        
        # 散点图：如果相关性很弱则降低分数
        if chart_type == ChartType.SCATTER and statistics:
            if "correlations" in statistics and statistics["correlations"].get("available"):
                strong_pairs = statistics["correlations"].get("strong_pairs", [])
                col_pair = tuple(columns[:2])
                has_strong = any(
                    (p["col1"] in col_pair and p["col2"] in col_pair) 
                    for p in strong_pairs
                )
                if not has_strong:
                    score -= 0.2
        
        # 水平柱状图：如果类别名称很长则加分
        if chart_type == ChartType.HORIZONTAL_BAR:
            cat_col = [c for c in columns if column_types[c] == "categorical"][0]
            score += 0.05  # 略微加分
        
        return max(0, min(1, score))
    
    @staticmethod
    def _generate_title(chart_type: ChartType, columns: List[str]) -> str:
        """生成图表标题"""
        titles = {
            ChartType.LINE: "趋势变化",
            ChartType.BAR: "类别对比",
            ChartType.PIE: "构成占比",
            ChartType.SCATTER: "变量关系",
            ChartType.HISTOGRAM: "分布特征",
            ChartType.BOX: "分布与异常",
            ChartType.HEATMAP: "矩阵热力",
            ChartType.AREA: "累积趋势",
            ChartType.GROUPED_BAR: "多维度对比",
            ChartType.STACKED_BAR: "构成对比",
            ChartType.HORIZONTAL_BAR: "排名对比",
            ChartType.BUBBLE: "三维关系",
            ChartType.TREEMAP: "层级构成",
            ChartType.RADAR: "多维特征",
            ChartType.LOLLIPOP: "排名展示",
            ChartType.CORR_MATRIX: "相关性矩阵",
        }
        base = titles.get(chart_type, "数据可视化")
        return f"{base} ({' vs '.join(columns[:2])})"
    
    @staticmethod
    def _generate_why(chart_type: ChartType, columns: List[str], column_types: Dict[str, str]) -> str:
        """生成推荐理由"""
        type_str = ", ".join([f"{c}({column_types[c]})" for c in columns])
        return f"选择 {chart_type.value} 是因为数据包含 {type_str}，适合展示该类图表擅长的信息"
    
    @staticmethod
    def _deduplicate(recommendations: List[ChartRecommendation]) -> List[ChartRecommendation]:
        """去重：相同图表类型和列组合只保留置信度最高的"""
        seen = {}
        for rec in recommendations:
            key = (rec.chart_type, tuple(rec.columns))
            if key not in seen or rec.confidence > seen[key].confidence:
                seen[key] = rec
        return list(seen.values())
