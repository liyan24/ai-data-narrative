"""
数据洞察引擎 — 基于统计规则自动生成数据洞察（无需 LLM）

核心能力：
- 趋势洞察：上升/下降/波动检测
- 分布洞察：偏态、多峰、异常值聚集
- 对比洞察：Top N、极值、差异显著性
- 关系洞察：相关性强弱、正/负相关
- 构成洞察：占比、集中度（赫芬达尔指数）
- 质量洞察：缺失模式、重复模式
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats


class InsightSeverity(Enum):
    """洞察重要性级别"""
    CRITICAL = "critical"    # 需要立即关注
    HIGH = "high"            # 重要发现
    MEDIUM = "medium"        # 值得注意
    LOW = "low"              # 补充信息


class InsightCategory(Enum):
    """洞察类别"""
    TREND = "trend"              # 趋势
    DISTRIBUTION = "distribution" # 分布
    COMPARISON = "comparison"      # 对比
    RELATIONSHIP = "relationship" # 关系
    COMPOSITION = "composition"   # 构成
    QUALITY = "quality"           # 质量
    ANOMALY = "anomaly"          # 异常


@dataclass
class DataInsight:
    """单条数据洞察"""
    category: InsightCategory
    severity: InsightSeverity
    title: str
    description: str
    metric: str = ""              # 涉及的指标
    value: Any = None             # 具体数值
    recommendation: str = ""      # 建议行动
    columns: List[str] = field(default_factory=list)  # 相关列


class InsightEngine:
    """数据洞察引擎 — 基于统计规则自动发现"""
    
    def __init__(self, df: pd.DataFrame, column_types: Dict[str, str]):
        self.df = df
        self.column_types = column_types
        self.insights: List[DataInsight] = []
    
    def generate_all(self) -> List[DataInsight]:
        """生成所有类型的洞察"""
        self.insights = []
        
        self._analyze_trends()
        self._analyze_distribution()
        self._analyze_comparison()
        self._analyze_relationships()
        self._analyze_composition()
        self._analyze_anomalies()
        
        # 按严重级别排序
        severity_order = {
            InsightSeverity.CRITICAL: 0,
            InsightSeverity.HIGH: 1,
            InsightSeverity.MEDIUM: 2,
            InsightSeverity.LOW: 3
        }
        self.insights.sort(key=lambda x: severity_order[x.severity])
        
        return self.insights
    
    def _analyze_trends(self):
        """分析趋势洞察"""
        dt_cols = [c for c, t in self.column_types.items() if t == "datetime"]
        num_cols = [c for c, t in self.column_types.items() if t == "numeric"]
        
        for dt_col in dt_cols[:1]:  # 只分析第一个时间列
            for num_col in num_cols[:3]:  # 最多3个数值列
                trend_insight = self._detect_trend(dt_col, num_col)
                if trend_insight:
                    self.insights.append(trend_insight)
    
    def _detect_trend(self, dt_col: str, num_col: str) -> Optional[DataInsight]:
        """检测时间序列趋势"""
        df = self.df[[dt_col, num_col]].dropna().sort_values(dt_col)
        if len(df) < 10:
            return None
        
        # 按时间聚合（日/周/月）
        df[dt_col] = pd.to_datetime(df[dt_col])
        if (df[dt_col].max() - df[dt_col].min()).days > 60:
            # 按月聚合
            df['period'] = df[dt_col].dt.to_period('M')
        else:
            df['period'] = df[dt_col].dt.to_period('W')
        
        monthly = df.groupby('period')[num_col].sum()
        if len(monthly) < 3:
            return None
        
        # 计算线性趋势
        x = np.arange(len(monthly))
        y = monthly.values
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # 计算波动
        volatility = np.std(y) / np.mean(y) if np.mean(y) != 0 else 0
        
        # 判断趋势类型
        if abs(r_value) > 0.7 and p_value < 0.05:
            direction = "上升" if slope > 0 else "下降"
            change_pct = abs(slope * len(monthly) / np.mean(y) * 100) if np.mean(y) != 0 else 0
            
            return DataInsight(
                category=InsightCategory.TREND,
                severity=InsightSeverity.HIGH if change_pct > 50 else InsightSeverity.MEDIUM,
                title=f"{num_col} 呈现显著{direction}趋势",
                description=f"{num_col} 在观察期内呈现显著{direction}趋势，线性相关系数 R²={r_value**2:.2f}。"
                           f"整体变化幅度约 {change_pct:.1f}%。"
                           f"{'波动较大' if volatility > 0.3 else '波动平稳'}（波动系数: {volatility:.1%}）。",
                metric=num_col,
                value={"slope": slope, "r2": r_value**2, "volatility": volatility},
                recommendation=f"建议关注{num_col}的{direction}驱动因素，{'并评估波动风险' if volatility > 0.3 else '保持当前策略'}。",
                columns=[dt_col, num_col]
            )
        elif volatility > 0.5:
            return DataInsight(
                category=InsightCategory.TREND,
                severity=InsightSeverity.MEDIUM,
                title=f"{num_col} 波动显著，无明显趋势",
                description=f"{num_col} 未呈现显著线性趋势（R²={r_value**2:.2f}），但波动较大（波动系数: {volatility:.1%}）。",
                metric=num_col,
                value={"volatility": volatility},
                recommendation="建议深入分析波动原因，考虑季节性因素或外部事件影响。",
                columns=[dt_col, num_col]
            )
        
        return None
    
    def _analyze_distribution(self):
        """分析分布洞察"""
        num_cols = [c for c, t in self.column_types.items() if t == "numeric"]
        
        for col in num_cols:
            series = self.df[col].dropna()
            if len(series) < 10:
                continue
            
            # 偏度检测
            skewness = series.skew()
            if abs(skewness) > 1:
                direction = "右偏（正偏态）" if skewness > 0 else "左偏（负偏态）"
                self.insights.append(DataInsight(
                    category=InsightCategory.DISTRIBUTION,
                    severity=InsightSeverity.MEDIUM if abs(skewness) > 2 else InsightSeverity.LOW,
                    title=f"{col} 分布呈{direction}",
                    description=f"{col} 的偏度系数为 {skewness:.2f}，{'远大于' if abs(skewness) > 2 else '大于'}正态分布的阈值。"
                               f"意味着数据分布不对称，{'尾部向右延伸，存在较多高值' if skewness > 0 else '尾部向左延伸，存在较多低值'}。"
                               f"中位数 ({series.median():.2f}) {'低于' if skewness > 0 else '高于'}均值 ({series.mean():.2f})。",
                    metric=col,
                    value=skewness,
                    recommendation="建议使用中位数而非均值作为典型值参考，或考虑对数据进行对数变换。",
                    columns=[col]
                ))
            
            # 峰度检测
            kurtosis = series.kurtosis()
            if kurtosis > 3:
                self.insights.append(DataInsight(
                    category=InsightCategory.DISTRIBUTION,
                    severity=InsightSeverity.LOW,
                    title=f"{col} 分布峰度较高（尖峰）",
                    description=f"{col} 的峰度系数为 {kurtosis:.2f}，高于正态分布（3.0），呈现尖峰特征。"
                               f"数据在均值附近更集中，同时尾部更厚。",
                    metric=col,
                    value=kurtosis,
                    recommendation="尖峰分布可能意味着数据存在聚集现象，建议检查是否有隐性的分组因素。",
                    columns=[col]
                ))
    
    def _analyze_comparison(self):
        """分析对比洞察"""
        cat_cols = [c for c, t in self.column_types.items() if t in ["categorical", "boolean"]]
        num_cols = [c for c, t in self.column_types.items() if t == "numeric"]
        
        for cat_col in cat_cols[:2]:  # 最多2个类别列
            for num_col in num_cols[:2]:  # 最多2个数值列
                self._detect_top_bottom(cat_col, num_col)
                self._detect_extreme_gap(cat_col, num_col)
    
    def _detect_top_bottom(self, cat_col: str, num_col: str):
        """检测 Top/Bottom 项"""
        grouped = self.df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
        if len(grouped) < 3:
            return
        
        total = grouped.sum()
        top1 = grouped.iloc[0]
        top1_name = grouped.index[0]
        top1_pct = top1 / total * 100 if total > 0 else 0
        
        bottom1 = grouped.iloc[-1]
        bottom1_name = grouped.index[-1]
        
        top3_sum = grouped.head(3).sum()
        top3_pct = top3_sum / total * 100 if total > 0 else 0
        
        # Top 1 占比过高
        if top1_pct > 50:
            self.insights.append(DataInsight(
                category=InsightCategory.COMPARISON,
                severity=InsightSeverity.HIGH,
                title=f"{top1_name} 在 {cat_col} 中占绝对主导地位",
                description=f"{top1_name} 的 {num_col} 占整体的 {top1_pct:.1f}%，"
                           f"远超其他 {cat_col}。"
                           f"Top 3 合计占比 {top3_pct:.1f}%。",
                metric=num_col,
                value={"top1_pct": top1_pct, "top3_pct": top3_pct},
                recommendation=f"{top1_name} 是核心支柱，建议确保其稳定性，同时关注其他 {cat_col} 的增长潜力。",
                columns=[cat_col, num_col]
            ))
        elif top3_pct > 70:
            self.insights.append(DataInsight(
                category=InsightCategory.COMPARISON,
                severity=InsightSeverity.MEDIUM,
                title=f"{cat_col} 的 {num_col} 高度集中在 Top 3",
                description=f"前 3 个 {cat_col} 合计贡献了 {top3_pct:.1f}% 的 {num_col}，"
                           f"其中 {top1_name} 占 {top1_pct:.1f}%。"
                           f"集中度较高，尾部 {cat_col} 占比较低。",
                metric=num_col,
                value={"top3_pct": top3_pct},
                recommendation="头部效应明显，建议通过差异化策略激活尾部类别。",
                columns=[cat_col, num_col]
            ))
        
        # 极值差异
        if top1 > bottom1 * 10 and bottom1 > 0:
            ratio = top1 / bottom1
            self.insights.append(DataInsight(
                category=InsightCategory.COMPARISON,
                severity=InsightSeverity.MEDIUM,
                title=f"{cat_col} 间 {num_col} 差异悬殊",
                description=f"最高的 {top1_name}（{top1:.0f}）是最低的 {bottom1_name}（{bottom1:.0f}）的 {ratio:.1f} 倍。"
                           f"两极分化严重。",
                metric=num_col,
                value=ratio,
                recommendation="建议分析两极差异的根本原因，制定针对性改进方案。",
                columns=[cat_col, num_col]
            ))
    
    def _detect_extreme_gap(self, cat_col: str, num_col: str):
        """检测类别间的统计显著性差异"""
        groups = [g[num_col].dropna() for name, g in self.df.groupby(cat_col) if len(g) > 5]
        if len(groups) < 2:
            return
        
        # 使用 ANOVA 检测差异
        try:
            f_stat, p_value = stats.f_oneway(*groups)
            if p_value < 0.05:
                self.insights.append(DataInsight(
                    category=InsightCategory.COMPARISON,
                    severity=InsightSeverity.MEDIUM if p_value < 0.01 else InsightSeverity.LOW,
                    title=f"不同 {cat_col} 的 {num_col} 存在显著差异",
                    description=f"ANOVA 检验显示，不同 {cat_col} 的 {num_col} 均值存在统计显著差异"
                               f"（F={f_stat:.2f}, p={p_value:.4f}）。"
                               f"{'差异极强' if p_value < 0.001 else '差异明显'}。",
                    metric=num_col,
                    value={"f_stat": f_stat, "p_value": p_value},
                    recommendation=f"{cat_col} 是影响 {num_col} 的重要因素，建议分层分析。",
                    columns=[cat_col, num_col]
                ))
        except Exception:
            pass
    
    def _analyze_relationships(self):
        """分析变量关系洞察"""
        num_cols = [c for c, t in self.column_types.items() if t == "numeric"]
        if len(num_cols) < 2:
            return
        
        # 计算相关性矩阵
        corr_matrix = self.df[num_cols].corr()
        
        # 提取强相关对
        strong_pairs = []
        for i in range(len(num_cols)):
            for j in range(i+1, len(num_cols)):
                corr = corr_matrix.iloc[i, j]
                if abs(corr) > 0.5:
                    strong_pairs.append((num_cols[i], num_cols[j], corr))
        
        # 按相关强度排序
        strong_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        
        for col1, col2, corr in strong_pairs[:3]:  # 最多3对
            direction = "正" if corr > 0 else "负"
            strength = "强" if abs(corr) > 0.8 else "中等"
            
            self.insights.append(DataInsight(
                category=InsightCategory.RELATIONSHIP,
                severity=InsightSeverity.HIGH if abs(corr) > 0.8 else InsightSeverity.MEDIUM,
                title=f"{col1} 与 {col2} 存在{strength}{direction}相关",
                description=f"{col1} 和 {col2} 的 Pearson 相关系数为 {corr:.3f}，"
                           f"呈{strength}{direction}相关。"
                           f"{'一个变量增加时另一个也趋向增加' if corr > 0 else '一个变量增加时另一个趋向减少'}。"
                           f"{'相关性极强，可能存在因果关系或共同驱动因素' if abs(corr) > 0.8 else '值得关注的关系'}。",
                metric=f"{col1} vs {col2}",
                value=corr,
                recommendation=f"建议深入分析两变量的{'共同驱动因素' if abs(corr) > 0.8 else '关系机制'}，"
                               f"{'考虑用其一预测另一' if abs(corr) > 0.8 else '注意排除混杂因素'}。",
                columns=[col1, col2]
            ))
    
    def _analyze_composition(self):
        """分析构成洞察"""
        cat_cols = [c for c, t in self.column_types.items() if t in ["categorical", "boolean"]]
        num_cols = [c for c, t in self.column_types.items() if t == "numeric"]
        
        for cat_col in cat_cols[:1]:
            for num_col in num_cols[:1]:
                self._detect_composition_concentration(cat_col, num_col)
    
    def _detect_composition_concentration(self, cat_col: str, num_col: str):
        """检测构成集中度"""
        grouped = self.df.groupby(cat_col)[num_col].sum()
        total = grouped.sum()
        if total == 0 or len(grouped) < 3:
            return
        
        # 赫芬达尔指数 (HHI)
        shares = grouped / total
        hhi = (shares ** 2).sum()
        
        # HHI > 0.25 表示高度集中，0.15-0.25 中度集中，< 0.15 分散
        if hhi > 0.25:
            level = "高度集中"
            severity = InsightSeverity.HIGH
        elif hhi > 0.15:
            level = "中度集中"
            severity = InsightSeverity.MEDIUM
        else:
            level = "相对分散"
            severity = InsightSeverity.LOW
        
        top1_name = grouped.index[grouped.argmax()]
        top1_share = shares.max() * 100
        
        self.insights.append(DataInsight(
            category=InsightCategory.COMPOSITION,
            severity=severity,
            title=f"{cat_col} 的 {num_col} 构成{level}",
            description=f"{cat_col} 的 {num_col} 分布 HHI 指数为 {hhi:.3f}，属于{level}。"
                       f"{top1_name} 占最大份额（{top1_share:.1f}%）。"
                       f"{'少数类别主导整体，存在集中度风险' if hhi > 0.25 else '分布相对均衡' if hhi < 0.15 else '集中度适中'}。",
            metric=num_col,
            value={"hhi": hhi, "top1_share": top1_share},
            recommendation=f"{'建议降低对单一类别的依赖，分散风险' if hhi > 0.25 else '当前结构良好，保持关注'}。",
            columns=[cat_col, num_col]
        ))
    
    def _analyze_anomalies(self):
        """分析异常洞察"""
        num_cols = [c for c, t in self.column_types.items() if t == "numeric"]
        
        for col in num_cols[:3]:
            series = self.df[col].dropna()
            if len(series) < 10:
                continue
            
            # Z-Score 检测
            z_scores = np.abs(stats.zscore(series))
            outliers = series[z_scores > 3]
            
            if len(outliers) > 0:
                outlier_pct = len(outliers) / len(series) * 100
                self.insights.append(DataInsight(
                    category=InsightCategory.ANOMALY,
                    severity=InsightSeverity.HIGH if outlier_pct > 5 else InsightSeverity.MEDIUM,
                    title=f"{col} 发现 {len(outliers)} 个统计异常值",
                    description=f"使用 Z-Score 方法（|z| > 3）检测到 {len(outliers)} 个异常值，"
                               f"占总数 {outlier_pct:.1f}%。"
                               f"异常值范围: {outliers.min():.2f} ~ {outliers.max():.2f}。"
                               f"正常范围: {series.mean():.2f} ± {3*series.std():.2f}。",
                    metric=col,
                    value={"count": len(outliers), "percentage": outlier_pct},
                    recommendation=f"{'异常值比例较高，建议检查数据采集或业务逻辑' if outlier_pct > 5 else '建议逐一核查异常值，确认是否为真实业务现象'}。",
                    columns=[col]
                ))
    
    def to_markdown(self, top_n: int = 10) -> str:
        """将洞察转换为 Markdown 文本"""
        lines = ["## 数据洞察", ""]
        
        for i, insight in enumerate(self.insights[:top_n]):
            emoji_map = {
                InsightSeverity.CRITICAL: "🚨",
                InsightSeverity.HIGH: "🔴",
                InsightSeverity.MEDIUM: "🟡",
                InsightSeverity.LOW: "🔵"
            }
            emoji = emoji_map.get(insight.severity, "⚪")
            
            lines.append(f"### {emoji} {insight.title}")
            lines.append(f"**类别**: {insight.category.value} | **级别**: {insight.severity.value}")
            lines.append("")
            lines.append(insight.description)
            if insight.recommendation:
                lines.append(f"\n💡 **建议**: {insight.recommendation}")
            lines.append("")
        
        return "\n".join(lines)
