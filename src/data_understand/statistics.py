"""
数据统计特征提取器
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
from scipy import stats


class StatisticExtractor:
    """统计特征提取器"""
    
    @classmethod
    def extract_all(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """提取所有统计特征"""
        return {
            "basic": cls.extract_basic(df),
            "numeric": cls.extract_numeric(df),
            "categorical": cls.extract_categorical(df),
            "datetime": cls.extract_datetime(df),
            "correlations": cls.extract_correlations(df)
        }
    
    @staticmethod
    def extract_basic(df: pd.DataFrame) -> Dict[str, Any]:
        """基础统计信息"""
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "density": round((1 - df.isna().sum().sum() / (df.shape[0] * df.shape[1])) * 100, 2)
        }
    
    @staticmethod
    def extract_numeric(df: pd.DataFrame) -> Dict[str, Dict]:
        """数值列统计特征"""
        numeric_df = df.select_dtypes(include=[np.number])
        result = {}
        
        for col in numeric_df.columns:
            series = numeric_df[col].dropna()
            if len(series) == 0:
                continue
            
            result[col] = {
                "count": int(len(series)),
                "mean": round(float(series.mean()), 4),
                "median": round(float(series.median()), 4),
                "std": round(float(series.std()), 4),
                "min": round(float(series.min()), 4),
                "max": round(float(series.max()), 4),
                "q25": round(float(series.quantile(0.25)), 4),
                "q75": round(float(series.quantile(0.75)), 4),
                "skewness": round(float(series.skew()), 4),
                "kurtosis": round(float(series.kurtosis()), 4),
                "missing": int(df[col].isna().sum())
            }
        
        return result
    
    @staticmethod
    def extract_categorical(df: pd.DataFrame) -> Dict[str, Dict]:
        """类别列统计特征"""
        cat_df = df.select_dtypes(include=['object', 'category'])
        result = {}
        
        for col in cat_df.columns:
            series = cat_df[col]
            value_counts = series.value_counts()
            
            result[col] = {
                "unique_count": int(series.nunique()),
                "most_frequent": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                "most_frequent_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                "top_values": {
                    str(k): int(v) 
                    for k, v in value_counts.head(5).to_dict().items()
                },
                "missing": int(series.isna().sum())
            }
        
        return result
    
    @staticmethod
    def extract_datetime(df: pd.DataFrame) -> Dict[str, Dict]:
        """日期列统计特征"""
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        result = {}
        
        for col in datetime_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            result[col] = {
                "earliest": str(series.min()),
                "latest": str(series.max()),
                "span_days": int((series.max() - series.min()).days),
                "missing": int(df[col].isna().sum())
            }
        
        return result
    
    @staticmethod
    def extract_correlations(df: pd.DataFrame) -> Dict[str, Any]:
        """提取相关性矩阵"""
        numeric_df = df.select_dtypes(include=[np.number])
        
        if len(numeric_df.columns) < 2:
            return {"available": False, "reason": "数值列不足 2 个"}
        
        corr_matrix = numeric_df.corr().round(3)
        
        # 找出强相关对
        strong_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                col1 = corr_matrix.columns[i]
                col2 = corr_matrix.columns[j]
                corr_val = corr_matrix.iloc[i, j]
                
                if abs(corr_val) > 0.7:
                    strong_pairs.append({
                        "col1": col1,
                        "col2": col2,
                        "correlation": corr_val,
                        "strength": "strong" if abs(corr_val) > 0.9 else "moderate"
                    })
        
        return {
            "available": True,
            "matrix": corr_matrix.to_dict(),
            "strong_pairs": strong_pairs,
            "pair_count": len(strong_pairs)
        }
