"""数据类型注册表 — 统一发现和管理所有数据加载器

支持文件扩展名、URL、数据库连接字符串的自动路由
"""

import re
from typing import Union, Dict, Any, Optional, List
from pathlib import Path
import pandas as pd

from src.data_schema.loaders import (
    CSVLoader, ExcelLoader, JSONLoader, JSONLinesLoader, ParquetLoader
)
from src.data_schema.loaders.sql_loader import SQLiteLoader, SQLLoader, MongoDBLoader
from src.data_schema.loaders.api_loader import RESTAPILoader
from src.data_schema.models import DataProfile, SchemaDescriptor


class TypeRegistry:
    """数据类型注册表 — 统一管理所有数据加载器"""
    
    # 文件扩展名到加载器的映射
    EXTENSION_LOADERS: Dict[str, Any] = {
        ".csv": CSVLoader,
        ".xlsx": ExcelLoader,
        ".xls": ExcelLoader,
        ".json": JSONLoader,
        ".jsonl": JSONLinesLoader,
        ".parquet": ParquetLoader,
        ".db": SQLiteLoader,
        ".sqlite": SQLiteLoader,
        ".sqlite3": SQLiteLoader,
    }
    
    # 数据库连接字符串前缀
    DB_PREFIXES: Dict[str, Any] = {
        "sqlite://": SQLiteLoader,
        "mysql://": SQLLoader,
        "postgresql://": SQLLoader,
        "postgres://": SQLLoader,
        "mongodb://": MongoDBLoader,
        "mongodb+srv://": MongoDBLoader,
    }
    
    @classmethod
    def load(cls, source: Union[str, Path], **kwargs) -> DataProfile:
        """
        统一入口：根据源类型自动选择加载器
        
        Args:
            source: 数据源（文件路径/URL/连接字符串）
            **kwargs: 额外参数（用于数据库/API 加载）
            
        Returns:
            DataProfile 对象
        """
        source_str = str(source)
        source_path = Path(source) if not cls._is_url_or_connection(source_str) else None
        
        # 判断源类型
        if source_path and source_path.exists():
            # 本地文件
            suffix = source_path.suffix.lower()
            loader_class = cls.EXTENSION_LOADERS.get(suffix)
            if loader_class:
                df = loader_class.load(source_path)
                return DataProfile(df=df, source_name=source_path.name)
            else:
                raise ValueError(f"不支持的文件格式: {suffix}")
        
        elif cls._is_url(source_str):
            # URL — REST API
            df = RESTAPILoader.load(source_str, **kwargs)
            return DataProfile(df=df, source_name=source_str.split("/")[-1].split("?")[0] or "api_data")
        
        elif cls._is_db_connection(source_str):
            # 数据库连接字符串
            for prefix, loader_class in cls.DB_PREFIXES.items():
                if source_str.startswith(prefix):
                    if loader_class in [SQLLoader, MongoDBLoader]:
                        df = loader_class.load(source_str, **kwargs)
                    else:
                        df = loader_class.load(source_str)
                    return DataProfile(df=df, source_name=f"db_{prefix.replace('://', '')}")
            raise ValueError(f"不支持的数据库连接字符串: {source_str[:50]}...")
        
        else:
            raise ValueError(f"无法识别的数据源: {source_str}")
    
    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """获取支持的所有格式"""
        formats = list(cls.EXTENSION_LOADERS.keys())
        formats.extend(["URL (REST API)", "SQLite", "MySQL", "PostgreSQL", "MongoDB"])
        return formats
    
    @staticmethod
    def _is_url(source: str) -> bool:
        """判断是否为 URL"""
        return bool(re.match(r'^https?://', source))
    
    @staticmethod
    def _is_db_connection(source: str) -> bool:
        """判断是否为数据库连接字符串"""
        return any(source.startswith(prefix) for prefix in TypeRegistry.DB_PREFIXES.keys())
    
    @staticmethod
    def _is_url_or_connection(source: str) -> bool:
        """判断是否为 URL 或连接字符串"""
        return TypeRegistry._is_url(source) or TypeRegistry._is_db_connection(source)


__all__ = ["TypeRegistry"]
