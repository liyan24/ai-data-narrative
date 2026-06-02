"""
高级分析引擎 — 机器学习异常检测、预测、聚类

基于 scikit-learn 的高级分析能力，无需依赖 LLM。
使用方式:
    from src.analysis.ml_engine import MLEngine
    
    engine = MLEngine(df)
    anomalies = engine.detect_anomalies()
    predictions = engine.predict(column, horizon=7)
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

import pandas as pd
import numpy as np


@dataclass
class AnomalyResult:
    """异常检测结果"""
    column: str
    indices: List[int]
    values: List[float]
    scores: List[float]
    method: str
    description: str


@dataclass
class PredictionResult:
    """预测结果"""
    column: str
    horizon: int
    predictions: List[float]
    confidence_interval: Tuple[List[float], List[float]]
    method: str


@dataclass
class ClusterResult:
    """聚类结果"""
    n_clusters: int
    labels: List[int]
    centers: List[List[float]]
    cluster_sizes: List[int]
    description: str


class MLEngine:
    """机器学习分析引擎"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.results: Dict[str, Any] = {}
    
    def detect_anomalies(self, columns: List[str] = None, 
                        method: str = "isolation_forest",
                        contamination: float = 0.05) -> List[AnomalyResult]:
        """
        检测异常值
        
        Args:
            columns: 要检测的数值列，默认所有数值列
            method: "isolation_forest" | "dbscan" | "zscore"
            contamination: 异常比例估计
        
        Returns:
            异常检测结果列表
        """
        numeric_cols = columns or self._get_numeric_columns()
        results = []
        
        for col in numeric_cols:
            if col not in self.df.columns:
                continue
            
            data = self.df[col].dropna()
            if len(data) < 10:
                continue
            
            try:
                if method == "isolation_forest":
                    from sklearn.ensemble import IsolationForest
                    model = IsolationForest(contamination=contamination, random_state=42)
                    scores = model.fit_predict(data.values.reshape(-1, 1))
                    anomaly_mask = scores == -1
                    
                elif method == "dbscan":
                    from sklearn.cluster import DBSCAN
                    model = DBSCAN(eps=0.5, min_samples=5)
                    labels = model.fit_predict(data.values.reshape(-1, 1))
                    anomaly_mask = labels == -1
                    
                elif method == "zscore":
                    z_scores = np.abs(stats.zscore(data))
                    anomaly_mask = z_scores > 3
                    
                else:
                    continue
                
                anomaly_indices = data[anomaly_mask].index.tolist()
                anomaly_values = data[anomaly_mask].values.tolist()
                
                if anomaly_indices:
                    results.append(AnomalyResult(
                        column=col,
                        indices=anomaly_indices[:20],  # 限制返回数量
                        values=anomaly_values[:20],
                        scores=[float(s) for s in (scores[anomaly_mask] if method == "isolation_forest" else [1.0]*len(anomaly_indices))][:20],
                        method=method,
                        description=f"{col} 检测到 {len(anomaly_indices)} 个异常值 (方法: {method})"
                    ))
                    
            except Exception as e:
                # 降级到简单统计方法
                q1 = data.quantile(0.25)
                q3 = data.quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                mask = (data < lower) | (data > upper)
                
                if mask.sum() > 0:
                    results.append(AnomalyResult(
                        column=col,
                        indices=data[mask].index.tolist()[:20],
                        values=data[mask].values.tolist()[:20],
                        scores=[1.0] * mask.sum(),
                        method="iqr_fallback",
                        description=f"{col} 检测到 {mask.sum()} 个异常值 (IQR 法)"
                    ))
        
        return results
    
    def predict(self, column: str, horizon: int = 7,
                method: str = "linear") -> PredictionResult:
        """
        时间序列预测
        
        Args:
            column: 目标列
            horizon: 预测步数
            method: "linear" | "moving_average" | "exponential_smoothing"
        
        Returns:
            预测结果
        """
        data = self.df[column].dropna()
        if len(data) < 10:
            return PredictionResult(
                column=column, horizon=horizon,
                predictions=[data.mean()] * horizon,
                confidence_interval=([data.mean()]*horizon, [data.mean()]*horizon),
                method="mean_fallback"
            )
        
        if method == "linear":
            # 简单线性趋势
            x = np.arange(len(data))
            slope, intercept = np.polyfit(x, data.values, 1)
            future_x = np.arange(len(data), len(data) + horizon)
            predictions = slope * future_x + intercept
            
            # 计算置信区间（基于历史残差）
            residuals = data.values - (slope * x + intercept)
            std_residual = np.std(residuals)
            upper = predictions + 1.96 * std_residual
            lower = predictions - 1.96 * std_residual
            
        elif method == "moving_average":
            window = min(7, len(data) // 2)
            ma = data.rolling(window=window).mean().iloc[-1]
            predictions = [ma] * horizon
            std = data.std()
            upper = [ma + 1.96 * std] * horizon
            lower = [ma - 1.96 * std] * horizon
            
        elif method == "exponential_smoothing":
            alpha = 0.3
            smoothed = data.ewm(alpha=alpha).mean()
            last = smoothed.iloc[-1]
            predictions = [last] * horizon
            std = data.std()
            upper = [last + 1.96 * std] * horizon
            lower = [last - 1.96 * std] * horizon
            
        else:
            predictions = [data.mean()] * horizon
            upper = [data.mean() + data.std()] * horizon
            lower = [data.mean() - data.std()] * horizon
        
        return PredictionResult(
            column=column,
            horizon=horizon,
            predictions=[float(p) for p in predictions],
            confidence_interval=(upper.tolist(), lower.tolist()),
            method=method
        )
    
    def cluster(self, columns: List[str] = None, 
                n_clusters: int = 3) -> Optional[ClusterResult]:
        """
        K-Means 聚类分析
        
        Args:
            columns: 用于聚类的数值列
            n_clusters: 聚类数量
        
        Returns:
            聚类结果
        """
        numeric_cols = columns or self._get_numeric_columns()
        if len(numeric_cols) < 2:
            return None
        
        data = self.df[numeric_cols].dropna()
        if len(data) < n_clusters * 2:
            return None
        
        try:
            from sklearn.preprocessing import StandardScaler
            from sklearn.cluster import KMeans
            
            scaler = StandardScaler()
            scaled = scaler.fit_transform(data)
            
            model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = model.fit_predict(scaled)
            
            cluster_sizes = [int((labels == i).sum()) for i in range(n_clusters)]
            centers = scaler.inverse_transform(model.cluster_centers_).tolist()
            
            return ClusterResult(
                n_clusters=n_clusters,
                labels=labels.tolist(),
                centers=centers,
                cluster_sizes=cluster_sizes,
                description=f"基于 {', '.join(numeric_cols)} 的 K-Means 聚类 (k={n_clusters})"
            )
            
        except ImportError:
            return None
    
    def feature_importance(self, target: str, 
                          features: List[str] = None) -> Dict[str, float]:
        """
        特征重要性分析（使用随机森林）
        
        Args:
            target: 目标列
            features: 特征列
        
        Returns:
            特征重要性字典
        """
        numeric_cols = features or self._get_numeric_columns()
        if target not in numeric_cols:
            numeric_cols = [c for c in numeric_cols if c != target]
        
        data = self.df[numeric_cols + [target]].dropna()
        if len(data) < 10:
            return {}
        
        try:
            from sklearn.ensemble import RandomForestRegressor
            
            X = data[numeric_cols]
            y = data[target]
            
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
            
            importance = dict(zip(numeric_cols, model.feature_importances_.tolist()))
            return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
            
        except ImportError:
            # 降级到相关性
            correlations = self.df[numeric_cols].corrwith(self.df[target]).abs().to_dict()
            return dict(sorted(correlations.items(), key=lambda x: x[1], reverse=True))
    
    def segment_analysis(self, target: str, segment_col: str) -> Dict[str, Any]:
        """分段分析（按类别分段统计目标列）"""
        if segment_col not in self.df.columns or target not in self.df.columns:
            return {}
        
        segments = self.df.groupby(segment_col)[target].agg([
            'count', 'mean', 'median', 'std', 'min', 'max'
        ]).round(2)
        
        return {
            "segments": segments.to_dict(),
            "top_segment": segments['mean'].idxmax(),
            "bottom_segment": segments['mean'].idxmin(),
            "variance_ratio": float(segments['mean'].std() / segments['mean'].mean()) if segments['mean'].mean() != 0 else 0
        }
    
    def _get_numeric_columns(self) -> List[str]:
        """获取所有数值列"""
        return self.df.select_dtypes(include=[np.number]).columns.tolist()


class AdvancedAnalyzer:
    """高级分析器 — 整合 ML 分析到流水线"""
    
    def __init__(self, df: pd.DataFrame):
        self.ml = MLEngine(df)
        self.df = df
    
    def analyze_all(self, target_column: str = None, 
                   segment_column: str = None) -> Dict[str, Any]:
        """执行所有高级分析"""
        results = {}
        
        # 1. 异常检测
        anomalies = self.ml.detect_anomalies()
        if anomalies:
            results["anomalies"] = [
                {
                    "column": a.column,
                    "count": len(a.indices),
                    "method": a.method,
                    "description": a.description
                }
                for a in anomalies
            ]
        
        # 2. 预测
        if target_column and target_column in self.df.columns:
            prediction = self.ml.predict(target_column, horizon=7)
            results["prediction"] = {
                "column": prediction.column,
                "horizon": prediction.horizon,
                "predictions": prediction.predictions,
                "method": prediction.method
            }
        
        # 3. 聚类
        clusters = self.ml.cluster(n_clusters=3)
        if clusters:
            results["clusters"] = {
                "n_clusters": clusters.n_clusters,
                "sizes": clusters.cluster_sizes,
                "description": clusters.description
            }
        
        # 4. 特征重要性
        if target_column:
            importance = self.ml.feature_importance(target_column)
            if importance:
                results["feature_importance"] = importance
        
        # 5. 分段分析
        if segment_column and segment_column in self.df.columns:
            segments = self.ml.segment_analysis(
                target_column or self.ml._get_numeric_columns()[0], 
                segment_column
            )
            if segments:
                results["segments"] = segments
        
        return results
