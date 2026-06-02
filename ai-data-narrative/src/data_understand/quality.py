"""
数据质量检查器 — 缺失值、异常值、重复值检测
"""

from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np


class QualityChecker:
    """数据质量检查器"""
    
    @classmethod
    def check_all(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        执行全部质量检查
        
        Returns:
            {
                "overall_score": float,  # 0-1
                "issues": List[dict],
                "summary": dict
            }
        """
        issues = []
        
        # 检查缺失值
        missing_issues = cls.check_missing(df)
        issues.extend(missing_issues)
        
        # 检查异常值
        outlier_issues = cls.check_outliers(df)
        issues.extend(outlier_issues)
        
        # 检查重复值
        dup_issues = cls.check_duplicates(df)
        issues.extend(dup_issues)
        
        # 检查常量列
        const_issues = cls.check_constant_columns(df)
        issues.extend(const_issues)
        
        # 计算综合得分
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isna().sum().sum()
        duplicate_rows = df.duplicated().sum()
        outlier_cells = sum(issue.get("count", 0) for issue in outlier_issues)
        
        good_cells = total_cells - missing_cells - outlier_cells
        overall_score = max(0, good_cells / total_cells) if total_cells > 0 else 1.0
        
        # 重复行惩罚
        if len(df) > 0:
            dup_penalty = duplicate_rows / len(df) * 0.2
            overall_score -= dup_penalty
        
        overall_score = max(0, min(1, overall_score))
        
        return {
            "overall_score": round(overall_score, 3),
            "grade": cls._score_to_grade(overall_score),
            "issues": issues,
            "summary": {
                "total_cells": int(total_cells),
                "missing_cells": int(missing_cells),
                "duplicate_rows": int(duplicate_rows),
                "outlier_cells": int(outlier_cells),
                "issue_count": len(issues)
            }
        }
    
    @staticmethod
    def _score_to_grade(score: float) -> str:
        """分数转等级"""
        if score >= 0.95:
            return "A+"
        elif score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    @staticmethod
    def check_missing(df: pd.DataFrame) -> List[Dict]:
        """检查缺失值"""
        issues = []
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_ratio = missing_count / len(df) if len(df) > 0 else 0
            
            if missing_count > 0:
                severity = "critical" if missing_ratio > 0.5 else "warning" if missing_ratio > 0.1 else "info"
                issues.append({
                    "type": "missing_values",
                    "column": col,
                    "count": int(missing_count),
                    "ratio": round(missing_ratio, 3),
                    "severity": severity,
                    "suggestion": f"列 '{col}' 有 {missing_count} 个缺失值 ({missing_ratio:.1%})，建议填充或删除"
                })
        return issues
    
    @staticmethod
    def check_outliers(df: pd.DataFrame, method: str = "iqr", threshold: float = 1.5) -> List[Dict]:
        """
        检查数值型异常值
        
        Args:
            method: "iqr" 或 "zscore"
            threshold: IQR 倍数或 Z-score 阈值
        """
        issues = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            if method == "iqr":
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                lower = q1 - threshold * iqr
                upper = q3 + threshold * iqr
                outlier_mask = (series < lower) | (series > upper)
            elif method == "zscore":
                mean = series.mean()
                std = series.std()
                if std == 0:
                    continue
                z_scores = (series - mean).abs() / std
                outlier_mask = z_scores > threshold
            else:
                continue
            
            outlier_count = outlier_mask.sum()
            if outlier_count > 0:
                outlier_values = series[outlier_mask].tolist()
                issues.append({
                    "type": "outliers",
                    "column": col,
                    "count": int(outlier_count),
                    "ratio": round(outlier_count / len(series), 3),
                    "severity": "warning" if outlier_count / len(series) > 0.05 else "info",
                    "suggestion": f"列 '{col}' 发现 {outlier_count} 个异常值，建议检查数据录入或考虑对数变换",
                    "sample_values": outlier_values[:5]
                })
        
        return issues
    
    @staticmethod
    def check_duplicates(df: pd.DataFrame) -> List[Dict]:
        """检查重复行"""
        issues = []
        dup_count = df.duplicated().sum()
        
        if dup_count > 0:
            issues.append({
                "type": "duplicate_rows",
                "column": "all",
                "count": int(dup_count),
                "ratio": round(dup_count / len(df), 3) if len(df) > 0 else 0,
                "severity": "warning" if dup_count / len(df) > 0.1 else "info",
                "suggestion": f"发现 {dup_count} 行完全重复数据，建议去重"
            })
        
        return issues
    
    @staticmethod
    def check_constant_columns(df: pd.DataFrame) -> List[Dict]:
        """检查常量列（所有值相同）"""
        issues = []
        for col in df.columns:
            if df[col].nunique() <= 1:
                issues.append({
                    "type": "constant_column",
                    "column": col,
                    "count": len(df),
                    "severity": "info",
                    "suggestion": f"列 '{col}' 为常量列，对分析无贡献，建议删除"
                })
        return issues
