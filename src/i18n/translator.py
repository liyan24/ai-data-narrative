"""
国际化支持 — 多语言翻译

使用方式:
    from src.i18n.translator import Translator
    
    t = Translator("zh")
    print(t("hello"))  # 你好
"""

from typing import Dict, Optional
from pathlib import Path
import json


class Translator:
    """翻译器"""
    
    DEFAULT_LOCALE = "zh"
    
    TRANSLATIONS = {
        "zh": {
            "hello": "你好",
            "data_overview": "数据概览",
            "quality_check": "质量检查",
            "statistics": "统计特征",
            "insights": "数据洞察",
            "analysis": "多维度分析",
            "narrative": "叙事策略",
            "charts": "可视化图表",
            "story": "数据故事",
            "report": "分析报告",
            "publish": "平台发布",
            "settings": "设置",
            "upload": "上传",
            "download": "下载",
            "processing": "处理中",
            "success": "成功",
            "error": "错误",
            "warning": "警告",
            "info": "信息",
            "loading": "加载中",
            "done": "完成",
            "cancel": "取消",
            "save": "保存",
            "close": "关闭",
            "row_count": "行数",
            "column_count": "列数",
            "memory_usage": "内存占用",
            "data_quality": "数据质量",
            "score": "评分",
            "grade": "等级",
            "issues": "问题",
            "trend": "趋势",
            "distribution": "分布",
            "comparison": "对比",
            "relationship": "关系",
            "composition": "构成",
            "anomaly": "异常",
            "critical": "严重",
            "high": "高",
            "medium": "中",
            "low": "低",
            "top_n": "前 N",
            "bottom_n": "后 N",
            "average": "平均",
            "median": "中位数",
            "std": "标准差",
            "min": "最小值",
            "max": "最大值",
            "missing": "缺失",
            "duplicate": "重复",
            "outlier": "异常值",
            "clean": "清洗",
            "auto_clean": "自动清洗",
            "aggressive": "激进模式",
            "advanced_charts": "高级图表",
            "storytelling": "数据故事",
            "platform": "平台",
            "xiaohongshu": "小红书",
            "wechat_mp": "微信公众号",
            "markdown": "Markdown",
            "llm_enhance": "LLM 增强",
            "performance": "性能",
            "memory": "内存",
            "cpu": "CPU",
            "time": "时间",
            "health_check": "健康检查",
            "status": "状态",
            "ok": "正常",
            "failed": "失败",
            "pending": "待处理",
            "published": "已发布",
            "task": "任务",
            "schedule": "调度",
            "daily": "每日",
            "interval": "间隔",
            "plugin": "插件",
            "custom": "自定义",
            "database": "数据库",
            "api": "API",
            "connector": "连接器",
            "prediction": "预测",
            "cluster": "聚类",
            "anomaly_detection": "异常检测",
            "feature_importance": "特征重要性",
            "segment": "分段",
        },
        "en": {
            "hello": "Hello",
            "data_overview": "Data Overview",
            "quality_check": "Quality Check",
            "statistics": "Statistics",
            "insights": "Insights",
            "analysis": "Analysis",
            "narrative": "Narrative",
            "charts": "Charts",
            "story": "Story",
            "report": "Report",
            "publish": "Publish",
            "settings": "Settings",
            "upload": "Upload",
            "download": "Download",
            "processing": "Processing",
            "success": "Success",
            "error": "Error",
            "warning": "Warning",
            "info": "Info",
            "loading": "Loading",
            "done": "Done",
            "cancel": "Cancel",
            "save": "Save",
            "close": "Close",
            "row_count": "Row Count",
            "column_count": "Column Count",
            "memory_usage": "Memory Usage",
            "data_quality": "Data Quality",
            "score": "Score",
            "grade": "Grade",
            "issues": "Issues",
            "trend": "Trend",
            "distribution": "Distribution",
            "comparison": "Comparison",
            "relationship": "Relationship",
            "composition": "Composition",
            "anomaly": "Anomaly",
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "top_n": "Top N",
            "bottom_n": "Bottom N",
            "average": "Average",
            "median": "Median",
            "std": "Std Dev",
            "min": "Min",
            "max": "Max",
            "missing": "Missing",
            "duplicate": "Duplicate",
            "outlier": "Outlier",
            "clean": "Clean",
            "auto_clean": "Auto Clean",
            "aggressive": "Aggressive",
            "advanced_charts": "Advanced Charts",
            "storytelling": "Storytelling",
            "platform": "Platform",
            "xiaohongshu": "Xiaohongshu",
            "wechat_mp": "WeChat MP",
            "markdown": "Markdown",
            "llm_enhance": "LLM Enhance",
            "performance": "Performance",
            "memory": "Memory",
            "cpu": "CPU",
            "time": "Time",
            "health_check": "Health Check",
            "status": "Status",
            "ok": "OK",
            "failed": "Failed",
            "pending": "Pending",
            "published": "Published",
            "task": "Task",
            "schedule": "Schedule",
            "daily": "Daily",
            "interval": "Interval",
            "plugin": "Plugin",
            "custom": "Custom",
            "database": "Database",
            "api": "API",
            "connector": "Connector",
            "prediction": "Prediction",
            "cluster": "Cluster",
            "anomaly_detection": "Anomaly Detection",
            "feature_importance": "Feature Importance",
            "segment": "Segment",
        }
    }
    
    def __init__(self, locale: str = None):
        self.locale = locale or self.DEFAULT_LOCALE
        self._dict = self.TRANSLATIONS.get(self.locale, self.TRANSLATIONS[self.DEFAULT_LOCALE])
    
    def __call__(self, key: str, default: str = None) -> str:
        """获取翻译"""
        return self._dict.get(key, default or key)
    
    def set_locale(self, locale: str):
        """切换语言"""
        self.locale = locale
        self._dict = self.TRANSLATIONS.get(locale, self.TRANSLATIONS[self.DEFAULT_LOCALE])
    
    def available_locales(self) -> list:
        """获取可用语言列表"""
        return list(self.TRANSLATIONS.keys())
    
    def translate_dict(self, data: dict, keys: list = None) -> dict:
        """翻译字典中的特定键"""
        result = data.copy()
        target_keys = keys or list(self._dict.keys())
        for key in target_keys:
            if key in result and isinstance(result[key], str):
                result[key] = self(result[key])
        return result


def _(key: str, locale: str = None) -> str:
    """快捷翻译函数"""
    t = Translator(locale)
    return t(key)
