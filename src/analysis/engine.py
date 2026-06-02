"""
多维度分析引擎 — 交叉分析、透视分析、分组聚合

核心能力：
- 交叉分析：类别 x 类别 → 数值聚合
- 透视分析：多维切片与钻取
- 分组聚合：多维度统计摘要
- 排名分析：Top N / Bottom N / 变化率
- 对比分析：同比/环比/差异分析
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats


class AnalysisType(Enum):
    """分析类型"""
    CROSS = "cross"              # 交叉分析
    PIVOT = "pivot"              # 透视分析
    GROUP = "group"              # 分组聚合
    RANK = "rank"                # 排名分析
    COMPARE = "compare"          # 对比分析
    SEGMENT = "segment"          # 分段分析


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_type: AnalysisType
    title: str
    description: str
    data: Any  # DataFrame / Dict / List
    metrics: Dict[str, Any] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    columns_used: List[str] = field(default_factory=list)


class MultiDimensionAnalyzer:
    """多维度分析器"""
    
    def __init__(self, df: pd.DataFrame, column_types: Dict[str, str]):
        self.df = df
        self.column_types = column_types
        self.cat_cols = [c for c, t in column_types.items() if t in ["categorical", "boolean"]]
        self.num_cols = [c for c, t in column_types.items() if t == "numeric"]
        self.dt_cols = [c for c, t in column_types.items() if t == "datetime"]
    
    def analyze(self, analysis_type: AnalysisType = None) -> List[AnalysisResult]:
        """
        执行多维度分析
        
        Args:
            analysis_type: 指定分析类型，None 则全部执行
            
        Returns:
            分析结果列表
        """
        results = []
        
        if analysis_type is None or analysis_type == AnalysisType.CROSS:
            cross_results = self._cross_analysis()
            results.extend(cross_results)
        
        if analysis_type is None or analysis_type == AnalysisType.RANK:
            rank_results = self._rank_analysis()
            results.extend(rank_results)
        
        if analysis_type is None or analysis_type == AnalysisType.COMPARE:
            compare_results = self._compare_analysis()
            results.extend(compare_results)
        
        if analysis_type is None or analysis_type == AnalysisType.SEGMENT:
            segment_results = self._segment_analysis()
            results.extend(segment_results)
        
        return results
    
    def _cross_analysis(self) -> List[AnalysisResult]:
        """交叉分析：类别 x 类别 → 数值"""
        results = []
        
        if len(self.cat_cols) >= 2 and len(self.num_cols) >= 1:
            for i, cat1 in enumerate(self.cat_cols[:2]):
                for cat2 in self.cat_cols[i+1:3]:
                    for num_col in self.num_cols[:1]:
                        pivot = self.df.pivot_table(
                            values=num_col,
                            index=cat1,
                            columns=cat2,
                            aggfunc='sum',
                            fill_value=0
                        )
                        
                        # 计算 insights
                        total = pivot.sum().sum()
                        max_cell = pivot.stack().idxmax()
                        max_value = pivot.stack().max()
                        max_pct = max_value / total * 100 if total > 0 else 0
                        
                        insights = [
                            f"最强组合：{max_cell[0]} x {max_cell[1]} = {max_value:.0f}（{max_pct:.1f}%）"
                        ]
                        
                        # 检测不均衡
                        row_totals = pivot.sum(axis=1)
                        if row_totals.max() / row_totals.sum() > 0.6:
                            insights.append(
                                f"{cat1} 分布不均：{row_totals.idxmax()} 占 {(row_totals.max()/row_totals.sum()*100):.1f}%"
                            )
                        
                        results.append(AnalysisResult(
                            analysis_type=AnalysisType.CROSS,
                            title=f"{cat1} × {cat2} 的 {num_col} 交叉分析",
                            description=f"分析不同 {cat1} 和 {cat2} 组合下的 {num_col} 分布",
                            data=pivot.to_dict(),
                            metrics={
                                "total": total,
                                "max_cell": f"{max_cell[0]} - {max_cell[1]}",
                                "max_value": max_value
                            },
                            insights=insights,
                            columns_used=[cat1, cat2, num_col]
                        ))
        
        return results
    
    def _rank_analysis(self) -> List[AnalysisResult]:
        """排名分析：Top N / Bottom N"""
        results = []
        
        for cat_col in self.cat_cols[:2]:
            for num_col in self.num_cols[:2]:
                grouped = self.df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
                
                top5 = grouped.head(5)
                bottom5 = grouped.tail(5)
                total = grouped.sum()
                
                insights = [
                    f"Top 1：{top5.index[0]} = {top5.iloc[0]:.0f}（{top5.iloc[0]/total*100:.1f}%）",
                    f"Top 5 合计：{top5.sum():.0f}（{top5.sum()/total*100:.1f}%）",
                ]
                
                # 检测长尾
                if len(grouped) > 5:
                    tail_pct = grouped.iloc[5:].sum() / total * 100
                    insights.append(f"尾部（第6名以后）合计：{tail_pct:.1f}%")
                
                results.append(AnalysisResult(
                    analysis_type=AnalysisType.RANK,
                    title=f"{cat_col} 的 {num_col} 排名分析",
                    description=f"{cat_col} 按 {num_col} 排序的 Top 5 和 Bottom 5",
                    data={
                        "top5": {k: round(v, 2) for k, v in top5.to_dict().items()},
                        "bottom5": {k: round(v, 2) for k, v in bottom5.to_dict().items()}
                    },
                    metrics={
                        "total": total,
                        "top1_share": top5.iloc[0] / total * 100 if total > 0 else 0,
                        "top5_share": top5.sum() / total * 100 if total > 0 else 0,
                    },
                    insights=insights,
                    columns_used=[cat_col, num_col]
                ))
        
        return results
    
    def _compare_analysis(self) -> List[AnalysisResult]:
        """对比分析：同比/环比/差异"""
        results = []
        
        if len(self.dt_cols) >= 1 and len(self.num_cols) >= 1:
            dt_col = self.dt_cols[0]
            for num_col in self.num_cols[:2]:
                df = self.df[[dt_col, num_col]].copy()
                df[dt_col] = pd.to_datetime(df[dt_col])
                
                # 按月聚合
                df['month'] = df[dt_col].dt.to_period('M')
                monthly = df.groupby('month')[num_col].sum()
                
                if len(monthly) >= 2:
                    # 环比
                    mom = monthly.pct_change() * 100
                    latest_mom = mom.iloc[-1]
                    
                    insights = []
                    if abs(latest_mom) > 10:
                        direction = "增长" if latest_mom > 0 else "下降"
                        insights.append(
                            f"最新月环比{direction} {abs(latest_mom):.1f}%，{'变化显著' if abs(latest_mom) > 20 else '值得关注'}"
                        )
                    
                    # 最大增长/下降
                    max_growth = mom.max()
                    max_decline = mom.min()
                    insights.append(
                        f"最大环比增长：{mom.idxmax()} ({max_growth:.1f}%) | "
                        f"最大环比下降：{mom.idxmin()} ({max_decline:.1f}%)"
                    )
                    
                    results.append(AnalysisResult(
                        analysis_type=AnalysisType.COMPARE,
                        title=f"{num_col} 的月度环比分析",
                        description=f"{num_col} 逐月变化趋势及环比增长率",
                        data={
                            "monthly": {str(k): round(v, 2) for k, v in monthly.to_dict().items()},
                            "mom": {str(k): round(v, 2) for k, v in mom.dropna().to_dict().items()}
                        },
                        metrics={
                            "latest_mom": latest_mom,
                            "max_growth": max_growth,
                            "max_decline": max_decline,
                            "avg_mom": mom.mean()
                        },
                        insights=insights,
                        columns_used=[dt_col, num_col]
                    ))
        
        return results
    
    def _segment_analysis(self) -> List[AnalysisResult]:
        """分段分析：将数值分段后分析"""
        results = []
        
        for num_col in self.num_cols[:2]:
            for cat_col in self.cat_cols[:1]:
                # 等频分箱
                try:
                    self.df[f'{num_col}_segment'] = pd.qcut(
                        self.df[num_col], 
                        q=5, 
                        labels=['低', '中低', '中', '中高', '高'],
                        duplicates='drop'
                    )
                    
                    segment_analysis = self.df.groupby([f'{num_col}_segment', cat_col]).size().unstack(fill_value=0)
                    
                    insights = []
                    # 检测哪个类别在高分段占优
                    if '高' in segment_analysis.index:
                        high_segment = segment_analysis.loc['高']
                        dominant = high_segment.idxmax()
                        insights.append(
                            f"高分段中，{dominant} 数量最多（{high_segment.max()}）"
                        )
                    
                    results.append(AnalysisResult(
                        analysis_type=AnalysisType.SEGMENT,
                        title=f"{num_col} 分段 × {cat_col} 分析",
                        description=f"将 {num_col} 分为 5 段后观察 {cat_col} 分布",
                        data=segment_analysis.to_dict(),
                        metrics={
                            "segments": 5
                        },
                        insights=insights,
                        columns_used=[num_col, cat_col]
                    ))
                    
                    # 清理临时列
                    self.df = self.df.drop(columns=[f'{num_col}_segment'])
                    
                except Exception:
                    pass
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        return {
            "cat_cols": self.cat_cols,
            "num_cols": self.num_cols,
            "dt_cols": self.dt_cols,
            "total_rows": len(self.df),
            "total_columns": len(self.df.columns)
        }