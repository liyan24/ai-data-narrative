"""数据类型层 — 数据模型定义

包含数据画像、Schema描述、字段描述等核心数据类
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class FieldRole(Enum):
    """字段在分析中的角色"""
    TIME_AXIS = "time_axis"      # 时间维度
    MEASURE = "measure"           # 度量值（可聚合的数值）
    DIMENSION = "dimension"       # 分类维度（可分组）
    IDENTIFIER = "identifier"     # 标识符（ID/唯一值）
    TEXT = "text"                 # 文本内容（描述/备注等）
    UNKNOWN = "unknown"           # 未知角色


@dataclass
class FieldDescriptor:
    """字段描述 — 包含物理类型和语义理解"""
    
    name: str
    physical_type: str               # pandas dtype
    logical_type: str = ""          # 推断的业务类型: numeric | categorical | datetime | text | boolean | id
    semantic_meaning: str = ""      # 语义含义（如"订单创建日期"）
    role: FieldRole = FieldRole.UNKNOWN  # 字段在分析中的角色
    confidence: float = 0.0          # 类型推断置信度
    sample_values: List[Any] = field(default_factory=list)  # 样本值
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "physical_type": self.physical_type,
            "logical_type": self.logical_type,
            "semantic_meaning": self.semantic_meaning,
            "role": self.role.value,
            "confidence": self.confidence,
            "sample_values": [str(v) for v in self.sample_values[:5]],
        }


@dataclass
class SchemaDescriptor:
    """Schema描述 — LLM辅助理解数据结构"""
    
    format: str                      # 数据格式: csv | excel | json | parquet | ...
    shape: Dict[str, int] = field(default_factory=dict)  # {"rows": 1000, "columns": 15}
    fields: List[FieldDescriptor] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)  # 字段间关系
    llm_summary: str = ""             # LLM对数据的整体理解摘要
    
    def get_field(self, name: str) -> Optional[FieldDescriptor]:
        """根据名称获取字段描述"""
        for f in self.fields:
            if f.name == name:
                return f
        return None
    
    def get_fields_by_role(self, role: FieldRole) -> List[FieldDescriptor]:
        """根据角色获取字段列表"""
        return [f for f in self.fields if f.role == role]
    
    def to_markdown(self) -> str:
        """生成Markdown格式的Schema描述"""
        lines = [
            f"## 数据结构: {self.format}",
            f"",
            f"**维度**: {self.shape.get('rows', 0)} 行 × {self.shape.get('columns', 0)} 列",
            f"",
            f"### 字段列表",
            f"",
            "| 字段名 | 物理类型 | 逻辑类型 | 角色 | 语义含义 | 置信度 |",
            "|--------|----------|----------|------|----------|--------|",
        ]
        for f in self.fields:
            lines.append(
                f"| {f.name} | {f.physical_type} | {f.logical_type} | {f.role.value} | {f.semantic_meaning or '-'} | {f.confidence:.0%} |"
            )
        
        if self.relationships:
            lines.extend(["", "### 字段关系", ""])
            for r in self.relationships:
                lines.append(f"- {r.get('from', '?')} → {r.get('to', '?')} ({r.get('type', 'unknown')})")
        
        if self.llm_summary:
            lines.extend(["", "### 数据摘要", "", self.llm_summary])
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format,
            "shape": self.shape,
            "fields": [f.to_dict() for f in self.fields],
            "relationships": self.relationships,
            "llm_summary": self.llm_summary,
        }


@dataclass
class DataProfile:
    """数据画像 — 包含原始DataFrame + Schema描述 + 统计信息"""
    
    df: Any = None                    # pandas DataFrame（实际对象，不参与序列化）
    source_name: str = "unknown"
    schema: Optional[SchemaDescriptor] = None
    
    # 便捷属性（从df和schema派生）
    @property
    def row_count(self) -> int:
        return len(self.df) if self.df is not None else 0
    
    @property
    def col_count(self) -> int:
        return len(self.df.columns) if self.df is not None else 0
    
    def get_column_types(self) -> Dict[str, str]:
        """获取列名到逻辑类型的映射"""
        if self.schema:
            return {f.name: f.logical_type for f in self.schema.fields}
        # 降级：从pandas dtype推断
        if self.df is not None:
            result = {}
            for col in self.df.columns:
                dtype = str(self.df[col].dtype)
                if 'int' in dtype or 'float' in dtype:
                    result[col] = 'numeric'
                elif 'datetime' in dtype:
                    result[col] = 'datetime'
                elif 'bool' in dtype:
                    result[col] = 'boolean'
                else:
                    result[col] = 'categorical' if self.df[col].nunique() / len(self.df) < 0.05 else 'text'
            return result
        return {}
    
    def get_summary(self) -> Dict[str, Any]:
        """获取数据摘要（可序列化）"""
        type_distribution = {}
        if self.schema:
            for f in self.schema.fields:
                t = f.logical_type or 'unknown'
                type_distribution[t] = type_distribution.get(t, 0) + 1
        
        missing_summary = {}
        if self.df is not None:
            for col in self.df.columns:
                missing = int(self.df[col].isna().sum())
                if missing > 0:
                    missing_summary[col] = missing
        
        return {
            "source": self.source_name,
            "rows": self.row_count,
            "columns": self.col_count,
            "type_distribution": type_distribution,
            "missing_summary": missing_summary,
            "schema": self.schema.to_dict() if self.schema else None,
        }
    
    def to_markdown(self) -> str:
        """生成数据概览Markdown"""
        lines = [
            f"## 数据概览: {self.source_name}",
            "",
            f"- **行数**: {self.row_count:,}",
            f"- **列数**: {self.col_count}",
            "",
        ]
        
        if self.schema:
            lines.append(self.schema.to_markdown())
        
        return "\n".join(lines)


__all__ = [
    "FieldRole", "FieldDescriptor", "SchemaDescriptor", "DataProfile",
]