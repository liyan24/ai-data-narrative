"""数据类型层 — 各种数据格式加载器

支持 CSV/Excel/JSON/Parquet/数据库/API 等多种数据源
"""

import json
import warnings
from typing import Union, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import numpy as np

from src.config import INPUT_CONFIG

warnings.filterwarnings("ignore", category=UserWarning)


class DataLoaderInterface:
    """数据加载器接口"""
    
    @staticmethod
    def load(source: Union[str, Path, Any]) -> pd.DataFrame:
        """加载数据为 DataFrame"""
        raise NotImplementedError
    
    @staticmethod
    def supports(source: Union[str, Path, Any]) -> bool:
        """判断是否支持该数据源"""
        raise NotImplementedError


class CSVLoader(DataLoaderInterface):
    """CSV 加载器 — 支持自动编码探测"""
    
    @staticmethod
    def load(source: Union[str, Path]) -> pd.DataFrame:
        file_path = Path(source)
        for encoding in INPUT_CONFIG["encoding_fallback"]:
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法识别文件编码: {file_path}")
    
    @staticmethod
    def supports(source: Union[str, Path, Any]) -> bool:
        return Path(source).suffix.lower() == ".csv"


class ExcelLoader(DataLoaderInterface):
    """Excel 加载器 — 支持多 Sheet 自动选择"""
    
    @staticmethod
    def load(source: Union[str, Path]) -> pd.DataFrame:
        file_path = Path(source)
        xls = pd.ExcelFile(file_path, engine="openpyxl")
        
        # 自动选择数据量最大的 Sheet
        best_sheet = None
        best_rows = 0
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, nrows=5)
            if len(df.columns) > 1 and len(df) >= best_rows:
                best_rows = len(df)
                best_sheet = sheet_name
        
        if best_sheet is None:
            best_sheet = xls.sheet_names[0]
        
        return pd.read_excel(xls, sheet_name=best_sheet)
    
    @staticmethod
    def supports(source: Union[str, Path, Any]) -> bool:
        return Path(source).suffix.lower() in [".xlsx", ".xls"]


class JSONLoader(DataLoaderInterface):
    """JSON 加载器 — 支持多种 JSON 结构"""
    
    @staticmethod
    def load(source: Union[str, Path]) -> pd.DataFrame:
        file_path = Path(source)
        
        # 先尝试按 JSON Lines 读取
        try:
            return JSONLinesLoader.load(file_path)
        except Exception:
            pass
        
        # 标准 JSON 读取
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 对象列表
        if isinstance(data, list):
            # 确保每个元素都是字典
            if data and isinstance(data[0], dict):
                return pd.json_normalize(data)
            elif data:
                # 元素不是字典 — 可能是值列表，包裹为 DataFrame
                return pd.DataFrame({"value": data})
            else:
                return pd.DataFrame()
        
        # 字典结构 — 尝试提取最深层的数据列表
        elif isinstance(data, dict):
            df = JSONLoader._extract_data_from_dict(data)
            if df is not None:
                return df
        
        raise ValueError(f"不支持的 JSON 结构: {type(data).__name__}")
    
    @staticmethod
    def _extract_data_from_dict(data: Dict) -> Optional[pd.DataFrame]:
        """从嵌套字典中提取数据列表"""
        # 策略：递归查找列表，返回第一个元素为字典的列表
        def find_data_list(obj, depth=0):
            if depth > 5:
                return None
            if isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
                return obj
            if isinstance(obj, dict):
                for k, v in obj.items():
                    result = find_data_list(v, depth + 1)
                    if result is not None:
                        return result
            return None
        
        data_list = find_data_list(data)
        if data_list:
            return pd.json_normalize(data_list)
        
        # 如果字典的每个值都是列表，尝试横向展开
        if all(isinstance(v, list) for v in data.values()):
            # 检查是否是键值对结构
            if all(len(v) == len(list(data.values())[0]) for v in data.values()):
                return pd.DataFrame(data)
        
        return None
    
    @staticmethod
    def supports(source: Union[str, Path, Any]) -> bool:
        return Path(source).suffix.lower() == ".json"


class JSONLinesLoader(DataLoaderInterface):
    """JSON Lines 加载器 — 每行一个 JSON 对象"""
    
    @staticmethod
    def load(source: Union[str, Path]) -> pd.DataFrame:
        file_path = Path(source)
        records = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    # JSON Lines 要求每行是一个独立记录（不是数组）
                    if isinstance(record, list):
                        raise ValueError("该行是 JSON 数组，不是 JSON Lines 格式")
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        if not records:
            raise ValueError("未找到有效的 JSON Lines 记录")
        
        return pd.json_normalize(records)
    
    @staticmethod
    def supports(source: Union[str, Path, Any]) -> bool:
        return Path(source).suffix.lower() == ".jsonl"


class ParquetLoader(DataLoaderInterface):
    """Parquet 加载器"""
    
    @staticmethod
    def load(source: Union[str, Path]) -> pd.DataFrame:
        return pd.read_parquet(source)
    
    @staticmethod
    def supports(source: Union[str, Path, Any]) -> bool:
        return Path(source).suffix.lower() == ".parquet"


# 导出所有加载器
__all__ = [
    "DataLoaderInterface",
    "CSVLoader", "ExcelLoader", "JSONLoader", "JSONLinesLoader", "ParquetLoader",
]
