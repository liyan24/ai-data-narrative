"""
高级图表引擎 — 扩展图表类型（箱线图、热力图、散点图矩阵、桑基图）

核心能力：
- 箱线图：展示数值分布、异常值
- 热力图：展示相关性矩阵、交叉表
- 散点图矩阵：多变量关系探索
- 桑基图：流向/构成分析
- 小提琴图：分布密度对比
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from pathlib import Path
import base64
import io

import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

from src.config import VIZ_CONFIG

matplotlib.use('Agg')


class AdvancedChartType(Enum):
    """高级图表类型"""
    BOXPLOT = "boxplot"              # 箱线图
    HEATMAP = "heatmap"              # 热力图
    SCATTER_MATRIX = "scatter_matrix"  # 散点图矩阵
    SANKEY = "sankey"                # 桑基图（简化为流向图）
    VIOLIN = "violin"                # 小提琴图
    PAIRPLOT = "pairplot"            # 配对图


class AdvancedChartEngine:
    """高级图表引擎"""
    
    def __init__(self):
        self.colors = VIZ_CONFIG["color_palette"]
        self.width = VIZ_CONFIG["default_width"] / 100
        self.height = VIZ_CONFIG["default_height"] / 100
        self.dpi = VIZ_CONFIG["dpi"]
    
    def generate(self, df: pd.DataFrame, chart_type: AdvancedChartType,
                 columns: List[str], title: str = "", **kwargs) -> str:
        """生成高级图表"""
        fig = None
        
        if chart_type == AdvancedChartType.BOXPLOT:
            fig = self._boxplot(df, columns, title)
        elif chart_type == AdvancedChartType.HEATMAP:
            fig = self._heatmap(df, columns, title)
        elif chart_type == AdvancedChartType.SCATTER_MATRIX:
            fig = self._scatter_matrix(df, columns, title)
        elif chart_type == AdvancedChartType.VIOLIN:
            fig = self._violin(df, columns, title)
        elif chart_type == AdvancedChartType.SANKEY:
            fig = self._sankey(df, columns, title)
        elif chart_type == AdvancedChartType.PAIRPLOT:
            fig = self._pairplot(df, columns, title)
        else:
            return "[ERROR] 不支持的图表类型"
        
        if fig is None:
            return "[ERROR] 图表生成失败"
        
        return self._fig_to_base64(fig)
    
    def _boxplot(self, df: pd.DataFrame, columns: List[str], title: str) -> plt.Figure:
        """箱线图 — 展示数值分布和异常值"""
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
        if not numeric_cols:
            return None
        
        fig, ax = plt.subplots(figsize=(self.width, self.height))
        
        data_to_plot = [df[c].dropna() for c in numeric_cols[:6]]  # 最多6个
        bp = ax.boxplot(data_to_plot, labels=numeric_cols[:6], patch_artist=True)
        
        for patch, color in zip(bp['boxes'], self.colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_title(title or "数值分布箱线图", fontsize=14, fontweight='bold')
        ax.set_ylabel("数值", fontsize=12)
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        return fig
    
    def _heatmap(self, df: pd.DataFrame, columns: List[str], title: str) -> plt.Figure:
        """热力图 — 展示相关性矩阵或交叉表"""
        # 如果 columns 都是数值型，计算相关性
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
        
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr()
            data = corr.values
            labels = numeric_cols
            cmap = 'RdBu_r'
            vmin, vmax = -1, 1
        else:
            # 否则尝试类别交叉表
            cat_cols = [c for c in columns if not pd.api.types.is_numeric_dtype(df[c])]
            if len(cat_cols) >= 2:
                crosstab = pd.crosstab(df[cat_cols[0]], df[cat_cols[1]])
                data = crosstab.values
                labels = crosstab.columns.tolist()
                row_labels = crosstab.index.tolist()
                cmap = 'YlOrRd'
                vmin, vmax = None, None
            else:
                return None
        
        fig, ax = plt.subplots(figsize=(max(self.width, len(labels)*0.5), self.height))
        
        im = ax.imshow(data, cmap=cmap, aspect='auto', vmin=vmin, vmax=vmax)
        
        # 设置标签
        if 'row_labels' in dir():
            ax.set_yticks(range(len(row_labels)))
            ax.set_yticklabels(row_labels)
        else:
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels)
        
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        
        # 添加数值标注
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                text = ax.text(j, i, f'{data[i, j]:.2f}' if abs(data[i, j]) < 10 else f'{data[i, j]:.0f}',
                             ha="center", va="center", color="black" if abs(data[i, j]) < 0.5 else "white",
                             fontsize=8)
        
        ax.set_title(title or "热力图", fontsize=14, fontweight='bold')
        plt.colorbar(im, ax=ax)
        plt.tight_layout()
        return fig
    
    def _scatter_matrix(self, df: pd.DataFrame, columns: List[str], title: str) -> plt.Figure:
        """散点图矩阵 — 多变量关系探索"""
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric_cols) < 2:
            return None
        
        cols = numeric_cols[:4]  # 最多4个避免过大
        n = len(cols)
        
        fig, axes = plt.subplots(n, n, figsize=(n*2.5, n*2.5))
        if n == 1:
            axes = np.array([[axes]])
        
        for i, col_i in enumerate(cols):
            for j, col_j in enumerate(cols):
                ax = axes[i, j]
                
                if i == j:
                    # 对角线：直方图
                    ax.hist(df[col_i].dropna(), bins=20, color=self.colors[0], alpha=0.7)
                    ax.set_title(col_i, fontsize=10)
                else:
                    # 非对角线：散点图
                    ax.scatter(df[col_j], df[col_i], alpha=0.5, s=10, color=self.colors[1])
                    
                    # 计算相关系数
                    corr = df[[col_i, col_j]].corr().iloc[0, 1]
                    ax.annotate(f'r={corr:.2f}', xy=(0.05, 0.95), xycoords='axes fraction',
                               fontsize=9, fontweight='bold')
                
                if i < n - 1:
                    ax.set_xticklabels([])
                if j > 0:
                    ax.set_yticklabels([])
        
        fig.suptitle(title or "散点图矩阵", fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        return fig
    
    def _violin(self, df: pd.DataFrame, columns: List[str], title: str) -> plt.Figure:
        """小提琴图 — 分布密度对比"""
        # columns: [数值列, 类别列]
        if len(columns) < 2:
            return None
        
        num_col = columns[0]
        cat_col = columns[1]
        
        if not pd.api.types.is_numeric_dtype(df[num_col]):
            return None
        
        categories = df[cat_col].unique()
        if len(categories) > 8:
            categories = categories[:8]
        
        fig, ax = plt.subplots(figsize=(self.width, self.height))
        
        positions = range(len(categories))
        violin_data = [df[df[cat_col] == cat][num_col].dropna().values for cat in categories]
        
        parts = ax.violinplot(violin_data, positions=positions, showmeans=True, showmedians=True)
        
        for pc, color in zip(parts['bodies'], self.colors):
            pc.set_facecolor(color)
            pc.set_alpha(0.7)
        
        ax.set_xticks(positions)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.set_title(title or f"{num_col} 按 {cat_col} 分布", fontsize=14, fontweight='bold')
        ax.set_ylabel(num_col, fontsize=12)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def _sankey(self, df: pd.DataFrame, columns: List[str], title: str) -> plt.Figure:
        """简化为流向图/堆叠条形图 — 展示构成流向"""
        if len(columns) < 2:
            return None
        
        source_col = columns[0]  # 来源类别
        target_col = columns[1]  # 目标类别
        value_col = columns[2] if len(columns) > 2 else None  # 数值列
        
        if value_col and pd.api.types.is_numeric_dtype(df[value_col]):
            grouped = df.groupby([source_col, target_col])[value_col].sum().unstack(fill_value=0)
        else:
            grouped = pd.crosstab(df[source_col], df[target_col])
        
        fig, ax = plt.subplots(figsize=(self.width, self.height))
        
        grouped.plot(kind='bar', stacked=True, ax=ax, color=self.colors[:len(grouped.columns)])
        
        ax.set_title(title or f"{source_col} → {target_col} 流向", fontsize=14, fontweight='bold')
        ax.set_xlabel(source_col, fontsize=12)
        ax.set_ylabel(value_col or "数量", fontsize=12)
        ax.legend(title=target_col, bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        return fig
    
    def _pairplot(self, df: pd.DataFrame, columns: List[str], title: str) -> plt.Figure:
        """配对图 — 增强版散点图矩阵，带回归线"""
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric_cols) < 2:
            return None
        
        cols = numeric_cols[:3]  # 最多3个
        n = len(cols)
        
        fig, axes = plt.subplots(n, n, figsize=(n*3, n*3))
        if n == 1:
            axes = np.array([[axes]])
        
        for i, col_i in enumerate(cols):
            for j, col_j in enumerate(cols):
                ax = axes[i, j]
                
                if i == j:
                    # KDE 密度图
                    data = df[col_i].dropna()
                    ax.hist(data, bins=20, density=True, alpha=0.6, color=self.colors[0])
                    
                    # 添加 KDE 曲线
                    from scipy.stats import gaussian_kde
                    kde = gaussian_kde(data)
                    x_range = np.linspace(data.min(), data.max(), 100)
                    ax.plot(x_range, kde(x_range), color=self.colors[1], linewidth=2)
                    ax.set_title(col_i, fontsize=11, fontweight='bold')
                else:
                    # 散点 + 回归线
                    x = df[col_j].dropna()
                    y = df[col_i].dropna()
                    
                    # 对齐数据
                    valid_idx = df[[col_i, col_j]].dropna().index
                    x_aligned = df.loc[valid_idx, col_j]
                    y_aligned = df.loc[valid_idx, col_i]
                    
                    ax.scatter(x_aligned, y_aligned, alpha=0.5, s=15, color=self.colors[2])
                    
                    # 线性回归
                    if len(x_aligned) > 2:
                        z = np.polyfit(x_aligned, y_aligned, 1)
                        p = np.poly1d(z)
                        x_line = np.linspace(x_aligned.min(), x_aligned.max(), 100)
                        ax.plot(x_line, p(x_line), color=self.colors[3], linewidth=2, linestyle='--')
                        
                        corr = df[[col_i, col_j]].corr().iloc[0, 1]
                        ax.annotate(f'r = {corr:.3f}', xy=(0.05, 0.95), 
                                   xycoords='axes fraction', fontsize=10,
                                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                if i < n - 1:
                    ax.set_xticklabels([])
                if j > 0:
                    ax.set_yticklabels([])
        
        fig.suptitle(title or "配对分析图", fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        return fig
    
    def _fig_to_base64(self, fig: plt.Figure) -> str:
        """将图表转换为 Base64"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    
    def recommend_advanced(self, df: pd.DataFrame, column_types: Dict[str, str],
                          top_k: int = 3) -> List[Dict[str, Any]]:
        """推荐高级图表"""
        recommendations = []
        num_cols = [c for c, t in column_types.items() if t == "numeric"]
        cat_cols = [c for c, t in column_types.items() if t in ["categorical", "boolean"]]
        
        # 箱线图：多个数值列
        if len(num_cols) >= 2:
            recommendations.append({
                "chart_type": AdvancedChartType.BOXPLOT,
                "columns": num_cols[:4],
                "title": "数值分布对比",
                "description": "箱线图展示各数值列的分布特征、中位数和异常值"
            })
        
        # 热力图：数值相关性或类别交叉
        if len(num_cols) >= 2:
            recommendations.append({
                "chart_type": AdvancedChartType.HEATMAP,
                "columns": num_cols[:6],
                "title": "相关性热力图",
                "description": "热力图展示数值列之间的相关性强弱"
            })
        elif len(cat_cols) >= 2:
            recommendations.append({
                "chart_type": AdvancedChartType.HEATMAP,
                "columns": cat_cols[:2],
                "title": "类别交叉热力图",
                "description": "热力图展示两个类别列的交叉频次"
            })
        
        # 散点图矩阵：3+ 数值列
        if len(num_cols) >= 3:
            recommendations.append({
                "chart_type": AdvancedChartType.SCATTER_MATRIX,
                "columns": num_cols[:4],
                "title": "多变量关系矩阵",
                "description": "散点图矩阵探索多个数值变量之间的关系"
            })
        
        # 小提琴图：数值 + 类别
        if len(num_cols) >= 1 and len(cat_cols) >= 1:
            recommendations.append({
                "chart_type": AdvancedChartType.VIOLIN,
                "columns": [num_cols[0], cat_cols[0]],
                "title": f"{num_cols[0]} 分布密度对比",
                "description": "小提琴图展示不同类别下的数值分布密度"
            })
        
        # 桑基/流向图：两个类别 + 数值
        if len(cat_cols) >= 2 and len(num_cols) >= 1:
            recommendations.append({
                "chart_type": AdvancedChartType.SANKEY,
                "columns": [cat_cols[0], cat_cols[1], num_cols[0]],
                "title": f"{cat_cols[0]} → {cat_cols[1]} 流向",
                "description": "堆叠条形图展示从来源到目标的数值流向"
            })
        
        # 配对图：2-3 数值列
        if len(num_cols) >= 2:
            recommendations.append({
                "chart_type": AdvancedChartType.PAIRPLOT,
                "columns": num_cols[:3],
                "title": "变量配对分析",
                "description": "配对图展示变量间的散点关系、回归线和密度分布"
            })
        
        return recommendations[:top_k]
