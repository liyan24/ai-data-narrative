"""数据类型层

支持 CSV/Excel/JSON/Parquet/数据库/API 等多种数据源，
通过 LLM 辅助理解字段语义和业务含义。
"""

from src.data_schema.models import (
    DataProfile, SchemaDescriptor, FieldDescriptor, FieldRole
)
from src.data_schema.registry import TypeRegistry
from src.data_schema.schema_engine import SchemaEngine

__all__ = [
    # 模型
    "DataProfile", "SchemaDescriptor", "FieldDescriptor", "FieldRole",
    # 引擎
    "TypeRegistry", "SchemaEngine",
]
