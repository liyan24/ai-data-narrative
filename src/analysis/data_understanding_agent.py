"""
数据理解智能体 — 用大模型理解数据的业务含义

在数据分析之前，先理解：
1. 每个表头/列名的业务含义
2. 数据所属的业务场景（电商、金融、医疗等）
3. 列之间的关系（主键、时间轴、度量、维度等）
4. 数据的质量和结构特征

输出被 SkillDirector 和 NarrativeDirector 使用，影响技能选择和叙事策略。
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import numpy as np

from src.llm_client import LLMClient, get_llm_client


@dataclass
class ColumnUnderstanding:
    """单列的业务理解"""
    name: str                          # 列名
    business_meaning: str              # 业务含义（中文）
    data_type: str                     # 数据类型: numeric / categorical / datetime / text / id
    business_role: str                   # 业务角色: metric / dimension / time_axis / identifier / foreign_key / label
    sample_values: List[Any]           # 样本值（前5个）
    statistics: Dict[str, Any] = field(default_factory=dict)  # 统计摘要
    quality_issues: List[str] = field(default_factory=list)  # 质量问题
    suggested_aggregations: List[str] = field(default_factory=list)  # 建议聚合方式


@dataclass
class DataUnderstandingResult:
    """数据理解完整结果"""
    source_name: str
    business_domain: str               # 业务领域: 电商/金融/医疗/教育/物流等
    business_scenario: str               # 具体场景: 销售分析/库存管理/用户行为等
    table_description: str               # 整体数据描述
    columns: List[ColumnUnderstanding] # 各列理解
    relationships: List[Dict[str, str]]  # 列关系 [{"from": "order_id", "to": "product_id", "type": "一对多"}]
    key_metrics: List[str]             # 核心指标列
    key_dimensions: List[str]          # 核心维度列
    time_column: Optional[str] = None  # 时间列
    id_column: Optional[str] = None    # ID列
    total_rows: int = 0
    total_columns: int = 0


_DEFAULT_DATA_UNDERSTANDING_PROMPT = """你是数据理解专家。请根据以下数据样本和统计信息，深入理解这份数据的业务含义。

【数据源】
文件名: {source_name}
总行数: {total_rows}
总列数: {total_columns}

【用户意图】
{user_input}

【列信息】
{column_info}

【样本数据（前5行）】
{sample_data}

【统计摘要】
{statistics}

请输出 JSON 格式：
{{
    "business_domain": "推断的业务领域，如电商、金融、医疗、教育、物流等",
    "business_scenario": "具体业务场景，如销售分析、库存管理、用户行为分析、财务报表等",
    "table_description": "用一段话描述这份数据整体上是什么，包含什么信息，适合做什么分析",
    "columns": [
        {{
            "name": "列名",
            "business_meaning": "这列的业务含义，用通俗易懂的中文解释这个字段代表什么",
            "data_type": "numeric|categorical|datetime|text|id",
            "business_role": "metric(度量/指标)|dimension(维度/分类)|time_axis(时间轴)|identifier(标识符)|foreign_key(外键)|label(标签/状态)",
            "sample_values": ["值1", "值2"],
            "quality_issues": ["如有问题描述，如缺失率30%"],
            "suggested_aggregations": ["sum", "mean", "count"]
        }}
    ],
    "relationships": [
        {{
            "from": "列A",
            "to": "列B",
            "type": "关系类型，如一对多、时间序列、关联"
        }}
    ],
    "key_metrics": ["核心指标列名，如销售额、订单量"],
    "key_dimensions": ["核心维度列名，如地区、品类、时间"],
    "time_column": "时间列名，如无则留空",
    "id_column": "主键/ID列名，如无则留空"
}}

要求：
1. 业务含义必须准确、具体，不要泛泛而谈
2. 根据列名和样本数据推断真实的业务含义（如'amount'在电商数据中是'订单金额'）
3. 识别数据的业务场景，帮助后续分析决策
4. 指出数据质量问题（如缺失值、异常值、格式问题）
5. 建议每列的聚合方式（适合求和、平均、计数等）
6. 中文撰写，通俗易懂
"""


class DataUnderstandingAgent:
    """数据理解智能体 — 理解数据的业务含义"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()
    
    def analyze(self, df: pd.DataFrame, source_name: str = "unknown",
                user_input: Optional[str] = None,
                schema: Any = None) -> DataUnderstandingResult:
        """
        分析数据并理解其业务含义
        
        如果 LLM 不可用，返回基于规则的理解结果
        """
        
        # 1. 构建列信息
        column_info = self._build_column_info(df)
        
        # 2. 样本数据（前5行）
        sample_data = df.head(5).to_dict(orient='records')
        
        # 3. 统计摘要
        statistics = self._build_statistics(df)
        
        # 4. LLM 分析
        if self.llm and self.llm.api_key:
            try:
                prompt = _DEFAULT_DATA_UNDERSTANDING_PROMPT.format(
                    source_name=source_name,
                    total_rows=len(df),
                    total_columns=len(df.columns),
                    user_input=user_input or "未指定用户意图",
                    column_info=json.dumps(column_info, ensure_ascii=False, indent=2),
                    sample_data=json.dumps(sample_data, ensure_ascii=False, indent=2, default=str),
                    statistics=json.dumps(statistics, ensure_ascii=False, indent=2, default=str),
                )
                
                response = self.llm.chat([
                    {"role": "system", "content": "你是数据理解专家。请严格输出 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ], temperature=0.3)
                
                data = self._extract_json(response)
                
                return self._parse_llm_result(data, df, source_name)
            except Exception as e:
                # LLM 失败，回退到规则
                pass
        
        # LLM 不可用，回退到规则生成
        return self._rule_based_understanding(df, source_name, user_input)
    
    def _build_column_info(self, df: pd.DataFrame) -> List[Dict]:
        """构建列信息"""
        info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            unique = df[col].nunique()
            null_count = df[col].isna().sum()
            null_pct = round(null_count / len(df) * 100, 1)
            
            col_info = {
                "name": col,
                "dtype": dtype,
                "unique_count": int(unique),
                "null_count": int(null_count),
                "null_pct": null_pct,
                "sample": [str(v) for v in df[col].dropna().head(3).tolist()],
            }
            
            # 数值列额外统计
            if np.issubdtype(df[col].dtype, np.number):
                col_info.update({
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                })
            
            info.append(col_info)
        return info
    
    def _build_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """构建统计摘要"""
        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": [c for c in df.columns if np.issubdtype(df[c].dtype, np.number)],
            "categorical_columns": [c for c in df.columns if df[c].dtype == object],
            "datetime_columns": [c for c in df.columns if 'datetime' in str(df[c].dtype)],
        }
        
        # 数值列统计
        for col in stats["numeric_columns"]:
            stats[f"{col}_stats"] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
            }
        
        # 分类列统计
        for col in stats["categorical_columns"]:
            top = df[col].value_counts().head(3)
            stats[f"{col}_top"] = {str(k): int(v) for k, v in top.items()}
        
        return stats
    
    def _parse_llm_result(self, data: Dict, df: pd.DataFrame, source_name: str) -> DataUnderstandingResult:
        """解析 LLM 返回的 JSON"""
        columns = []
        for col_data in data.get("columns", []):
            col_name = col_data.get("name", "")
            if col_name not in df.columns:
                continue
            
            columns.append(ColumnUnderstanding(
                name=col_name,
                business_meaning=col_data.get("business_meaning", ""),
                data_type=col_data.get("data_type", "unknown"),
                business_role=col_data.get("business_role", "unknown"),
                sample_values=df[col_name].dropna().head(5).tolist(),
                statistics=self._build_column_stats(df[col_name]),
                quality_issues=col_data.get("quality_issues", []),
                suggested_aggregations=col_data.get("suggested_aggregations", []),
            ))
        
        return DataUnderstandingResult(
            source_name=source_name,
            business_domain=data.get("business_domain", "未知领域"),
            business_scenario=data.get("business_scenario", "未知场景"),
            table_description=data.get("table_description", ""),
            columns=columns,
            relationships=data.get("relationships", []),
            key_metrics=data.get("key_metrics", []),
            key_dimensions=data.get("key_dimensions", []),
            time_column=data.get("time_column") or None,
            id_column=data.get("id_column") or None,
            total_rows=len(df),
            total_columns=len(df.columns),
        )
    
    def _build_column_stats(self, series: pd.Series) -> Dict[str, Any]:
        """构建单列统计"""
        stats = {
            "count": int(series.count()),
            "null_count": int(series.isna().sum()),
            "null_pct": round(series.isna().sum() / len(series) * 100, 1),
            "unique_count": int(series.nunique()),
        }
        
        if np.issubdtype(series.dtype, np.number):
            stats.update({
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std": float(series.std()),
            })
        
        return stats
    
    def _rule_based_understanding(self, df: pd.DataFrame, source_name: str,
                                   user_input: Optional[str]) -> DataUnderstandingResult:
        """基于规则的数据理解（LLM 不可用时回退）"""
        
        # 推断业务领域
        domain = self._infer_domain(df, source_name, user_input)
        
        columns = []
        for col in df.columns:
            col_lower = str(col).lower()
            
            # 推断数据类型
            if np.issubdtype(df[col].dtype, np.number):
                data_type = "numeric"
            elif 'datetime' in str(df[col].dtype):
                data_type = "datetime"
            else:
                data_type = "categorical"
            
            # 推断业务角色
            if any(k in col_lower for k in ['date', 'time', '日期', '时间']):
                role = "time_axis"
            elif any(k in col_lower for k in ['id', '编号', '序号']):
                role = "identifier"
            elif any(k in col_lower for k in ['amount', 'price', 'sales', 'revenue', 'sum', 'total', '金额', '价格', '销售额', '收入']):
                role = "metric"
            elif any(k in col_lower for k in ['category', 'region', 'type', 'status', '品类', '地区', '类型', '状态']):
                role = "dimension"
            else:
                role = "metric" if data_type == "numeric" else "dimension"
            
            # 推断业务含义
            meaning_map = {
                'amount': '订单金额/交易金额', 'price': '单价/价格', 'sales': '销售额',
                'quantity': '数量/销量', 'count': '计数', 'revenue': '收入',
                'date': '日期', 'time': '时间', 'datetime': '日期时间',
                'category': '品类/类别', 'region': '地区/区域', 'product': '产品',
                'customer': '客户', 'order': '订单', 'status': '状态',
                'id': '标识符/ID', 'name': '名称', 'type': '类型',
            }
            meaning = meaning_map.get(col_lower, f"{'数值' if data_type == 'numeric' else '分类'}字段")
            
            # 建议聚合
            aggs = []
            if role == "metric" and data_type == "numeric":
                aggs = ["sum", "mean", "count"]
            elif role == "dimension":
                aggs = ["count", "distinct_count"]
            elif role == "time_axis":
                aggs = ["count"]
            
            columns.append(ColumnUnderstanding(
                name=col,
                business_meaning=meaning,
                data_type=data_type,
                business_role=role,
                sample_values=df[col].dropna().head(5).tolist(),
                statistics=self._build_column_stats(df[col]),
                suggested_aggregations=aggs,
            ))
        
        # 识别关键列
        key_metrics = [c.name for c in columns if c.business_role == "metric"]
        key_dimensions = [c.name for c in columns if c.business_role == "dimension"]
        time_col = next((c.name for c in columns if c.business_role == "time_axis"), None)
        id_col = next((c.name for c in columns if c.business_role == "identifier"), None)
        
        return DataUnderstandingResult(
            source_name=source_name,
            business_domain=domain,
            business_scenario="数据分析",
            table_description=f"这是一份{domain}数据，包含{len(df.columns)}个字段，共{len(df)}条记录。",
            columns=columns,
            relationships=[],
            key_metrics=key_metrics,
            key_dimensions=key_dimensions,
            time_column=time_col,
            id_column=id_col,
            total_rows=len(df),
            total_columns=len(df.columns),
        )
    
    def _infer_domain(self, df: pd.DataFrame, source_name: str, user_input: Optional[str]) -> str:
        """推断业务领域"""
        text = f"{source_name} {user_input or ''} {' '.join(df.columns.astype(str))}"
        text_lower = text.lower()
        
        domain_keywords = {
            "电商": ['sales', 'order', 'product', 'customer', 'price', 'quantity', 'amount', 'revenue', 'purchase', 'cart', 'shop', 'store', '销售', '订单', '产品', '客户', '价格', '购买'],
            "金融": ['finance', 'stock', 'trading', 'investment', 'profit', 'loss', 'risk', 'return', 'asset', 'portfolio', '金融', '股票', '交易', '投资', '收益', '风险'],
            "医疗": ['patient', 'diagnosis', 'treatment', 'medical', 'health', 'hospital', 'doctor', 'disease', '患者', '诊断', '治疗', '医疗', '健康', '医院'],
            "教育": ['student', 'course', 'grade', 'score', 'exam', 'school', 'teacher', 'education', '学生', '课程', '成绩', '考试', '学校', '教育'],
            "物流": ['delivery', 'shipment', 'transport', 'warehouse', 'logistics', 'shipping', 'route', '配送', '物流', '运输', '仓库', '发货'],
            "人力资源": ['employee', 'salary', 'hr', 'recruitment', 'performance', 'department', '员工', '薪资', '招聘', '绩效', '部门'],
        }
        
        scores = {domain: sum(1 for k in keywords if k in text_lower) for domain, keywords in domain_keywords.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "通用业务"
    
    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())


__all__ = ["DataUnderstandingAgent", "DataUnderstandingResult", "ColumnUnderstanding"]
