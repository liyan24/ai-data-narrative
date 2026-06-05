"""
AI数据叙事系统 — 全局配置
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（项目根目录）
PROJECT_ROOT = Path(__file__).parent.parent
dotenv_path = PROJECT_ROOT / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()  # 尝试从环境或其他位置加载

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# 技能目录
SKILLS_DIR = PROJECT_ROOT / "skills"
BUILTIN_SKILLS_DIR = SKILLS_DIR / "builtin"
CUSTOM_SKILLS_DIR = SKILLS_DIR / "custom"

# 确保目录存在
for d in [DATA_DIR, OUTPUT_DIR, PROMPTS_DIR, TEMPLATES_DIR, SKILLS_DIR, BUILTIN_SKILLS_DIR, CUSTOM_SKILLS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 大模型配置（兼容 OpenAI API，优先从 .env 读取）
LLM_CONFIG = {
    "base_url": os.getenv("LLM_BASE_URL", "https://api.moonshot.cn/v1"),
    "api_key": os.getenv("LLM_API_KEY", ""),
    "model": os.getenv("LLM_MODEL", "kimi-latest"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
}

# LLM 缓存配置
LLM_CACHE_CONFIG = {
    "enabled": os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true",
    "dir": PROJECT_ROOT / "cache" / "llm",
    "ttl_seconds": int(os.getenv("LLM_CACHE_TTL", "3600")),
}
LLM_CACHE_CONFIG["dir"].mkdir(parents=True, exist_ok=True)

# 技能执行器配置
SKILL_EXECUTOR_CONFIG = {
    "max_workers": int(os.getenv("SKILL_MAX_WORKERS", "4")),
    "enable_parallel": os.getenv("SKILL_PARALLEL", "true").lower() == "true",
}

# 可视化配置（优先从 .env 读取）
VIZ_CONFIG = {
    "default_width": int(os.getenv("VIZ_WIDTH", "800")),
    "default_height": int(os.getenv("VIZ_HEIGHT", "500")),
    "dpi": int(os.getenv("VIZ_DPI", "150")),
    "color_palette": [
        "#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
        "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"
    ],
    "theme": "light",
    "font_family": os.getenv("VIZ_FONT", "SimHei"),
    "font_size": int(os.getenv("VIZ_FONT_SIZE", "12")),
}

# 报告配置（优先从 .env 读取）
REPORT_CONFIG = {
    "default_format": os.getenv("REPORT_FORMAT", "html"),
    "supported_formats": ["html", "markdown", "pdf"],
    "title": os.getenv("REPORT_TITLE", "AI数据叙事报告"),
    "author": os.getenv("REPORT_AUTHOR", "AI数据叙事系统"),
}

# 数据输入配置（优先从 .env 读取）
_encoding_fallback = os.getenv("ENCODING_FALLBACK", "utf-8,gbk,gb2312,latin1")
INPUT_CONFIG = {
    "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "50")),
    "supported_formats": [".csv", ".xlsx", ".xls", ".json", ".jsonl", ".parquet", ".db", ".sqlite", ".sqlite3"],
    "max_rows_preview": 100,
    "encoding_fallback": [e.strip() for e in _encoding_fallback.split(",")],
}
