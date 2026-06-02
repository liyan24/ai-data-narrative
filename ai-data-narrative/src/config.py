"""
AI数据叙事系统 — 全局配置
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# 确保目录存在
for d in [DATA_DIR, OUTPUT_DIR, PROMPTS_DIR, TEMPLATES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 大模型配置（兼容 OpenAI API）
LLM_CONFIG = {
    "base_url": os.getenv("LLM_BASE_URL", "https://api.moonshot.cn/v1"),
    "api_key": os.getenv("LLM_API_KEY", ""),
    "model": os.getenv("LLM_MODEL", "kimi-latest"),
    "temperature": 0.3,
    "max_tokens": 4096,
}

# 可视化配置
VIZ_CONFIG = {
    "default_width": 800,
    "default_height": 500,
    "dpi": 150,
    "color_palette": [
        "#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
        "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"
    ],
    "theme": "light",
    "font_family": "SimHei",  # 中文回退
    "font_size": 12,
}

# 报告配置
REPORT_CONFIG = {
    "default_format": "html",
    "supported_formats": ["html", "markdown", "pdf"],
    "title": "AI数据叙事报告",
    "author": "AI数据叙事系统",
}

# 数据输入配置
INPUT_CONFIG = {
    "max_file_size_mb": 50,
    "supported_formats": [".csv", ".xlsx", ".xls", ".json", ".parquet"],
    "max_rows_preview": 100,
    "encoding_fallback": ["utf-8", "gbk", "gb2312", "latin1"],
}
