"""
ECharts 图表生成引擎 v2.0 — 集成时序智能体 + 描述智能体

特点：
- 时序图表自动检测日期列并由大模型建议聚合粒度（年/月/周/日）
- 每个图表的说明文字由大模型根据数据生成（而非规则模板）
- 生成 ECharts 配置（JSON/HTML）供 Streamlit 渲染
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import numpy as np

from pyecharts.charts import Bar, Line, Pie, Scatter, Boxplot, HeatMap, Radar, WordCloud, TreeMap
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
from pyecharts.globals import ThemeType

from src.visualization.recommender import ChartType
from src.config import VIZ_CONFIG
from src.analysis.timeseries_agent import TimeSeriesAgent, TimeSeriesConfig
from src.analysis.chart_describer_agent import ChartDescriberAgent, ChartDescription


@dataclass
class EChartOutput:
    """ECharts 图表输出"""
    chart_type: str
    title: str
    description: str      # 图表描述（由 LLM 生成）
    meaning: str            # 数据意义（由 LLM 生成）
    html: str               # pyecharts render_embed() 输出的 HTML
    config: Dict[str, Any]  # ECharts 配置 JSON
    columns_used: List[str]
    timeseries_config: Optional[TimeSeriesConfig] = None  # 时序配置（如有）


class EChartsEngine:
    """ECharts 图表生成引擎 v2.0"""
    
    COLORS = VIZ_CONFIG.get("color_palette", [
        "#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
        "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"
    ])
    
    def __init__(self, width: str = "800px", height: str = "450px", theme: str = ThemeType.LIGHT):
        self.width = width
        self.height = height
        self.theme = theme
        self.ts_agent = TimeSeriesAgent()
        self.desc_agent = ChartDescriberAgent()
    
    def generate(self, df: pd.DataFrame, chart_type: ChartType,
                 columns: List[str], title: str = None,
                 user_profile: Any = None, schema: Any = None,
                 source_name: str = "unknown", **kwargs) -> EChartOutput:
        """生成 ECharts 图表 + 智能描述"""
        
        # 时序图表：检测并聚合时间数据
        ts_config = None
        if chart_type in (ChartType.LINE, ChartType.AREA):
            ts_config = self.ts_agent.analyze(df, user_profile, schema, source_name)
            if ts_config and ts_config.agg_level != "raw":
                df = self.ts_agent.aggregate(df, ts_config)
                title = f"{title or chart_type.value}（按{ts_config.agg_level}聚合）"
        
        # 生成图表
        generators = {
            ChartType.BAR: self._gen_bar,
            ChartType.LINE: self._gen_line,
            ChartType.PIE: self._gen_pie,
            ChartType.SCATTER: self._gen_scatter,
            ChartType.HISTOGRAM: self._gen_histogram,
            ChartType.BOX: self._gen_boxplot,
            ChartType.HEATMAP: self._gen_heatmap,
            ChartType.AREA: self._gen_area,
            ChartType.HORIZONTAL_BAR: self._gen_horizontal_bar,
            ChartType.GROUPED_BAR: self._gen_grouped_bar,
            ChartType.CORR_MATRIX: self._gen_corr_matrix,
        }
        
        gen_fn = generators.get(chart_type, self._gen_bar)
        chart_obj, extra_data = gen_fn(df, columns, title, **kwargs)
        
        # 渲染 HTML
        html = chart_obj.render_embed()
        config = chart_obj.dump_options()
        
        # 用 LLM 生成描述
        chart_desc = self.desc_agent.describe(
            chart_type=chart_type.value,
            title=title or "图表",
            columns=columns,
            df=df,
            user_profile=user_profile,
            extra_data=extra_data,
        )
        
        return EChartOutput(
            chart_type=chart_type.value,
            title=title or "图表",
            description=chart_desc.description,
            meaning=chart_desc.meaning,
            html=html,
            config=config,
            columns_used=columns,
            timeseries_config=ts_config,
        )
    
    # ─────────────────── 柱状图 ───────────────────
    
    def _gen_bar(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        cat_col = [c for c in columns if df[c].dtype == object or df[c].dtype.name == 'category'][0]
        num_col = [c for c in columns if np.issubdtype(df[c].dtype, np.number)][0]
        
        data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(15)
        x_data = data.index.astype(str).tolist()
        y_data = data.values.tolist()
        
        chart = (
            Bar(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
            .add_xaxis(x_data)
            .add_yaxis(num_col, y_data, itemstyle_opts=opts.ItemStyleOpts(color=JsCode(
                """function(params) { return ['#5470c6','#91cc75','#fac858','#ee6666','#73c0de',
                '#3ba272','#fc8452','#9a60b4','#ea7ccc'][params.dataIndex % 9]; }"""
            )))
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title or f"{num_col} 按 {cat_col} 分布"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                datazoom_opts=[opts.DataZoomOpts()],
            )
        )
        
        extra = {
            "total": sum(y_data),
            "max_value": max(y_data) if y_data else 0,
            "top_category": x_data[0] if x_data else "N/A",
            "category_count": len(x_data),
        }
        return chart, extra
    
    # ─────────────────── 折线图 ───────────────────
    
    def _gen_line(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        dt_cols = [c for c in columns if 'datetime' in str(df[c].dtype)]
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        
        if dt_cols:
            x_col = dt_cols[0]
            df = df.sort_values(x_col)
            x_data = df[x_col].astype(str).tolist()
        else:
            x_data = df.index.astype(str).tolist()
        
        chart = Line(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
        chart.add_xaxis(x_data)
        
        for i, num_col in enumerate(num_cols[:5]):
            chart.add_yaxis(
                num_col, df[num_col].tolist(),
                is_smooth=True,
                linestyle_opts=opts.LineStyleOpts(width=3, color=self.COLORS[i]),
                itemstyle_opts=opts.ItemStyleOpts(color=self.COLORS[i]),
                areastyle_opts=opts.AreaStyleOpts(opacity=0.2, color=self.COLORS[i]) if i == 0 else None,
            )
        
        chart.set_global_opts(
            title_opts=opts.TitleOpts(title=title or f"{', '.join(num_cols[:3])} 趋势"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            datazoom_opts=[opts.DataZoomOpts()],
        )
        
        extra = {
            "time_points": len(x_data),
            "series_count": len(num_cols[:5]),
            "series_names": num_cols[:5],
        }
        return chart, extra
    
    # ─────────────────── 饼图 ───────────────────
    
    def _gen_pie(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        cat_col = [c for c in columns if df[c].dtype == object or df[c].dtype.name == 'category'][0]
        num_col = [c for c in columns if np.issubdtype(df[c].dtype, np.number)][0]
        
        data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(8)
        pie_data = [(str(k), float(v)) for k, v in data.items()]
        total = sum(v for _, v in pie_data)
        top_pct = pie_data[0][1] / total * 100 if pie_data else 0
        
        chart = (
            Pie(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
            .add(
                "", pie_data, radius=["40%", "75%"], center=["50%", "50%"],
                label_opts=opts.LabelOpts(formatter="{b}: {d}%"),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title or f"{num_col} 按 {cat_col} 占比"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="left"),
                tooltip_opts=opts.TooltipOpts(formatter="{b}: {c} ({d}%)"),
            )
            .set_series_opts(
                itemstyle_opts=opts.ItemStyleOpts(border_width=2, border_color="#fff")
            )
        )
        
        extra = {
            "total": total,
            "top_category": pie_data[0][0] if pie_data else "N/A",
            "top_percentage": top_pct,
            "category_count": len(pie_data),
        }
        return chart, extra
    
    # ─────────────────── 散点图 ───────────────────
    
    def _gen_scatter(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        if len(num_cols) >= 2:
            x_col, y_col = num_cols[0], num_cols[1]
        else:
            x_col, y_col = df.columns[0], df.columns[1]
        
        x_data = df[x_col].dropna().tolist()
        y_data = df[y_col].dropna().tolist()
        corr = df[x_col].corr(df[y_col]) if len(x_data) > 1 else 0
        
        scatter_data = [[float(x), float(y)] for x, y in zip(x_data, y_data)]
        
        chart = (
            Scatter(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
            .add_xaxis([x_col])
            .add_yaxis(y_col, scatter_data, symbol_size=10,
                       itemstyle_opts=opts.ItemStyleOpts(color=self.COLORS[0], opacity=0.7))
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title or f"{x_col} vs {y_col}"),
                xaxis_opts=opts.AxisOpts(name=x_col, type_="value"),
                yaxis_opts=opts.AxisOpts(name=y_col, type_="value"),
            )
        )
        
        extra = {
            "correlation": corr,
            "point_count": len(scatter_data),
            "x_col": x_col, "y_col": y_col,
        }
        return chart, extra
    
    # ─────────────────── 直方图 ───────────────────
    
    def _gen_histogram(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        col = num_cols[0] if num_cols else columns[0]
        
        data = df[col].dropna()
        mean_val = data.mean()
        median_val = data.median()
        std_val = data.std()
        
        counts, bins = np.histogram(data, bins=30)
        x_data = [f"{bins[i]:.1f}-{bins[i+1]:.1f}" for i in range(len(bins)-1)]
        
        chart = (
            Bar(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
            .add_xaxis(x_data)
            .add_yaxis("频数", counts.tolist(),
                       itemstyle_opts=opts.ItemStyleOpts(color=self.COLORS[0]), bar_width="99%")
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title or f"{col} 分布直方图"),
                xaxis_opts=opts.AxisOpts(name=col, axislabel_opts=opts.LabelOpts(rotate=45)),
                yaxis_opts=opts.AxisOpts(name="频数"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
            )
        )
        
        extra = {
            "mean": mean_val, "median": median_val, "std": std_val,
            "sample_count": len(data), "skewness": "right" if mean_val > median_val * 1.1 else "left" if mean_val < median_val * 0.9 else "symmetric",
        }
        return chart, extra
    
    # ─────────────────── 箱线图 ───────────────────
    
    def _gen_boxplot(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        num_cols = num_cols[:8]
        
        box_data = []
        for col in num_cols:
            data = df[col].dropna()
            q1, q2, q3 = data.quantile([0.25, 0.5, 0.75])
            min_v, max_v = data.min(), data.max()
            box_data.append([round(min_v, 2), round(q1, 2), round(q2, 2), round(q3, 2), round(max_v, 2)])
        
        chart = (
            Boxplot(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
            .add_xaxis(num_cols)
            .add_yaxis("数值", box_data)
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title or "数值字段箱线图"),
                tooltip_opts=opts.TooltipOpts(trigger="item"),
            )
        )
        
        max_range = 0
        max_col = num_cols[0] if num_cols else "N/A"
        for col in num_cols:
            data = df[col].dropna()
            rng = data.max() - data.min()
            if rng > max_range:
                max_range = rng
                max_col = col
        
        extra = {"field_count": len(num_cols), "most_variable": max_col, "max_range": max_range}
        return chart, extra
    
    # ─────────────────── 热力图 ───────────────────
    
    def _gen_heatmap(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        if len(columns) >= 3:
            pivot = df.pivot_table(values=columns[2], index=columns[0], columns=columns[1], aggfunc='mean')
        else:
            pivot = df.select_dtypes(include=[np.number]).corr()
        
        y_data = pivot.index.astype(str).tolist()
        x_data = pivot.columns.astype(str).tolist()
        heat_data = []
        for i, row in enumerate(pivot.values):
            for j, val in enumerate(row):
                heat_data.append([j, i, round(float(val), 2)])
        
        chart = (
            HeatMap(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
            .add_xaxis(x_data)
            .add_yaxis("", y_data, heat_data, label_opts=opts.LabelOpts(is_show=True, position="inside"))
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title or "热力图"),
                visualmap_opts=opts.VisualMapOpts(
                    min_=float(pivot.values.min()), max_=float(pivot.values.max()),
                    orient="horizontal", pos_left="center", pos_bottom="5%",
                ),
            )
        )
        
        extra = {"is_correlation": len(columns) < 3, "rows": len(y_data), "cols": len(x_data)}
        return chart, extra
    
    # ─────────────────── 面积图 ───────────────────
    
    def _gen_area(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        dt_cols = [c for c in columns if 'datetime' in str(df[c].dtype)]
        num_cols = [c for c in columns if np.issubdtype(df[c].dtype, np.number)]
        
        if dt_cols:
            x_col = dt_cols[0]
            df = df.sort_values(x_col)
            x_data = df[x_col].astype(str).tolist()
        else:
            x_data = df.index.astype(str).tolist()
        
        chart = Line(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
        chart.add_xaxis(x_data)
        
        for i, num_col in enumerate(num_cols[:3]):
            chart.add_yaxis(
                num_col, df[num_col].tolist(), is_smooth=True,
                areastyle_opts=opts.AreaStyleOpts(opacity=0.4, color=self.COLORS[i]),
                linestyle_opts=opts.LineStyleOpts(width=2, color=self.COLORS[i]),
            )
        
        chart.set_global_opts(
            title_opts=opts.TitleOpts(title=title or f"{', '.join(num_cols[:3])} 面积趋势"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            datazoom_opts=[opts.DataZoomOpts()],
        )
        
        total_area = sum(df[num_cols[0]].dropna().sum() for c in num_cols[:3] if c in df.columns)
        extra = {"total": total_area, "series_count": len(num_cols[:3])}
        return chart, extra
    
    # ─────────────────── 水平柱状图 ───────────────────
    
    def _gen_horizontal_bar(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        cat_col = [c for c in columns if df[c].dtype == object or df[c].dtype.name == 'category'][0]
        num_col = [c for c in columns if np.issubdtype(df[c].dtype, np.number)][0]
        
        data = df.groupby(cat_col)[num_col].sum().sort_values(ascending=True).head(15)
        y_data = data.index.astype(str).tolist()
        x_data = data.values.tolist()
        
        chart = (
            Bar(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
            .add_xaxis(y_data)
            .add_yaxis(num_col, x_data, itemstyle_opts=opts.ItemStyleOpts(color=self.COLORS[0]))
            .reversal_axis()
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title or f"{num_col} 按 {cat_col} 排名"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                datazoom_opts=[opts.DataZoomOpts(orient="vertical")],
            )
            .set_series_opts(label_opts=opts.LabelOpts(position="right"))
        )
        
        extra = {
            "total": sum(x_data), "top_value": max(x_data) if x_data else 0,
            "top_category": y_data[-1] if y_data else "N/A", "category_count": len(y_data),
        }
        return chart, extra
    
    # ─────────────────── 分组柱状图 ───────────────────
    
    def _gen_grouped_bar(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        cat_cols = [c for c in columns if df[c].dtype == object or df[c].dtype.name == 'category']
        num_col = [c for c in columns if np.issubdtype(df[c].dtype, np.number)][0]
        
        if len(cat_cols) >= 2:
            pivot = df.groupby(cat_cols[:2])[num_col].sum().unstack()
            x_data = pivot.index.astype(str).tolist()
            
            chart = Bar(init_opts=opts.InitOpts(width=self.width, height=self.height, theme=self.theme))
            chart.add_xaxis(x_data)
            
            for i, sub_col in enumerate(pivot.columns):
                chart.add_yaxis(str(sub_col), pivot[sub_col].tolist(),
                                itemstyle_opts=opts.ItemStyleOpts(color=self.COLORS[i % len(self.COLORS)]))
            
            chart.set_global_opts(
                title_opts=opts.TitleOpts(title=title or f"{num_col} 按 {cat_cols[0]} 和 {cat_cols[1]}"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                legend_opts=opts.LegendOpts(pos_top="5%"),
                datazoom_opts=[opts.DataZoomOpts()],
            )
            
            extra = {"sub_categories": [str(c) for c in pivot.columns], "main_category": cat_cols[0]}
        else:
            return self._gen_bar(df, columns, title, **kwargs)
        
        return chart, extra
    
    # ─────────────────── 相关性矩阵 ───────────────────
    
    def _gen_corr_matrix(self, df: pd.DataFrame, columns: List[str], title: str, **kwargs) -> Tuple[Any, Dict]:
        numeric_df = df.select_dtypes(include=[np.number])
        corr = numeric_df.corr()
        
        cols = corr.columns.tolist()
        n = len(cols)
        
        heat_data = []
        for i in range(n):
            for j in range(n):
                heat_data.append([j, i, round(corr.iloc[i, j], 2)])
        
        chart = (
            HeatMap(init_opts=opts.InitOpts(width=f"{max(400, n*80)}px", height=f"{max(400, n*80)}px", theme=self.theme))
            .add_xaxis(cols)
            .add_yaxis("", cols, heat_data, label_opts=opts.LabelOpts(is_show=True))
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title or "相关性矩阵"),
                visualmap_opts=opts.VisualMapOpts(min_=-1, max_=1, orient="horizontal", pos_left="center"),
            )
        )
        
        max_corr = 0
        max_pair = (cols[0], cols[1]) if n >= 2 else (cols[0], cols[0])
        for i in range(n):
            for j in range(i+1, n):
                c = abs(corr.iloc[i, j])
                if c > max_corr:
                    max_corr = c
                    max_pair = (cols[i], cols[j])
        
        extra = {"field_count": n, "strongest_pair": max_pair, "strongest_corr": max_corr}
        return chart, extra


__all__ = ["EChartsEngine", "EChartOutput"]
