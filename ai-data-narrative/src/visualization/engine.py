"""
图表生成引擎 — 基于 matplotlib/plotly 生成图表
"""

import base64
import io
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import warnings

import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from src.config import VIZ_CONFIG
from src.visualization.recommender import ChartType

warnings.filterwarnings("ignore")

# 尝试设置中文字体
def _get_chinese_font():
    """获取可用的中文字体"""
    chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei']
    available = [f.name for f in fm.fontManager.ttflist]
    for font in chinese_fonts:
        if font in available:
            return font
    return None

_CHINESE_FONT = _get_chinese_font()
if _CHINESE_FONT:
    plt.rcParams['font.sans-serif'] = [_CHINESE_FONT] + plt.rcParams['font.sans-serif']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


class ChartEngine:
    """图表生成引擎"""
    
    def __init__(self, width: int = None, height: int = None, dpi: int = None):
        self.width = width or VIZ_CONFIG["default_width"]
        self.height = height or VIZ_CONFIG["default_height"]
        self.dpi = dpi or VIZ_CONFIG["dpi"]
        self.colors = VIZ_CONFIG["color_palette"]
    
    def generate(self, df: pd.DataFrame, chart_type: ChartType, 
                 columns: List[str], title: str = None, **kwargs) -> str:
        """
        生成图表并返回 base64 编码
        
        Args:
            df: 数据框
            chart_type: 图表类型
            columns: 使用的列
            title: 图表标题
            
        Returns:
            base64 编码的 PNG 图像
        """
        fig, ax = plt.subplots(figsize=(self.width / 100, self.height / 100), dpi=self.dpi)
        
        try:
            if chart_type == ChartType.BAR:
                self._draw_bar(df, columns, ax, **kwargs)
            elif chart_type == ChartType.LINE:
                self._draw_line(df, columns, ax, **kwargs)
            elif chart_type == ChartType.PIE:
                self._draw_pie(df, columns, ax, **kwargs)
            elif chart_type == ChartType.SCATTER:
                self._draw_scatter(df, columns, ax, **kwargs)
            elif chart_type == ChartType.HISTOGRAM:
                self._draw_histogram(df, columns, ax, **kwargs)
            elif chart_type == ChartType.BOX:
                self._draw_box(df, columns, ax, **kwargs)
            elif chart_type == ChartType.HEATMAP:
                self._draw_heatmap(df, columns, ax, **kwargs)
            elif chart_type == ChartType.HORIZONTAL_BAR:
                self._draw_horizontal_bar(df, columns, ax, **kwargs)
            elif chart_type == ChartType.AREA:
                self._draw_area(df, columns, ax, **kwargs)
            elif chart_type == ChartType.GROUPED_BAR:
                self._draw_grouped_bar(df, columns, ax, **kwargs)
            elif chart_type == ChartType.CORR_MATRIX:
                self._draw_corr_matrix(df, columns, ax, **kwargs)
            else:
                self._draw_bar(df, columns, ax, **kwargs)
            
            if title:
                ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
            
            plt.tight_layout()
            
            # 转 base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            return img_base64
            
        except Exception as e:
            plt.close(fig)
            return f"[图表生成错误] {str(e)}"
    
    def save(self, df: pd.DataFrame, chart_type: ChartType, columns: List[str], 
             output_path: str, title: str = None, **kwargs) -> Path:
        """保存图表到文件"""
        img_data = self.generate(df, chart_type, columns, title, **kwargs)
        if img_data.startswith("["):
            raise ValueError(img_data)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(img_data))
        
        return output_path
    
    def _draw_bar(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """柱状图"""
        cat_col = [c for c in columns if df[c].dtype == object or df[c].dtype.name == 'category'][0]
        num_col = [c for c in columns if np.issubdtype(df[c].dtype, np.number)][0]
        
        data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(15)
        colors = self.colors[:len(data)]
        bars = ax.bar(range(len(data)), data.values, color=colors, edgecolor='white', linewidth=0.5)
        ax.set_xticks(range(len(data)))
        ax.set_xticklabels(data.index, rotation=45, ha='right')
        ax.set_ylabel(num_col)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # 添加数值标签
        for bar, val in zip(bars, data.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(data.values)*0.01,
                   f'{val:.0f}', ha='center', va='bottom', fontsize=8)
    
    def _draw_horizontal_bar(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """水平柱状图"""
        cat_col = [c for c in columns if df[c].dtype == object or df[c].dtype.name == 'category'][0]
        num_col = [c for c in columns if np.issubdtype(df[c].dtype, np.number)][0]
        
        data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=True).head(15)
        colors = self.colors[:len(data)]
        ax.barh(range(len(data)), data.values, color=colors, edgecolor='white', linewidth=0.5)
        ax.set_yticks(range(len(data)))
        ax.set_yticklabels(data.index)
        ax.set_xlabel(num_col)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    def _draw_line(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """折线图"""
        dt_cols = [c for c in columns if 'datetime' in str(df[c].dtype)]
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        
        if dt_cols:
            x_col = dt_cols[0]
            df = df.sort_values(x_col)
            x = df[x_col]
        else:
            x = range(len(df))
        
        for i, num_col in enumerate(num_cols[:5]):  # 最多5条线
            ax.plot(x, df[num_col], color=self.colors[i], linewidth=2, label=num_col, marker='o', markersize=3)
        
        ax.legend(loc='best')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if dt_cols:
            ax.tick_params(axis='x', rotation=45)
    
    def _draw_area(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """面积图"""
        dt_cols = [c for c in columns if 'datetime' in str(df[c].dtype)]
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        
        if dt_cols:
            x_col = dt_cols[0]
            df = df.sort_values(x_col)
            x = df[x_col]
        else:
            x = range(len(df))
        
        for i, num_col in enumerate(num_cols[:3]):
            ax.fill_between(x, 0, df[num_col], alpha=0.3, color=self.colors[i], label=num_col)
            ax.plot(x, df[num_col], color=self.colors[i], linewidth=1.5)
        
        ax.legend(loc='best')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    def _draw_pie(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """饼图"""
        cat_col = [c for c in columns if df[c].dtype == object or df[c].dtype.name == 'category'][0]
        num_col = [c for c in columns if np.issubdtype(df[c].dtype, np.number)][0]
        
        data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(8)
        colors = self.colors[:len(data)]
        
        wedges, texts, autotexts = ax.pie(data.values, labels=data.index, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        for text in texts:
            text.set_fontsize(9)
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color('white')
            autotext.set_fontweight('bold')
    
    def _draw_scatter(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """散点图"""
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        if len(num_cols) >= 2:
            x_col, y_col = num_cols[0], num_cols[1]
            z_col = num_cols[2] if len(num_cols) > 2 else None
            
            sizes = df[z_col] * 50 / df[z_col].max() if z_col else 50
            ax.scatter(df[x_col], df[y_col], s=sizes, alpha=0.6, c=self.colors[0], edgecolors='white', linewidth=0.5)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
    
    def _draw_histogram(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """直方图"""
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        for i, col in enumerate(num_cols[:3]):
            ax.hist(df[col].dropna(), bins=30, alpha=0.6, color=self.colors[i], label=col, edgecolor='white')
        ax.legend()
        ax.set_xlabel('Value')
        ax.set_ylabel('Frequency')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    def _draw_box(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """箱线图"""
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        data_to_plot = [df[col].dropna() for col in num_cols[:8]]
        bp = ax.boxplot(data_to_plot, labels=num_cols[:8], patch_artist=True)
        for patch, color in zip(bp['boxes'], self.colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax.set_ylabel('Value')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    def _draw_heatmap(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """热力图"""
        if len(columns) >= 3:
            pivot = df.pivot_table(values=columns[2], index=columns[0], columns=columns[1], aggfunc='mean')
        else:
            pivot = df.corr(numeric_only=True)
        
        im = ax.imshow(pivot.values, cmap='YlOrRd', aspect='auto')
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_yticks(range(len(pivot.index)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha='right')
        ax.set_yticklabels(pivot.index)
        plt.colorbar(im, ax=ax)
    
    def _draw_grouped_bar(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """分组柱状图"""
        cat_cols = [c for c in columns if df[c].dtype == object or df[c].dtype.name == 'category']
        num_col = [c for c in columns if np.issubdtype(df[c].dtype, np.number)][0]
        
        if len(cat_cols) >= 2:
            pivot = df.groupby(cat_cols[:2])[num_col].sum().unstack()
            pivot.plot(kind='bar', ax=ax, color=self.colors[:len(pivot.columns)], edgecolor='white')
            ax.legend(title=cat_cols[1], bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    def _draw_corr_matrix(self, df: pd.DataFrame, columns: List[str], ax, **kwargs):
        """相关性矩阵"""
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) >= 2:
            corr = numeric_df.corr()
            im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
            ax.set_xticks(range(len(corr.columns)))
            ax.set_yticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha='right')
            ax.set_yticklabels(corr.columns)
            
            # 添加数值标注
            for i in range(len(corr.columns)):
                for j in range(len(corr.columns)):
                    ax.text(j, i, f'{corr.iloc[i, j]:.2f}', ha='center', va='center',
                           color='white' if abs(corr.iloc[i, j]) > 0.5 else 'black', fontsize=8)
            
            plt.colorbar(im, ax=ax)
