"""SQL 数据库加载器 — 支持 SQLite/MySQL/PostgreSQL/MongoDB"""

from typing import Union, Optional, Any
from pathlib import Path
import pandas as pd


class SQLiteLoader:
    """SQLite 加载器"""
    
    @staticmethod
    def load(source: Union[str, Path]) -> pd.DataFrame:
        import sqlite3
        conn = sqlite3.connect(str(source))
        
        # 获取所有表名
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
        if tables.empty:
            raise ValueError("SQLite 数据库中没有表")
        
        # 选择数据量最大的表
        best_table = tables.iloc[0]["name"]
        best_count = 0
        for table in tables["name"]:
            count = pd.read_sql_query(f"SELECT COUNT(*) FROM {table}", conn).iloc[0, 0]
            if count > best_count:
                best_count = count
                best_table = table
        
        df = pd.read_sql_query(f"SELECT * FROM {best_table}", conn)
        conn.close()
        return df
    
    @staticmethod
    def supports(source: Union[str, Path, Any]) -> bool:
        return Path(source).suffix.lower() in [".db", ".sqlite", ".sqlite3"]


class SQLLoader:
    """通用 SQL 数据库加载器 (MySQL/PostgreSQL/...)"""
    
    @staticmethod
    def load(connection_string: str, table: Optional[str] = None) -> pd.DataFrame:
        try:
            from sqlalchemy import create_engine
        except ImportError:
            raise ImportError("使用 SQL 数据库需要安装 sqlalchemy: pip install sqlalchemy")
        
        engine = create_engine(connection_string)
        
        if table:
            return pd.read_sql_table(table, engine)
        
        # 自动选择表
        tables = pd.read_sql_query("SHOW TABLES", engine) if "mysql" in connection_string else \
                 pd.read_sql_query("SELECT tablename FROM pg_tables WHERE schemaname='public'", engine)
        
        if tables.empty:
            raise ValueError("数据库中没有表")
        
        best_table = tables.iloc[0, 0]
        return pd.read_sql_table(best_table, engine)


class MongoDBLoader:
    """MongoDB 加载器"""
    
    @staticmethod
    def load(connection_string: str, collection: Optional[str] = None, limit: int = 10000) -> pd.DataFrame:
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("使用 MongoDB 需要安装 pymongo: pip install pymongo")
        
        client = MongoClient(connection_string)
        db = client.get_default_database()
        
        if collection:
            coll = db[collection]
        else:
            # 选择文档数最多的集合
            best_coll = None
            best_count = 0
            for name in db.list_collection_names():
                count = db[name].count_documents({})
                if count > best_count:
                    best_count = count
                    best_coll = db[name]
            coll = best_coll
        
        docs = list(coll.find().limit(limit))
        client.close()
        
        if not docs:
            raise ValueError("MongoDB 集合为空")
        
        return pd.json_normalize(docs)


__all__ = ["SQLiteLoader", "SQLLoader", "MongoDBLoader"]
