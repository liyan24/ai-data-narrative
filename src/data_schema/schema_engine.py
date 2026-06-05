"""Schema理解引擎 — LLM辅助理解数据结构

输入: DataFrame
输出: SchemaDescriptor（字段语义 + 角色 + 关系）
"""

import json
from typing import Dict, Any, Optional, List

import pandas as pd

from src.data_schema.models import SchemaDescriptor, FieldDescriptor, FieldRole, DataProfile
from src.llm_client import LLMClient, get_llm_client


# 规则引擎：基于字段名和数据特征推断字段角色
_RULE_ROLE_MAPPING = {
    # 时间轴
    "time_axis": ["date", "time", "timestamp", "datetime", "created_at", "updated_at", 
                  "日期", "时间", "年月", "年份", "月份", "日期", "下单时间", "创建时间"],
    # 度量值
    "measure": ["amount", "price", "cost", "revenue", "sales", "quantity", "count", 
                "value", "total", "sum", "avg", "rate", "score", "profit", "margin",
                "金额", "价格", "成本", "收入", "销售额", "销量", "数量", "总数", "均值", "得分", "利润"],
    # 标识符
    "identifier": ["id", "uuid", "code", "no", "number", "index", "seq",
                   "编号", "序号", "编码", "id", "标识"],
}


_DEFAULT_SCHEMA_PROMPT = """你是数据语义分析专家。

请根据以下数据样本和字段信息，分析每个字段的业务含义和在分析中的角色。

【数据信息】
文件名: {source_name}
数据维度: {row_count} 行 × {column_count} 列

【字段样本】
{field_samples}

请分析每个字段：
1. 业务语义含义（如"订单创建日期"、"商品售价"）
2. 在数据分析中的角色:
   - time_axis: 时间维度（日期、时间戳等）
   - measure: 度量值（金额、数量、评分等可聚合数值）
   - dimension: 分类维度（类别、地区、状态等可分组字段）
   - identifier: 标识符（ID、编号、UUID）
   - text: 文本内容（描述、备注、评论）
3. 字段间的可能关系（如 user_id 与 order_amount 的关系）

输出 JSON 格式:
{{
    "fields": [
        {{
            "name": "字段名",
            "logical_type": "numeric|categorical|datetime|text|boolean|id",
            "semantic_meaning": "业务含义描述",
            "role": "time_axis|measure|dimension|identifier|text"
        }}
    ],
    "relationships": [
        {{
            "from": "字段A",
            "to": "字段B",
            "type": "group_by|correlate|time_series|hierarchy"
        }}
    ],
    "llm_summary": "对这份数据的整体理解摘要（1-2句话）"
}}
"""


class SchemaEngine:
    """Schema理解引擎 — 规则+LLM混合"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None,
                 prompt_template: Optional[str] = None):
        self.llm = llm_client or get_llm_client()
        self.prompt_template = prompt_template or _DEFAULT_SCHEMA_PROMPT
    
    def analyze(self, data_profile: DataProfile) -> SchemaDescriptor:
        """
        分析数据结构，生成Schema描述
        
        Args:
            data_profile: 数据画像（含DataFrame）
            
        Returns:
            SchemaDescriptor 对象
        """
        df = data_profile.df
        if df is None:
            raise ValueError("DataProfile 中没有 DataFrame")
        
        # Step 1: 规则引擎生成初步推断
        fields = self._rule_based_infer(df)
        
        # Step 2: LLM 增强（如果可用）
        if self.llm and self.llm.api_key:
            try:
                llm_fields, relationships, summary = self._llm_enhance(df, data_profile.source_name, fields)
                # 合并 LLM 结果（LLM 置信度更高时覆盖）
                fields = self._merge_results(fields, llm_fields)
            except Exception:
                llm_fields, relationships, summary = fields, [], ""
        else:
            relationships, summary = [], "（规则引擎推断）"
        
        # Step 3: 构建 SchemaDescriptor
        return SchemaDescriptor(
            format=self._detect_format(data_profile.source_name),
            shape={"rows": data_profile.row_count, "columns": data_profile.col_count},
            fields=fields,
            relationships=relationships,
            llm_summary=summary,
        )
    
    def _rule_based_infer(self, df: pd.DataFrame) -> List[FieldDescriptor]:
        """基于规则的字段推断"""
        fields = []
        
        for col in df.columns:
            series = df[col]
            dtype = str(series.dtype)
            
            # 判断逻辑类型
            logical_type = self._infer_logical_type(series, dtype)
            
            # 判断角色
            role = self._infer_role(col, logical_type, series)
            
            # 置信度
            confidence = 0.7  # 规则引擎默认置信度
            
            # 样本值
            sample_values = series.dropna().head(3).tolist()
            
            fields.append(FieldDescriptor(
                name=str(col),
                physical_type=dtype,
                logical_type=logical_type,
                semantic_meaning="",  # LLM 填充
                role=role,
                confidence=confidence,
                sample_values=sample_values,
            ))
        
        return fields
    
    def _infer_logical_type(self, series: pd.Series, dtype: str) -> str:
        """推断逻辑类型"""
        if 'datetime' in dtype:
            return "datetime"
        if 'int' in dtype or 'float' in dtype:
            # 检查是否是布尔值（0/1）
            unique_vals = set(series.dropna().unique())
            if unique_vals <= {0, 1} or unique_vals <= {0.0, 1.0}:
                return "boolean"
            return "numeric"
        if 'bool' in dtype:
            return "boolean"
        
        # 对象类型 — 先过滤掉不可哈希的类型（dict, list 等嵌套结构）
        try:
            hashable_series = series.apply(lambda x: x if not isinstance(x, (dict, list, tuple, set)) else None)
            nunique = hashable_series.nunique()
            total = len(series)
            ratio = nunique / total if total > 0 else 0
        except Exception:
            # 如果 still 失败，回退到字符串化
            nunique = series.astype(str).nunique()
            total = len(series)
            ratio = nunique / total if total > 0 else 0
        
        # 尝试日期转换
        try:
            pd.to_datetime(series, errors='raise')
            return "datetime"
        except Exception:
            pass
        
        # ID 特征：唯一值占比极高
        if ratio > 0.95 and total > 10:
            return "id"
        
        # 类别特征：唯一值较少
        if nunique <= 20 or (total > 100 and ratio < 0.05):
            return "categorical"
        
        # 默认文本
        return "text"
    
    def _infer_role(self, col_name: str, logical_type: str, series: pd.Series) -> FieldRole:
        """基于规则推断字段角色"""
        col_lower = col_name.lower()
        
        # 时间轴
        for keyword in _RULE_ROLE_MAPPING["time_axis"]:
            if keyword in col_lower:
                return FieldRole.TIME_AXIS
        if logical_type == "datetime":
            return FieldRole.TIME_AXIS
        
        # 标识符
        for keyword in _RULE_ROLE_MAPPING["identifier"]:
            if keyword in col_lower:
                return FieldRole.IDENTIFIER
        if logical_type == "id":
            return FieldRole.IDENTIFIER
        
        # 度量值
        for keyword in _RULE_ROLE_MAPPING["measure"]:
            if keyword in col_lower:
                return FieldRole.MEASURE
        if logical_type == "numeric":
            return FieldRole.MEASURE
        
        # 分类维度
        if logical_type == "categorical":
            return FieldRole.DIMENSION
        
        # 文本
        if logical_type == "text":
            return FieldRole.TEXT
        
        return FieldRole.UNKNOWN
    
    def _llm_enhance(self, df: pd.DataFrame, source_name: str, 
                     rule_fields: List[FieldDescriptor]) -> tuple:
        """使用 LLM 增强 Schema 理解"""
        
        # 构建字段样本（前3行的字符串表示）
        sample_rows = df.head(3).to_string()
        field_samples = f"列名: {', '.join(df.columns)}\n\n样本数据:\n{sample_rows}"
        
        prompt = self.prompt_template.format(
            source_name=source_name,
            row_count=len(df),
            column_count=len(df.columns),
            field_samples=field_samples
        )
        
        response = self.llm.chat([
            {"role": "system", "content": "你是一个数据语义分析专家。请严格输出 JSON 格式。"},
            {"role": "user", "content": prompt}
        ], temperature=0.2)
        
        data = self._extract_json(response)
        
        # 解析字段
        llm_fields = []
        for f_data in data.get("fields", []):
            llm_fields.append(FieldDescriptor(
                name=f_data["name"],
                physical_type="unknown",  # 保持规则推断的物理类型
                logical_type=f_data.get("logical_type", "unknown"),
                semantic_meaning=f_data.get("semantic_meaning", ""),
                role=FieldRole(f_data.get("role", "unknown")),
                confidence=0.9,  # LLM 结果置信度更高
                sample_values=[],
            ))
        
        relationships = data.get("relationships", [])
        summary = data.get("llm_summary", "")
        
        return llm_fields, relationships, summary
    
    def _merge_results(self, rule_fields: List[FieldDescriptor],
                       llm_fields: List[FieldDescriptor]) -> List[FieldDescriptor]:
        """合并规则和 LLM 结果（LLM 优先）"""
        llm_field_map = {f.name: f for f in llm_fields}
        
        merged = []
        for rf in rule_fields:
            lf = llm_field_map.get(rf.name)
            if lf and lf.confidence > rf.confidence:
                # LLM 置信度更高，使用 LLM 结果但保留物理类型
                merged.append(FieldDescriptor(
                    name=rf.name,
                    physical_type=rf.physical_type,
                    logical_type=lf.logical_type or rf.logical_type,
                    semantic_meaning=lf.semantic_meaning or rf.semantic_meaning,
                    role=lf.role if lf.role != FieldRole.UNKNOWN else rf.role,
                    confidence=lf.confidence,
                    sample_values=rf.sample_values,
                ))
            else:
                merged.append(rf)
        
        return merged
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从 LLM 响应中提取 JSON"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    
    @staticmethod
    def _detect_format(source_name: str) -> str:
        """根据文件名推断格式"""
        suffix = source_name.split(".")[-1].lower() if "." in source_name else ""
        format_map = {
            "csv": "csv", "xlsx": "excel", "xls": "excel",
            "json": "json", "jsonl": "json_lines", "parquet": "parquet",
            "db": "sqlite", "sqlite": "sqlite", "sqlite3": "sqlite",
        }
        if suffix in format_map:
            return format_map[suffix]
        if source_name.startswith("http"):
            return "rest_api"
        return "unknown"


__all__ = ["SchemaEngine"]
