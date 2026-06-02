"""
数据输入层 — 多格式文件解析与数据类型推断
"""

import json
import warnings
from pathlib import Path
from typing import Union, Dict, List, Any, Optional
import pandas as pd
import numpy as np
from src.config import INPUT_CONFIG

warnings.filterwarnings("ignore", category=UserWarning)


class DataTypeInferencer:
    """智能数据类型推断器"""
    
    # 类型优先级（从具体到模糊）
    TYPE_PRIORITY = ["datetime", "numeric", "categorical", "text", "boolean", "id"]
    
    @classmethod
    def infer(cls, series: pd.Series) -> Dict[str, Any]:
        """
        推断单个列的数据类型
        
        Returns:
            {
                "type": "numeric" | "categorical" | "datetime" | "text" | "boolean" | "id",
                "subtype": "integer" | "float" | "date" | "time" | "datetime" | "string",
                "confidence": float,
                "details": dict
            }
        """
        series = series.dropna()
        if len(series) == 0:
            return {"type": "unknown", "subtype": None, "confidence": 0.0, "details": {}}
        
        # 尝试布尔型
        bool_result = cls._check_boolean(series)
        if bool_result:
            return bool_result
        
        # 尝试 ID 型
        id_result = cls._check_id(series)
        if id_result:
            return id_result
        
        # 尝试日期时间
        dt_result = cls._check_datetime(series)
        if dt_result:
            return dt_result
        
        # 尝试数值型
        num_result = cls._check_numeric(series)
        if num_result:
            return num_result
        
        # 尝试类别型
        cat_result = cls._check_categorical(series)
        if cat_result:
            return cat_result
        
        # 默认文本型
        return {
            "type": "text",
            "subtype": "string",
            "confidence": 0.7,
            "details": {"unique_ratio": series.nunique() / len(series), "avg_length": series.astype(str).str.len().mean()}
        }
    
    @staticmethod
    def _check_boolean(series: pd.Series) -> Optional[Dict]:
        """检查是否为布尔类型"""
        unique_vals = set(series.dropna().astype(str).str.lower().unique())
        bool_sets = [
            {"true", "false"}, {"1", "0"}, {"yes", "no"}, {"y", "n"}, 
            {"是", "否"}, {"真", "假"}, {"on", "off"}
        ]
        if any(unique_vals <= bs for bs in bool_sets):
            return {
                "type": "boolean",
                "subtype": "bool",
                "confidence": 0.95,
                "details": {"values": list(unique_vals)}
            }
        return None
    
    @staticmethod
    def _check_id(series: pd.Series) -> Optional[Dict]:
        """检查是否为 ID 列（唯一值占比高，无明显规律，且为字符串类型）"""
        # 排除数值类型 — 数值列不应该是 ID
        if pd.api.types.is_numeric_dtype(series.dtype):
            return None
        
        # 排除日期格式 — 日期字符串通常长度固定且唯一
        sample_str = str(series.iloc[0]) if len(series) > 0 else ""
        # 简单日期格式检测：包含数字和连字符/斜杠/冒号
        import re
        if re.match(r'\d{4}[\-/]\d{2}[\-/]\d{2}', sample_str):
            return None
        
        nunique = series.nunique()
        total = len(series)
        if total > 0 and nunique / total > 0.95:
            avg_len = series.astype(str).str.len().mean()
            if avg_len > 5:  # 长字符串通常是 ID
                return {
                    "type": "id",
                    "subtype": "string_id",
                    "confidence": 0.85,
                    "details": {"unique_ratio": nunique / total, "avg_length": avg_len}
                }
        return None
    
    @staticmethod
    def _check_datetime(series: pd.Series) -> Optional[Dict]:
        """检查是否为日期时间类型"""
        # 数值类型直接跳过 — 避免整数被转换为时间戳
        if pd.api.types.is_numeric_dtype(series.dtype):
            return None
        
        try:
            converted = pd.to_datetime(series, errors='coerce')
            valid_ratio = converted.notna().sum() / len(series)
            if valid_ratio > 0.8:
                # 判断是日期、时间还是日期时间
                has_time = (converted.dt.hour != 0).any() | (converted.dt.minute != 0).any()
                has_date = (converted.dt.year != 1970).any()
                
                if has_time and has_date:
                    subtype = "datetime"
                elif has_time:
                    subtype = "time"
                else:
                    subtype = "date"
                
                return {
                    "type": "datetime",
                    "subtype": subtype,
                    "confidence": valid_ratio,
                    "details": {
                        "range": [str(converted.min()), str(converted.max())],
                        "valid_ratio": valid_ratio
                    }
                }
        except Exception:
            pass
        return None
    
    @staticmethod
    def _check_numeric(series: pd.Series) -> Optional[Dict]:
        """检查是否为数值类型"""
        try:
            converted = pd.to_numeric(series, errors='coerce')
            valid_ratio = converted.notna().sum() / len(series)
            if valid_ratio > 0.8:
                is_integer = (converted.dropna() % 1 == 0).all()
                return {
                    "type": "numeric",
                    "subtype": "integer" if is_integer else "float",
                    "confidence": valid_ratio,
                    "details": {
                        "min": float(converted.min()),
                        "max": float(converted.max()),
                        "mean": float(converted.mean()),
                        "std": float(converted.std()),
                        "valid_ratio": valid_ratio
                    }
                }
        except Exception:
            pass
        return None
    
    @staticmethod
    def _check_categorical(series: pd.Series) -> Optional[Dict]:
        """检查是否为类别类型"""
        nunique = series.nunique()
        total = len(series)
        ratio = nunique / total if total > 0 else 0
        
        # 类别特征：唯一值较少（通常 < 20 或占比 < 5%）
        if nunique <= 20 or (total > 100 and ratio < 0.05):
            value_counts = series.value_counts().head(10).to_dict()
            return {
                "type": "categorical",
                "subtype": "string" if series.dtype == object else "numeric",
                "confidence": 0.9 if nunique <= 20 else 0.75,
                "details": {
                    "unique_count": nunique,
                    "unique_ratio": ratio,
                    "top_values": {str(k): int(v) for k, v in value_counts.items()}
                }
            }
        return None


class DataLoader:
    """多格式数据加载器"""
    
    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "DataProfile":
        """
        加载数据文件并返回数据画像
        
        Args:
            file_path: 文件路径
            
        Returns:
            DataProfile 对象
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        suffix = file_path.suffix.lower()
        
        if suffix == ".csv":
            df = cls._load_csv(file_path)
        elif suffix in [".xlsx", ".xls"]:
            df = cls._load_excel(file_path)
        elif suffix == ".json":
            df = cls._load_json(file_path)
        elif suffix == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")
        
        return DataProfile(df, file_path.name)
    
    @staticmethod
    def _load_csv(file_path: Path) -> pd.DataFrame:
        """加载 CSV 文件，自动探测编码"""
        for encoding in INPUT_CONFIG["encoding_fallback"]:
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("无法识别文件编码")
    
    @staticmethod
    def _load_excel(file_path: Path) -> pd.DataFrame:
        """加载 Excel 文件"""
        return pd.read_excel(file_path, engine="openpyxl")
    
    @staticmethod
    def _load_json(file_path: Path) -> pd.DataFrame:
        """加载 JSON 文件（支持对象列表和行式 JSON）"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            # 尝试处理嵌套结构
            return pd.json_normalize(data)
        else:
            raise ValueError("JSON 格式不支持")


class DataProfile:
    """数据画像 — 包含 DataFrame 和类型推断结果"""
    
    def __init__(self, df: pd.DataFrame, source_name: str = "unknown"):
        self.df = df
        self.source_name = source_name
        self.row_count = len(df)
        self.col_count = len(df.columns)
        self.column_profiles: Dict[str, Dict] = {}
        
        # 推断每列类型
        for col in df.columns:
            self.column_profiles[col] = DataTypeInferencer.infer(df[col])
    
    def get_column_types(self) -> Dict[str, str]:
        """获取列名到类型的映射"""
        return {col: info["type"] for col, info in self.column_profiles.items()}
    
    def get_numeric_columns(self) -> List[str]:
        """获取数值列"""
        return [col for col, info in self.column_profiles.items() if info["type"] == "numeric"]
    
    def get_categorical_columns(self) -> List[str]:
        """获取类别列"""
        return [col for col, info in self.column_profiles.items() if info["type"] == "categorical"]
    
    def get_datetime_columns(self) -> List[str]:
        """获取日期时间列"""
        return [col for col, info in self.column_profiles.items() if info["type"] == "datetime"]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取数据摘要信息"""
        type_counts = {}
        for info in self.column_profiles.values():
            t = info["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "source": self.source_name,
            "rows": self.row_count,
            "columns": self.col_count,
            "type_distribution": type_counts,
            "missing_summary": {
                col: int(self.df[col].isna().sum()) 
                for col in self.df.columns 
                if self.df[col].isna().sum() > 0
            },
            "column_profiles": self.column_profiles
        }
    
    def to_markdown(self) -> str:
        """输出数据摘要 Markdown"""
        summary = self.get_summary()
        lines = [
            f"## 数据概览: {summary['source']}",
            "",
            f"- **行数**: {summary['rows']:,}",
            f"- **列数**: {summary['columns']}",
            "",
            "### 列类型分布",
            "",
        ]
        
        for t, count in summary["type_distribution"].items():
            lines.append(f"- **{t}**: {count} 列")
        
        lines.extend(["", "### 各列详情", ""])
        
        for col, profile in self.column_profiles.items():
            dt = profile["type"]
            st = profile.get("subtype", "")
            conf = profile.get("confidence", 0)
            details = profile.get("details", {})
            
            lines.append(f"- **{col}** (`{dt}/{st}`, 置信度 {conf:.0%})")
            
            if dt == "numeric" and "min" in details:
                lines.append(f"  - 范围: {details['min']:.2f} ~ {details['max']:.2f}, 均值: {details['mean']:.2f}")
            elif dt == "categorical" and "top_values" in details:
                top = ", ".join([f"{k}({v})" for k, v in list(details["top_values"].items())[:3]])
                lines.append(f"  - 高频值: {top}")
            elif dt == "datetime" and "range" in details:
                lines.append(f"  - 范围: {details['range'][0]} ~ {details['range'][1]}")
        
        return "\n".join(lines)
