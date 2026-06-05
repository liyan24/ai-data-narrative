"""
时序智能体 — 检测时间列并建议聚合粒度

当数据中包含时间维度时，由大模型决定最佳聚合方式（年/月/周/日/小时），
使时序图表能清晰展示趋势。
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

from src.llm_client import LLMClient, get_llm_client


@dataclass
class TimeSeriesConfig:
    """时序分析配置"""
    time_column: str          # 时间列名称
    date_format: str          # 原始日期格式
    agg_level: str            # 聚合粒度: year / month / week / day / hour / raw
    group_columns: List[str]  # 额外的分组列（如地区、品类）
    value_columns: List[str]  # 需要聚合的数值列
    explanation: str          # LLM 对选择原因的解释


_DEFAULT_TIMESERIES_PROMPT = """你是数据时序分析专家。

【数据概况】
数据集: {source_name}
总行数: {row_count}
时间范围: {time_range}

【时间列信息】
列名: {time_column}
时间粒度: {granularity}（系统自动检测: 日/周/月/小时/秒级）
唯一时间点数: {unique_count}

【其他字段】
数值列: {numeric_cols}
分类列: {categorical_cols}

【用户意图】
{user_goal}

请分析最佳时间聚合粒度，要求：
1. 考虑数据量：时间点多时聚合到更大粒度避免图表拥挤
2. 考虑用户意图：分析"月度趋势"就聚合到月，"年度对比"就聚合到年
3. 考虑业务场景：零售数据一般按月/周，日志数据按小时/天

输出 JSON：
{{
    "agg_level": "year|month|week|day|hour|raw",
    "group_by": ["category_column_1"],
    "aggregate": {{"sales": "sum", "orders": "sum", "rating": "mean"}},
    "explanation": "选择month，因为数据跨3年，按日显示600+点太拥挤；用户关注销售趋势，月度粒度最适合。"
}}
"""


class TimeSeriesAgent:
    """时序智能体 — 检测时间列并建议聚合策略"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()
    
    def detect_time_column(self, df: pd.DataFrame, schema: Any = None) -> Optional[str]:
        """检测时间列"""
        # 1. 根据 schema 角色检测
        if schema and hasattr(schema, 'fields'):
            for f in schema.fields:
                if getattr(f, 'role', None) == 'time_axis':
                    return f.name
        
        # 2. 根据列名猜测
        time_keywords = ['date', 'time', 'datetime', 'timestamp', 'period', '月份', '日期', '时间', '年月', '年', '月', '日']
        for col in df.columns:
            col_lower = str(col).lower()
            if any(k in col_lower for k in time_keywords):
                return col
        
        # 3. 根据 dtype 检测
        for col in df.columns:
            dtype = str(df[col].dtype)
            if 'datetime' in dtype:
                return col
            # 尝试解析字符串为日期
            try:
                pd.to_datetime(df[col].dropna().iloc[:5])
                return col
            except:
                pass
        
        return None
    
    def detect_granularity(self, series: pd.Series) -> Tuple[str, int]:
        """检测时间粒度
        
        Returns:
            (granularity_label, unique_count)
        """
        try:
            dt = pd.to_datetime(series.dropna())
        except:
            return "unknown", 0
        
        unique_count = dt.nunique()
        
        if unique_count == 0:
            return "unknown", 0
        
        # 计算平均间隔
        sorted_dt = dt.sort_values()
        if len(sorted_dt) > 1:
            avg_gap = (sorted_dt.iloc[-1] - sorted_dt.iloc[0]).total_seconds() / (unique_count - 1)
        else:
            avg_gap = float('inf')
        
        # 判断粒度
        if avg_gap < 60:
            return "second", unique_count
        elif avg_gap < 3600:
            return "minute", unique_count
        elif avg_gap < 86400:
            return "hour", unique_count
        elif avg_gap < 604800:
            return "day", unique_count
        elif avg_gap < 2592000:
            return "week", unique_count
        elif avg_gap < 31536000:
            return "month", unique_count
        else:
            return "year", unique_count
    
    def analyze(self, df: pd.DataFrame, 
                user_profile: Any = None,
                schema: Any = None,
                source_name: str = "unknown") -> Optional[TimeSeriesConfig]:
        """
        分析时序数据并建议聚合策略
        
        如果无时间列或 LLM 不可用，返回 None（使用原始数据）
        """
        time_col = self.detect_time_column(df, schema)
        if not time_col:
            return None
        
        # 确保时间列是 datetime
        try:
            df[time_col] = pd.to_datetime(df[time_col])
        except:
            return None
        
        granularity, unique_count = self.detect_granularity(df[time_col])
        time_range = f"{df[time_col].min()} ~ {df[time_col].max()}"
        
        # 数值列和分类列
        numeric_cols = [c for c in df.columns 
                        if np.issubdtype(df[c].dtype, np.number) and c != time_col]
        categorical_cols = [c for c in df.columns 
                            if df[c].dtype == object and c != time_col]
        
        # LLM 分析
        user_goal = ""
        if user_profile and hasattr(user_profile, 'goal'):
            user_goal = user_profile.goal or ""
        
        if self.llm and self.llm.api_key:
            try:
                prompt = _DEFAULT_TIMESERIES_PROMPT.format(
                    source_name=source_name,
                    row_count=len(df),
                    time_range=time_range,
                    time_column=time_col,
                    granularity=granularity,
                    unique_count=unique_count,
                    numeric_cols=", ".join(numeric_cols[:5]) or "无",
                    categorical_cols=", ".join(categorical_cols[:5]) or "无",
                    user_goal=user_goal or "未指定",
                )
                
                response = self.llm.chat([
                    {"role": "system", "content": "你是数据时序分析专家。请严格输出 JSON。"},
                    {"role": "user", "content": prompt}
                ], temperature=0.3)
                
                data = self._extract_json(response)
                
                return TimeSeriesConfig(
                    time_column=time_col,
                    date_format=granularity,
                    agg_level=data.get("agg_level", "raw"),
                    group_columns=data.get("group_by", []),
                    value_columns=numeric_cols,
                    explanation=data.get("explanation", ""),
                )
            except Exception as e:
                # LLM 失败，使用规则推断
                pass
        
        # 规则推断（LLM 不可用或失败）
        agg_level = self._rule_based_agg(granularity, unique_count, len(df))
        
        return TimeSeriesConfig(
            time_column=time_col,
            date_format=granularity,
            agg_level=agg_level,
            group_columns=categorical_cols[:2],
            value_columns=numeric_cols[:3],
            explanation=f"规则推断: 检测到{granularity}粒度，共{unique_count}个时间点，按{agg_level}聚合",
        )
    
    def _rule_based_agg(self, granularity: str, unique_count: int, total_rows: int) -> str:
        """基于规则的聚合粒度推断"""
        # 点数太多就聚合，太少保持原样
        if granularity == "second" or unique_count > 500:
            return "day" if total_rows > 1000 else "hour"
        elif granularity == "minute" and unique_count > 200:
            return "hour"
        elif granularity == "hour" and unique_count > 200:
            return "day"
        elif granularity == "day" and unique_count > 300:
            return "month"
        elif granularity == "week" and unique_count > 100:
            return "month"
        elif granularity == "month" and unique_count > 60:
            return "year"
        else:
            return "raw"  # 不聚合
    
    def aggregate(self, df: pd.DataFrame, config: TimeSeriesConfig) -> pd.DataFrame:
        """按配置聚合数据"""
        if config.agg_level == "raw" or not config.time_column:
            return df
        
        time_col = config.time_column
        df = df.copy()
        df[time_col] = pd.to_datetime(df[time_col])
        
        # 提取聚合维度
        if config.agg_level == "year":
            df["_agg_period"] = df[time_col].dt.to_period("Y").astype(str)
        elif config.agg_level == "month":
            df["_agg_period"] = df[time_col].dt.to_period("M").astype(str)
        elif config.agg_level == "week":
            df["_agg_period"] = df[time_col].dt.to_period("W").astype(str)
        elif config.agg_level == "day":
            df["_agg_period"] = df[time_col].dt.to_period("D").astype(str)
        elif config.agg_level == "hour":
            df["_agg_period"] = df[time_col].dt.to_period("h").astype(str)
        else:
            return df
        
        # 聚合数值列
        agg_dict = {c: "sum" if c in config.value_columns else "first" for c in df.columns 
                    if c not in [time_col, "_agg_period"] + config.group_columns}
        for c in config.group_columns:
            agg_dict[c] = "first"
        
        # 只保留数值列的聚合
        numeric_agg = {c: "sum" for c in config.value_columns if c in df.columns}
        for c in config.group_columns:
            if c in df.columns:
                numeric_agg[c] = "first"
        
        grouped = df.groupby(["_agg_period"] + config.group_columns).agg(numeric_agg).reset_index()
        grouped = grouped.rename(columns={"_agg_period": time_col})
        
        return grouped
    
    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())


__all__ = ["TimeSeriesAgent", "TimeSeriesConfig"]
