"""
数据清洗引擎 — 自动检测问题并提供清洗建议

核心能力：
- 缺失值处理：删除/填充/插值策略
- 异常值处理：截断/替换/删除
- 重复值处理：去重策略
- 格式标准化：统一编码、日期格式
- 类型转换：安全类型转换
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats


class CleanAction(Enum):
    """清洗动作"""
    DROP_ROWS = "drop_rows"           # 删除行
    DROP_COLS = "drop_cols"           # 删除列
    FILL_MEAN = "fill_mean"           # 均值填充
    FILL_MEDIAN = "fill_median"       # 中位数填充
    FILL_MODE = "fill_mode"           # 众数填充
    FILL_CONST = "fill_const"         # 常量填充
    INTERPOLATE = "interpolate"       # 插值
    CLIP = "clip"                     # 截断
    REMOVE_DUPLICATES = "remove_duplicates"  # 去重
    CONVERT_TYPE = "convert_type"     # 类型转换


@dataclass
class CleanSuggestion:
    """清洗建议"""
    column: str
    issue: str
    action: CleanAction
    description: str
    before_count: int
    after_count: int
    preview: Any = None
    params: Dict = None


class DataCleaner:
    """数据清洗器"""
    
    def __init__(self, df: pd.DataFrame):
        self.original_df = df.copy()
        self.df = df.copy()
        self.suggestions: List[CleanSuggestion] = []
        self.log: List[str] = []
    
    def auto_clean(self, aggressive: bool = False) -> pd.DataFrame:
        """
        自动清洗数据
        
        Args:
            aggressive: 是否激进清洗（删除更多数据）
            
        Returns:
            清洗后的 DataFrame
        """
        self.suggestions = []
        self.df = self.original_df.copy()
        
        # 1. 处理重复行
        self._handle_duplicates()
        
        # 2. 处理缺失值
        self._handle_missing(aggressive)
        
        # 3. 处理异常值
        self._handle_outliers(aggressive)
        
        # 4. 类型标准化
        self._standardize_types()
        
        return self.df
    
    def _handle_duplicates(self):
        """处理重复行"""
        dup_count = self.df.duplicated().sum()
        if dup_count > 0:
            self.df = self.df.drop_duplicates()
            self.suggestions.append(CleanSuggestion(
                column="*",
                issue="duplicate_rows",
                action=CleanAction.REMOVE_DUPLICATES,
                description=f"删除 {dup_count} 行完全重复的数据",
                before_count=dup_count,
                after_count=0,
                preview=None
            ))
            self.log.append(f"[去重] 删除 {dup_count} 行重复数据")
    
    def _handle_missing(self, aggressive: bool):
        """处理缺失值"""
        missing = self.df.isnull().sum()
        missing_cols = missing[missing > 0].index.tolist()
        
        for col in missing_cols:
            missing_count = missing[col]
            missing_pct = missing_count / len(self.df)
            
            if missing_pct > 0.5 and aggressive:
                # 缺失过半，删除列
                self.df = self.df.drop(columns=[col])
                self.suggestions.append(CleanSuggestion(
                    column=col,
                    issue="high_missing",
                    action=CleanAction.DROP_COLS,
                    description=f"{col} 缺失率 {missing_pct:.1%}，超过50%，删除该列",
                    before_count=missing_count,
                    after_count=0,
                    preview=None
                ))
                self.log.append(f"[缺失值] {col} 缺失率 {missing_pct:.1%}，删除列")
            
            elif missing_pct > 0.3 and not aggressive:
                # 缺失较多，删除行
                self.df = self.df.dropna(subset=[col])
                self.suggestions.append(CleanSuggestion(
                    column=col,
                    issue="high_missing",
                    action=CleanAction.DROP_ROWS,
                    description=f"{col} 缺失率 {missing_pct:.1%}，删除缺失行",
                    before_count=missing_count,
                    after_count=0,
                    preview=None
                ))
                self.log.append(f"[缺失值] {col} 缺失率 {missing_pct:.1%}，删除缺失行")
            
            else:
                # 填充策略
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    # 数值型：中位数填充
                    fill_value = self.df[col].median()
                    self.df[col] = self.df[col].fillna(fill_value)
                    action = CleanAction.FILL_MEDIAN
                    desc = f"{col} 使用中位数 {fill_value:.2f} 填充 {missing_count} 个缺失值"
                else:
                    # 类别型：众数填充
                    fill_value = self.df[col].mode().iloc[0] if len(self.df[col].mode()) > 0 else "未知"
                    self.df[col] = self.df[col].fillna(fill_value)
                    action = CleanAction.FILL_MODE
                    desc = f"{col} 使用众数 '{fill_value}' 填充 {missing_count} 个缺失值"
                
                self.suggestions.append(CleanSuggestion(
                    column=col,
                    issue="missing_values",
                    action=action,
                    description=desc,
                    before_count=missing_count,
                    after_count=0,
                    preview=fill_value,
                    params={"fill_value": fill_value}
                ))
                self.log.append(f"[缺失值] {desc}")
    
    def _handle_outliers(self, aggressive: bool):
        """处理异常值"""
        num_cols = self.df.select_dtypes(include=[np.number]).columns
        
        for col in num_cols:
            series = self.df[col].dropna()
            if len(series) < 10:
                continue
            
            # IQR 方法
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            
            outliers = self.df[(self.df[col] < lower) | (self.df[col] > upper)]
            outlier_count = len(outliers)
            
            if outlier_count > 0:
                if aggressive:
                    # 激进模式：删除异常行
                    self.df = self.df[(self.df[col] >= lower) | (self.df[col].isna())]
                    self.df = self.df[(self.df[col] <= upper) | (self.df[col].isna())]
                    action = CleanAction.DROP_ROWS
                    desc = f"{col} 删除 {outlier_count} 个异常值（IQR 法）"
                else:
                    # 保守模式：截断到边界
                    self.df[col] = self.df[col].clip(lower, upper)
                    action = CleanAction.CLIP
                    desc = f"{col} 截断 {outlier_count} 个异常值到边界 [{lower:.2f}, {upper:.2f}]"
                
                self.suggestions.append(CleanSuggestion(
                    column=col,
                    issue="outliers",
                    action=action,
                    description=desc,
                    before_count=outlier_count,
                    after_count=0,
                    preview={"lower": lower, "upper": upper}
                ))
                self.log.append(f"[异常值] {desc}")
    
    def _standardize_types(self):
        """标准化数据类型"""
        for col in self.df.columns:
            # 尝试将字符串日期转换为 datetime
            if self.df[col].dtype == object:
                try:
                    sample = self.df[col].dropna().head(10)
                    # 检查是否是日期格式
                    if sample.astype(str).str.match(r'\d{4}-\d{2}-\d{2}').any():
                        self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
                        self.suggestions.append(CleanSuggestion(
                            column=col,
                            issue="type_conversion",
                            action=CleanAction.CONVERT_TYPE,
                            description=f"{col} 自动转换为 datetime 类型",
                            before_count=0,
                            after_count=0
                        ))
                        self.log.append(f"[类型转换] {col} -> datetime")
                except Exception:
                    pass
    
    def get_cleaning_report(self) -> Dict[str, Any]:
        """获取清洗报告"""
        return {
            "original_shape": self.original_df.shape,
            "cleaned_shape": self.df.shape,
            "rows_removed": self.original_df.shape[0] - self.df.shape[0],
            "cols_removed": self.original_df.shape[1] - self.df.shape[1],
            "suggestions_count": len(self.suggestions),
            "suggestions": [
                {
                    "column": s.column,
                    "issue": s.issue,
                    "action": s.action.value,
                    "description": s.description,
                }
                for s in self.suggestions
            ],
            "log": self.log
        }
    
    def get_cleaned_data(self) -> pd.DataFrame:
        """获取清洗后的数据"""
        return self.df.copy()
