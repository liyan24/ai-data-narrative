"""
平台发布适配器 — 小红书 + 微信公众号内容适配

核心能力：
- 小红书：短文本、emoji、关键词、话题标签
- 微信公众号：长图文、标题、摘要、排版
- 内容分段：自动拆分长文为多个短篇
- 封面图推荐：基于图表选择最佳封面
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

import pandas as pd


class Platform(Enum):
    """发布平台"""
    XIAOHONGSHU = "xiaohongshu"      # 小红书
    WECHAT_MP = "wechat_mp"          # 微信公众号
    MARKDOWN = "markdown"            # 通用 Markdown


@dataclass
class PlatformContent:
    """平台内容"""
    platform: Platform
    title: str
    content: str
    summary: str = ""                # 摘要/简介
    hashtags: List[str] = field(default_factory=list)  # 话题标签
    cover_image: str = ""            # 封面图
    word_count: int = 0
    estimated_read_time: int = 0     # 预计阅读时间（分钟）
    sections: List[str] = field(default_factory=list)  # 分段内容


class PlatformAdapter:
    """平台适配器基类"""
    
    def __init__(self, platform: Platform):
        self.platform = platform
    
    def adapt(self, title: str, story_sections: List[Any], 
              insights: List[Any], charts: List[Dict]) -> PlatformContent:
        """适配内容到平台"""
        raise NotImplementedError
    
    def _extract_key_insights(self, insights: List[Any], top_n: int = 5) -> List[str]:
        """提取关键洞察"""
        # 按重要性排序
        def get_severity_value(x):
            severity = getattr(x, 'severity', None)
            if severity is None:
                return 4
            # severity 可能是 Enum 对象或字符串
            if hasattr(severity, 'value'):
                severity = severity.value
            order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            return order.get(severity, 4)
        
        sorted_insights = sorted(insights, key=get_severity_value)
        return [getattr(i, 'title', str(i)) for i in sorted_insights[:top_n]]
    
    def _select_cover_chart(self, charts: List[Dict]) -> Optional[str]:
        """选择最佳封面图"""
        if not charts:
            return None
        # 优先选择趋势图或对比图
        for chart in charts:
            chart_type = chart.get("type", "")
            if chart_type in ["trend", "comparison", "bar", "line"]:
                return chart.get("data", "")
        # 默认选第一个
        return charts[0].get("data", "")


class XiaohongshuAdapter(PlatformAdapter):
    """小红书适配器 — 短文本、emoji、话题标签"""
    
    MAX_WORDS = 1000                 # 小红书正文上限约1000字
    HASHTAG_COUNT = 5                # 推荐话题数量
    
    def __init__(self):
        super().__init__(Platform.XIAOHONGSHU)
        self.emoji_map = {
            "趋势": "📈",
            "对比": "⚖️",
            "分布": "📊",
            "关系": "🔗",
            "构成": "🥧",
            "异常": "🚨",
            "洞察": "💡",
            "数据": "📊",
            "分析": "🔍",
            "报告": "📄",
            "发现": "✨",
            "建议": "💡",
        }
    
    def adapt(self, title: str, story_sections: List[Any],
              insights: List[Any], charts: List[Dict]) -> PlatformContent:
        """适配为小红书内容"""
        # 提取关键洞察
        key_insights = self._extract_key_insights(insights, top_n=3)
        
        # 构建标题
        xhs_title = self._make_title(title)
        
        # 构建正文
        content_parts = []
        
        # 开头钩子
        content_parts.append("💡 今天分享一组数据分析洞察，看看有什么有趣发现！")
        content_parts.append("")
        
        # 核心发现（3条，每条配emoji）
        for i, insight in enumerate(key_insights[:3], 1):
            emoji = self._get_emoji_for_insight(insight)
            content_parts.append(f"{emoji} 发现{i}：{insight}")
            content_parts.append("")
        
        # 数据背景
        content_parts.append("📊 数据规模：")
        # 尝试从 story 中提取数据规模
        for section in story_sections:
            if "数据规模" in getattr(section, 'content', '') or "行" in getattr(section, 'content', ''):
                # 提取数字
                import re
                content_text = getattr(section, 'content', '')
                # 简单提取行数列数
                content_parts.append(content_text[:100])
                break
        content_parts.append("")
        
        # 结尾互动
        content_parts.append("🤔 你觉得哪个发现最有意思？评论区聊聊！")
        content_parts.append("")
        content_parts.append("👆 关注我看更多数据分析故事")
        
        content = "\n".join(content_parts)
        
        # 生成话题标签
        hashtags = self._generate_hashtags(insights, charts)
        
        # 选择封面
        cover = self._select_cover_chart(charts) or ""
        
        # 字数和阅读时间
        word_count = len(content)
        read_time = max(1, word_count // 300)
        
        return PlatformContent(
            platform=Platform.XIAOHONGSHU,
            title=xhs_title,
            content=content,
            summary=f"数据分析发现 {len(key_insights)} 个关键洞察",
            hashtags=hashtags,
            cover_image=cover,
            word_count=word_count,
            estimated_read_time=read_time,
            sections=[content]  # 小红书不分段
        )
    
    def _make_title(self, title: str) -> str:
        """制作小红书标题"""
        # 添加emoji，控制长度
        emoji = "📊"
        # 检查是否已有emoji
        if not any(e in title for e in self.emoji_map.values()):
            title = f"{emoji} {title}"
        
        # 小红书标题建议30字以内
        if len(title) > 30:
            title = title[:27] + "..."
        
        return title
    
    def _get_emoji_for_insight(self, insight: str) -> str:
        """为洞察选择emoji"""
        for keyword, emoji in self.emoji_map.items():
            if keyword in insight:
                return emoji
        return "💡"
    
    def _generate_hashtags(self, insights: List[Any], charts: List[Dict]) -> List[str]:
        """生成话题标签"""
        tags = ["#数据分析", "#数据可视化", "#AI洞察"]
        
        # 从洞察中提取关键词
        for insight in insights[:3]:
            title = getattr(insight, 'title', str(insight))
            # 提取前几个字作为标签
            if len(title) > 4:
                tags.append(f"#{title[:6]}")
        
        # 从图表类型添加
        chart_types = set()
        for chart in charts[:3]:
            chart_type = chart.get("type", "")
            if chart_type:
                chart_types.add(chart_type)
        
        for ct in chart_types:
            type_map = {
                "trend": "#趋势分析",
                "bar": "#柱状图",
                "line": "#折线图",
                "pie": "#饼图",
                "heatmap": "#热力图",
            }
            if ct in type_map:
                tags.append(type_map[ct])
        
        return tags[:self.HASHTAG_COUNT]


class WechatMPAdapter(PlatformAdapter):
    """微信公众号适配器 — 长图文、标题、摘要、排版"""
    
    MAX_WORDS = 20000                # 公众号上限约2万字
    
    def __init__(self):
        super().__init__(Platform.WECHAT_MP)
    
    def adapt(self, title: str, story_sections: List[Any],
              insights: List[Any], charts: List[Dict]) -> PlatformContent:
        """适配为微信公众号内容"""
        # 构建标题
        wechat_title = self._make_title(title)
        
        # 构建正文（Markdown格式）
        content_parts = []
        
        # 引导语
        content_parts.append("> 📊 本文基于真实数据自动生成，通过 AI 分析发现以下关键洞察。")
        content_parts.append("")
        
        # 摘要
        key_insights = self._extract_key_insights(insights, top_n=5)
        content_parts.append("## 📋 核心发现速览")
        content_parts.append("")
        for i, insight in enumerate(key_insights, 1):
            content_parts.append(f"{i}. {insight}")
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        
        # 故事章节
        for section in story_sections:
            section_title = getattr(section, 'title', '分析')
            section_content = getattr(section, 'content', '')
            
            content_parts.append(f"## {section_title}")
            content_parts.append("")
            content_parts.append(section_content)
            content_parts.append("")
        
        # 图表展示
        if charts:
            content_parts.append("## 📈 可视化图表")
            content_parts.append("")
            for i, chart in enumerate(charts[:5], 1):
                content_parts.append(f"**图表 {i}：{chart.get('title', '')}**")
                content_parts.append("")
                content_parts.append(f"![{chart.get('title', '')}](data:image/png;base64,{chart.get('data', '')})")
                content_parts.append("")
        
        # 结尾
        content_parts.append("---")
        content_parts.append("")
        content_parts.append("> 💡 **关于本文**：本文由 AI 数据叙事系统自动生成，结合了统计分析、数据洞察和叙事策略。")
        content_parts.append("> ")
        content_parts.append("> 🔔 **关注我们**：获取更多数据驱动的深度分析！")
        
        content = "\n".join(content_parts)
        
        # 摘要
        summary = f"本文通过 AI 分析发现了 {len(key_insights)} 个关键洞察，"
        if insights:
            summary += f"包括 {key_insights[0]} 等。"
        summary += "点击阅读详细分析。"
        
        # 选择封面
        cover = self._select_cover_chart(charts) or ""
        
        # 字数和阅读时间
        word_count = len(content)
        read_time = max(1, word_count // 400)
        
        # 分段（公众号建议每段不要太长）
        sections = self._split_into_sections(content)
        
        return PlatformContent(
            platform=Platform.WECHAT_MP,
            title=wechat_title,
            content=content,
            summary=summary,
            hashtags=[],
            cover_image=cover,
            word_count=word_count,
            estimated_read_time=read_time,
            sections=sections
        )
    
    def _make_title(self, title: str) -> str:
        """制作公众号标题"""
        # 公众号标题可以较长，但建议有吸引力
        if len(title) < 15:
            title = f"数据分析 | {title}"
        return title
    
    def _split_into_sections(self, content: str, max_section_length: int = 2000) -> List[str]:
        """将内容分段"""
        sections = []
        current = []
        current_length = 0
        
        for line in content.split('\n'):
            line_length = len(line)
            
            if current_length + line_length > max_section_length and current:
                sections.append('\n'.join(current))
                current = [line]
                current_length = line_length
            else:
                current.append(line)
                current_length += line_length
        
        if current:
            sections.append('\n'.join(current))
        
        return sections


class MarkdownAdapter(PlatformAdapter):
    """通用 Markdown 适配器"""
    
    def __init__(self):
        super().__init__(Platform.MARKDOWN)
    
    def adapt(self, title: str, story_sections: List[Any],
              insights: List[Any], charts: List[Dict]) -> PlatformContent:
        """输出通用 Markdown"""
        content_parts = [f"# {title}", ""]
        
        # 生成时间
        content_parts.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        content_parts.append("")
        
        # 故事章节
        for section in story_sections:
            section_title = getattr(section, 'title', '分析')
            section_content = getattr(section, 'content', '')
            content_parts.append(f"## {section_title}")
            content_parts.append("")
            content_parts.append(section_content)
            content_parts.append("")
        
        # 图表
        if charts:
            content_parts.append("## 可视化图表")
            content_parts.append("")
            for chart in charts:
                content_parts.append(f"### {chart.get('title', '')}")
                content_parts.append("")
                content_parts.append(f"![{chart.get('title', '')}](data:image/png;base64,{chart.get('data', '')})")
                content_parts.append("")
        
        content = "\n".join(content_parts)
        
        return PlatformContent(
            platform=Platform.MARKDOWN,
            title=title,
            content=content,
            summary="",
            hashtags=[],
            cover_image="",
            word_count=len(content),
            estimated_read_time=max(1, len(content) // 500),
            sections=[content]
        )


class PublishingOrchestrator:
    """发布编排器 — 统一调度各平台适配"""
    
    def __init__(self):
        self.adapters = {
            Platform.XIAOHONGSHU: XiaohongshuAdapter(),
            Platform.WECHAT_MP: WechatMPAdapter(),
            Platform.MARKDOWN: MarkdownAdapter(),
        }
    
    def publish_to_all(self, title: str, story_sections: List[Any],
                      insights: List[Any], charts: List[Dict]) -> Dict[Platform, PlatformContent]:
        """
        生成所有平台的内容
        
        Returns:
            {平台: 内容, ...}
        """
        results = {}
        for platform, adapter in self.adapters.items():
            try:
                content = adapter.adapt(title, story_sections, insights, charts)
                results[platform] = content
            except Exception as e:
                results[platform] = None
                print(f"[WARN] {platform.value} 适配失败: {e}")
        
        return results
    
    def publish_to(self, platform: Platform, title: str, story_sections: List[Any],
                  insights: List[Any], charts: List[Dict]) -> Optional[PlatformContent]:
        """生成指定平台的内容"""
        adapter = self.adapters.get(platform)
        if not adapter:
            return None
        return adapter.adapt(title, story_sections, insights, charts)
    
    def save_platform_content(self, content: PlatformContent, output_dir: Path) -> Path:
        """保存平台内容到文件"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{content.platform.value}_{timestamp}.md"
        filepath = output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {content.title}\n\n")
            f.write(f"**平台**: {content.platform.value}\n\n")
            f.write(f"**字数**: {content.word_count}\n\n")
            f.write(f"**预计阅读时间**: {content.estimated_read_time} 分钟\n\n")
            if content.summary:
                f.write(f"**摘要**: {content.summary}\n\n")
            if content.hashtags:
                f.write(f"**话题**: {' '.join(content.hashtags)}\n\n")
            f.write("---\n\n")
            f.write(content.content)
        
        return filepath
