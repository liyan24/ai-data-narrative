"""
性能优化模块 — 大数据分块处理、内存优化、缓存机制

核心能力：
- 分块读取：处理超大 CSV/Excel 文件
- 内存优化：类型降采样、列筛选
- 采样分析：大数据集随机采样快速分析
- 缓存机制：避免重复计算
- 进度跟踪：长时间任务的进度反馈
"""

from typing import Dict, List, Any, Optional, Iterator, Callable
from dataclasses import dataclass
from pathlib import Path
import functools
import hashlib
import pickle
import os

import pandas as pd
import numpy as np

from src.config import INPUT_CONFIG, OUTPUT_DIR


class ChunkedDataLoader:
    """分块数据加载器"""
    
    DEFAULT_CHUNK_SIZE = 100000      # 默认每块 10 万行
    
    def __init__(self, chunk_size: int = None):
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
    
    def load_large_csv(self, file_path: str, columns: List[str] = None,
                       dtype: Dict[str, type] = None) -> Iterator[pd.DataFrame]:
        """
        分块加载大型 CSV
        
        Yields:
            每块 DataFrame
        """
        for chunk in pd.read_csv(
            file_path,
            chunksize=self.chunk_size,
            usecols=columns,
            dtype=dtype,
            low_memory=True
        ):
            yield chunk
    
    def load_large_excel(self, file_path: str, sheet_name: str = None,
                        chunk_size: int = None) -> pd.DataFrame:
        """
        加载大型 Excel（通过逐行读取）
        
        注：Excel 不支持真正的分块，这里使用内存优化方式
        """
        # 使用 openpyxl 的 read_only 模式
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name or 0,
            engine='openpyxl'
        )
        return df
    
    def analyze_in_chunks(self, file_path: str, column_types: Dict[str, str],
                         analysis_func: Callable[[pd.DataFrame], Dict],
                         progress_callback: Callable[[int, int], None] = None) -> Dict:
        """
        分块分析数据
        
        Args:
            file_path: 文件路径
            column_types: 列类型（用于选择需要分析的列）
            analysis_func: 分析函数，接收 DataFrame 返回 Dict
            progress_callback: 进度回调函数 (current_chunk, total_chunks)
            
        Returns:
            合并后的分析结果
        """
        # 估算总行数
        total_rows = self._estimate_rows(file_path)
        total_chunks = max(1, total_rows // self.chunk_size)
        
        results = []
        chunk_idx = 0
        
        for chunk in self.load_large_csv(file_path):
            chunk_result = analysis_func(chunk)
            results.append(chunk_result)
            chunk_idx += 1
            
            if progress_callback:
                progress_callback(chunk_idx, total_chunks)
        
        # 合并结果
        return self._merge_chunk_results(results)
    
    def _estimate_rows(self, file_path: str) -> int:
        """估算文件行数"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 读取前 1000 行计算平均行长度
                sample = []
                for _ in range(1000):
                    line = f.readline()
                    if not line:
                        break
                    sample.append(len(line))
                
                if not sample:
                    return 0
                
                avg_line_length = sum(sample) / len(sample)
                file_size = os.path.getsize(file_path)
                
                return int(file_size / avg_line_length)
        except Exception:
            return 0
    
    def _merge_chunk_results(self, results: List[Dict]) -> Dict:
        """合并分块分析结果"""
        merged = {}
        
        for result in results:
            for key, value in result.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, (int, float)):
                    # 数值型累加或取平均
                    if key in ['count', 'sum', 'total']:
                        merged[key] += value
                    else:
                        merged[key] = (merged[key] + value) / 2
                elif isinstance(value, list):
                    merged[key].extend(value)
                elif isinstance(value, dict):
                    for k, v in value.items():
                        if k not in merged[key]:
                            merged[key][k] = v
                        elif isinstance(v, (int, float)):
                            merged[key][k] += v
        
        return merged


class MemoryOptimizer:
    """内存优化器"""
    
    @staticmethod
    def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        优化 DataFrame 内存占用
        
        策略：
        1. 整数类型降采样（int64 -> int32/int16/int8）
        2. 浮点类型降采样（float64 -> float32）
        3. 类别类型转换（object -> category）
        4. 删除不必要的列
        """
        df_optimized = df.copy()
        
        for col in df_optimized.columns:
            col_type = df_optimized[col].dtype
            
            if pd.api.types.is_integer_dtype(col_type):
                # 整数降采样
                c_min = df_optimized[col].min()
                c_max = df_optimized[col].max()
                
                if c_min >= np.iinfo(np.int8).min and c_max <= np.iinfo(np.int8).max:
                    df_optimized[col] = df_optimized[col].astype(np.int8)
                elif c_min >= np.iinfo(np.int16).min and c_max <= np.iinfo(np.int16).max:
                    df_optimized[col] = df_optimized[col].astype(np.int16)
                elif c_min >= np.iinfo(np.int32).min and c_max <= np.iinfo(np.int32).max:
                    df_optimized[col] = df_optimized[col].astype(np.int32)
            
            elif pd.api.types.is_float_dtype(col_type):
                # 浮点降采样
                df_optimized[col] = df_optimized[col].astype(np.float32)
            
            elif pd.api.types.is_object_dtype(col_type):
                # 类别转换
                num_unique = df_optimized[col].nunique()
                num_total = len(df_optimized[col])
                
                if num_unique / num_total < 0.5:  # 唯一值占比 < 50%
                    df_optimized[col] = df_optimized[col].astype('category')
        
        return df_optimized
    
    @staticmethod
    def get_memory_usage(df: pd.DataFrame) -> Dict[str, Any]:
        """获取内存使用详情"""
        usage = df.memory_usage(deep=True)
        
        return {
            "total_mb": usage.sum() / 1024 / 1024,
            "per_column": {col: usage.get(col, 0) / 1024 / 1024 for col in df.columns},
            "index_mb": usage.get('Index', 0) / 1024 / 1024
        }


class SamplingAnalyzer:
    """采样分析器 — 大数据集快速采样分析"""
    
    DEFAULT_SAMPLE_SIZE = 10000      # 默认采样 1 万行
    
    def __init__(self, sample_size: int = None):
        self.sample_size = sample_size or self.DEFAULT_SAMPLE_SIZE
    
    def sample_and_analyze(self, df: pd.DataFrame, 
                          analysis_func: Callable[[pd.DataFrame], Dict]) -> Dict:
        """
        采样分析
        
        Args:
            df: 原始数据
            analysis_func: 分析函数
            
        Returns:
            分析结果 + 采样信息
        """
        if len(df) <= self.sample_size:
            # 数据量不大，直接分析
            result = analysis_func(df)
            result["sampling_info"] = {
                "sampled": False,
                "original_rows": len(df),
                "sample_rows": len(df)
            }
            return result
        
        # 随机采样
        sample_df = df.sample(n=self.sample_size, random_state=42)
        
        result = analysis_func(sample_df)
        result["sampling_info"] = {
            "sampled": True,
            "original_rows": len(df),
            "sample_rows": self.sample_size,
            "sample_ratio": self.sample_size / len(df)
        }
        
        return result
    
    def stratified_sample(self, df: pd.DataFrame, stratify_col: str,
                         sample_size: int = None) -> pd.DataFrame:
        """
        分层采样 — 保持类别分布
        
        Args:
            df: 原始数据
            stratify_col: 分层列
            sample_size: 采样大小
            
        Returns:
            采样后的 DataFrame
        """
        n = sample_size or self.sample_size
        
        # 按类别分层采样
        grouped = df.groupby(stratify_col)
        
        # 计算每层的采样数
        proportions = grouped.size() / len(df)
        samples_per_group = (proportions * n).round().astype(int)
        
        # 确保至少采样1个
        samples_per_group = samples_per_group.clip(lower=1)
        
        sampled = []
        for group_name, group_df in grouped:
            n_sample = min(samples_per_group[group_name], len(group_df))
            sampled.append(group_df.sample(n=n_sample, random_state=42))
        
        return pd.concat(sampled, ignore_index=True)


class AnalysisCache:
    """分析缓存 — 避免重复计算"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or (OUTPUT_DIR / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, Any] = {}
    
    def _get_cache_key(self, file_path: str, analysis_name: str, params: Dict = None) -> str:
        """生成缓存键"""
        # 对于文件路径获取修改时间，对于非文件路径使用字符串本身
        if os.path.isfile(file_path):
            mtime = os.path.getmtime(file_path)
        else:
            mtime = file_path
        key_data = f"{file_path}:{mtime}:{analysis_name}:{str(params)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, file_path: str, analysis_name: str, params: Dict = None) -> Optional[Any]:
        """获取缓存结果"""
        cache_key = self._get_cache_key(file_path, analysis_name, params)
        
        # 先检查内存缓存
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]
        
        # 检查磁盘缓存
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    result = pickle.load(f)
                self._memory_cache[cache_key] = result
                return result
            except Exception:
                pass
        
        return None
    
    def set(self, file_path: str, analysis_name: str, result: Any, params: Dict = None):
        """设置缓存"""
        cache_key = self._get_cache_key(file_path, analysis_name, params)
        
        # 内存缓存
        self._memory_cache[cache_key] = result
        
        # 磁盘缓存
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception:
            pass
    
    def clear(self):
        """清除所有缓存"""
        self._memory_cache.clear()
        for f in self.cache_dir.glob("*.pkl"):
            f.unlink()


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total_steps: int = 1, description: str = ""):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.step_names: List[str] = []
    
    def set_steps(self, steps: List[str]):
        """设置步骤名称"""
        self.step_names = steps
        self.total_steps = len(steps)
    
    def next_step(self, step_name: str = None):
        """进入下一步"""
        self.current_step += 1
        if step_name:
            self.description = step_name
        elif self.current_step <= len(self.step_names):
            self.description = self.step_names[self.current_step - 1]
        
        progress = self.current_step / self.total_steps * 100
        print(f"[PROGRESS] [{self.current_step}/{self.total_steps}] {progress:.0f}% - {self.description}")
    
    def get_progress(self) -> Dict[str, Any]:
        """获取当前进度"""
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_pct": self.current_step / self.total_steps * 100,
            "description": self.description
        }
