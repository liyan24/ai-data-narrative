"""
数据源连接器 — 数据库连接、API 数据源

支持 MySQL、PostgreSQL、SQLite、MongoDB 和 REST API 数据源。
使用方式:
    from src.data_input.connectors import DatabaseConnector, APIConnector
    
    db = DatabaseConnector("mysql://user:pass@host/db")
    df = db.query("SELECT * FROM sales")
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
import json

import pandas as pd
import numpy as np


@dataclass
class ConnectionConfig:
    """连接配置"""
    type: str  # "mysql", "postgresql", "sqlite", "mongodb", "api"
    host: str = None
    port: int = None
    database: str = None
    username: str = None
    password: str = None
    url: str = None
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)


class DatabaseConnector:
    """数据库连接器"""
    
    SUPPORTED_TYPES = {"mysql", "postgresql", "sqlite", "mongodb"}
    
    def __init__(self, connection_string: str = None, config: ConnectionConfig = None):
        self.connection_string = connection_string
        self.config = config
        self._connection = None
        self._engine = None
        
        if connection_string and not config:
            self.config = self._parse_connection_string(connection_string)
    
    def _parse_connection_string(self, conn_str: str) -> ConnectionConfig:
        """解析连接字符串"""
        parsed = urlparse(conn_str)
        
        db_type = parsed.scheme
        if db_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        
        return ConnectionConfig(
            type=db_type,
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path.lstrip("/") if parsed.path else None,
            username=parsed.username,
            password=parsed.password
        )
    
    def connect(self):
        """建立连接"""
        if self.config.type == "sqlite":
            import sqlite3
            db_path = self.config.database or ":memory:"
            self._connection = sqlite3.connect(db_path)
        elif self.config.type in ("mysql", "postgresql"):
            try:
                import sqlalchemy
                driver = "pymysql" if self.config.type == "mysql" else "psycopg2"
                conn_str = f"{self.config.type}+{driver}://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
                self._engine = sqlalchemy.create_engine(conn_str)
            except ImportError:
                raise ImportError(f"请安装 {driver} 驱动")
        elif self.config.type == "mongodb":
            try:
                import pymongo
                client = pymongo.MongoClient(f"mongodb://{self.config.host}:{self.config.port}/")
                self._connection = client[self.config.database]
            except ImportError:
                raise ImportError("请安装 pymongo")
        
        return self
    
    def query(self, sql: str, params: Dict = None) -> pd.DataFrame:
        """执行 SQL 查询"""
        if self.config.type == "sqlite":
            return pd.read_sql_query(sql, self._connection, params=params)
        elif self.config.type in ("mysql", "postgresql"):
            with self._engine.connect() as conn:
                return pd.read_sql(sql, conn, params=params)
        elif self.config.type == "mongodb":
            # MongoDB 使用 collection.find()
            collection = self._connection[sql]
            data = list(collection.find(params or {}))
            for d in data:
                d.pop("_id", None)
            return pd.DataFrame(data)
        
        return pd.DataFrame()
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        if self.config.type == "sqlite":
            cursor = self._connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
        elif self.config.type in ("mysql", "postgresql"):
            inspector = self._engine.dialect.name
            # 简化的表名获取
            if self.config.type == "mysql":
                sql = "SHOW TABLES"
            else:
                sql = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            df = self.query(sql)
            return df.iloc[:, 0].tolist()
        elif self.config.type == "mongodb":
            return self._connection.list_collection_names()
        return []
    
    def get_schema(self, table: str) -> pd.DataFrame:
        """获取表结构"""
        if self.config.type == "sqlite":
            return self.query(f"PRAGMA table_info({table})")
        elif self.config.type == "mysql":
            return self.query(f"DESCRIBE {table}")
        elif self.config.type == "postgresql":
            return self.query(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table}'
            """)
        return pd.DataFrame()
    
    def close(self):
        """关闭连接"""
        if self._connection:
            if self.config.type == "sqlite":
                self._connection.close()
            elif self.config.type == "mongodb":
                self._connection.client.close()
        if self._engine:
            self._engine.dispose()
    
    def __enter__(self):
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class APIConnector:
    """API 数据源连接器"""
    
    def __init__(self, base_url: str = None, headers: Dict[str, str] = None, 
                 config: ConnectionConfig = None):
        self.config = config or ConnectionConfig(type="api", url=base_url, headers=headers or {})
        self.base_url = self.config.url or base_url
        self.headers = self.config.headers or headers or {}
    
    def fetch(self, endpoint: str = "", params: Dict = None, 
              method: str = "GET", data: Dict = None) -> pd.DataFrame:
        """获取 API 数据"""
        try:
            import requests
        except ImportError:
            raise ImportError("请安装 requests")
        
        url = f"{self.base_url}/{endpoint}".rstrip("/")
        
        if method.upper() == "GET":
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
        else:
            raise ValueError(f"不支持的 HTTP 方法: {method}")
        
        response.raise_for_status()
        json_data = response.json()
        
        # 尝试提取数据数组
        if isinstance(json_data, list):
            return pd.DataFrame(json_data)
        elif isinstance(json_data, dict):
            # 常见 API 响应格式
            for key in ("data", "results", "items", "records"):
                if key in json_data and isinstance(json_data[key], list):
                    return pd.DataFrame(json_data[key])
            # 单条记录
            return pd.DataFrame([json_data])
        
        return pd.DataFrame()
    
    def fetch_paginated(self, endpoint: str, page_param: str = "page",
                       size_param: str = "size", page_size: int = 100,
                       max_pages: int = 10) -> pd.DataFrame:
        """分页获取数据"""
        all_data = []
        
        for page in range(1, max_pages + 1):
            params = {page_param: page, size_param: page_size}
            df = self.fetch(endpoint, params=params)
            if df.empty:
                break
            all_data.append(df)
            if len(df) < page_size:
                break
        
        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


class DataSourceManager:
    """数据源管理器 — 统一管理多种数据源"""
    
    def __init__(self):
        self.sources: Dict[str, Any] = {}
    
    def add_database(self, name: str, connection_string: str):
        """添加数据库源"""
        self.sources[name] = DatabaseConnector(connection_string)
    
    def add_api(self, name: str, base_url: str, headers: Dict = None):
        """添加 API 源"""
        self.sources[name] = APIConnector(base_url, headers)
    
    def query(self, name: str, query: str, **kwargs) -> pd.DataFrame:
        """查询数据源"""
        source = self.sources.get(name)
        if not source:
            raise ValueError(f"未知数据源: {name}")
        
        if isinstance(source, DatabaseConnector):
            with source.connect():
                return source.query(query, kwargs)
        elif isinstance(source, APIConnector):
            return source.fetch(endpoint=query, params=kwargs)
        
        return pd.DataFrame()
    
    def list_sources(self) -> List[str]:
        """列出所有数据源"""
        return list(self.sources.keys())
    
    def test_connection(self, name: str) -> Dict[str, Any]:
        """测试连接"""
        source = self.sources.get(name)
        if not source:
            return {"status": "error", "message": "数据源不存在"}
        
        try:
            if isinstance(source, DatabaseConnector):
                with source.connect():
                    tables = source.get_tables()
                    return {"status": "ok", "tables": len(tables)}
            elif isinstance(source, APIConnector):
                df = source.fetch()
                return {"status": "ok", "columns": len(df.columns)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
