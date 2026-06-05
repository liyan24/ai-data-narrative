"""
LLM驱动的叙事导演 — 替代规则模板填充

核心能力：
- 理解用户画像（角色/目标/专业水平）→ 调整叙事深度和语调
- 理解数据画像（Schema/统计）→ 把握数据全貌
- 基于价值矩阵过滤 → 只讲有价值的内容
- LLM生成故事大纲 + 章节内容 → 个性化叙事（非模板化）
- 降级：LLM不可用时回退到 StorytellerEngine（规则驱动）
"""

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import pandas as pd

from src.narrative.storyteller import StorytellerEngine, StorySection, StoryTone
from src.narrative.strategy import NarrativeStrategy, NarrativeType
from src.narrative.value_filter import ValueFilter, FilterLog
from src.insights.engine import DataInsight
from src.llm_client import LLMClient, get_llm_client
from src.config import PROJECT_ROOT


@dataclass
class StoryOutline:
    """故事大纲 — 由叙事导演制定"""
    title: str
    subtitle: str
    tone: str           # professional | casual | dramatic | data_driven
    target_audience: str  # beginner | intermediate | expert
    chapters: List[Dict[str, Any]]  # 每章：{title, type, insights_refs, key_message, estimated_length}
    data_hooks: List[str]   # 数据引用点（如"引用销售额TOP3"）


_DEFAULT_OUTLINE_PROMPT = """你是数据叙事导演。请根据数据洞察制定简短的故事大纲。

【用户画像】角色: {role} | 行业: {industry} | 目标: {goal} | 专业水平: {expertise_level}

【数据】{source_name} | {row_count}行×{column_count}列 | 字段: {field_list}

【高价值洞察】{insights_text}

【策略】类型: {narrative_type} | 标题: {strategy_title}

要求：
- 故事简短，每章100-200字，只讲事实
- 结构：发现→分析→结论（3章即可）
- 禁止空洞套话，每句必须有数据支撑
- 标题直接点明核心发现

输出JSON：
{{
    "title": "核心发现标题（20字以内）",
    "subtitle": "一句话概括",
    "chapters": [
        {{
            "title": "章节标题",
            "type": "discovery|analysis|conclusion",
            "key_message": "一句话核心信息",
            "insights_refs": [1],
            "estimated_length": 150
        }}
    ]
}}
"""


_DEFAULT_CHAPTER_PROMPT = """你是数据叙事写手。请根据数据撰写简短的事实性章节。

【故事】{story_title} | 本章：{chapter_title} | 关键信息：{key_message}

【数据】{source_name} | 字段：{field_list}

【本章洞察】{insights_text}

【要求】
- 只写事实，禁止空洞修辞（如"令人振奋""非常重要"）
- 每段必须有具体数据支撑
- 用数字说话，直接给出结论
- 控制在 {estimated_length} 字以内
- 中文撰写，通俗易懂
- 根据业务场景调整措辞：{business_scenario}

请直接输出正文（不要加标题）。
"""


class NarrativeDirector:
    """叙事导演 — LLM驱动的个性化故事编排"""
    
    def __init__(self,
                 llm_client: Optional[LLMClient] = None,
                 outline_prompt: Optional[str] = None,
                 chapter_prompt: Optional[str] = None,
                 value_filter: Optional[ValueFilter] = None):
        self.llm = llm_client or get_llm_client()
        self.outline_prompt = outline_prompt or _DEFAULT_OUTLINE_PROMPT
        self.chapter_prompt = chapter_prompt or _DEFAULT_CHAPTER_PROMPT
        self.value_filter = value_filter or ValueFilter()
        self._fallback_engine = StorytellerEngine()
    
    # ───────────── 核心入口：导演故事 ─────────────
    
    def direct_story(self,
                     user_profile: Any,
                     data_profile: Any,
                     insights: List[DataInsight],
                     strategy: NarrativeStrategy,
                     stats: Dict[str, Any],
                     value_matrix: Optional[Dict[str, Any]] = None,
                     data_understanding: Any = None,
                     verbose: bool = False) -> List[StorySection]:
        """
        导演完整故事：过滤 → 大纲 → 逐章撰写
        
        Returns:
            StorySection 列表
        """
        start = time.time()
        
        # Step 1: 价值过滤
        filtered_insights, filter_logs = self.value_filter.filter_insights(insights, value_matrix)
        if verbose and filter_logs:
            summary = self.value_filter.get_filter_summary(filter_logs)
            print(f"  [ValueFilter] 过滤 {summary['total_filtered']} 条低价值洞察")
            for t, count in summary["by_type"].items():
                print(f"    - {t}: {count}")
        
        # Step 2: 检查是否使用 LLM
        if not self.llm or not self.llm.api_key:
            if verbose:
                print("  [NarrativeDirector] LLM不可用，降级到 StorytellerEngine")
            return self._fallback_engine.generate_story(data_profile, filtered_insights, strategy, stats)
        
        # Step 3: 生成故事大纲
        try:
            outline = self._create_outline(user_profile, data_profile, filtered_insights, strategy, stats, data_understanding)
            if verbose:
                print(f"  [NarrativeDirector] 大纲: {outline.title} ({len(outline.chapters)} 章)")
        except Exception as e:
            if verbose:
                print(f"  [NarrativeDirector] 大纲生成失败: {e}，降级到 StorytellerEngine")
            return self._fallback_engine.generate_story(data_profile, filtered_insights, strategy, stats)
        
        # Step 4: 逐章撰写
        sections = []
        for i, chapter in enumerate(outline.chapters, 1):
            try:
                content = self._compose_chapter(
                    chapter=chapter,
                    outline=outline,
                    insights=filtered_insights,
                    data_profile=data_profile,
                    user_profile=user_profile,
                    data_understanding=data_understanding,
                    verbose=verbose,
                )
                sections.append(StorySection(
                    title=chapter["title"],
                    content=content,
                    strategy=outline.tone,
                    insights_used=chapter.get("insights_refs", []),
                    chart_references=chapter.get("data_hooks", [])
                ))
                if verbose:
                    print(f"    [OK] 第{i}章: {chapter['title']} ({len(content)} 字)")
            except Exception as e:
                if verbose:
                    print(f"    [FAIL] 第{i}章: {chapter['title']} - {e}")
                # 单章失败不影响整体，用占位符
                sections.append(StorySection(
                    title=chapter["title"],
                    content=f"*{chapter['key_message']}*\n\n（本章内容生成失败，请查看原始数据获取详情）",
                    strategy=outline.tone,
                ))
        
        elapsed = round(time.time() - start, 3)
        if verbose:
            print(f"  [NarrativeDirector] 故事生成完成: {len(sections)} 章, {elapsed}s")
        
        return sections
    
    # ───────────── 故事大纲 ─────────────
    
    def _create_outline(self,
                       user_profile: Any,
                       data_profile: Any,
                       insights: List[DataInsight],
                       strategy: NarrativeStrategy,
                       stats: Dict[str, Any],
                       data_understanding: Any = None) -> StoryOutline:
        """LLM生成故事大纲"""
        
        # 构建洞察文本
        insights_text = self._format_insights_for_prompt(insights)
        
        # 构建统计摘要
        stats_summary = self._format_stats_for_prompt(stats)
        
        # 构建字段列表（使用数据理解的业务含义）
        field_list = ""
        if data_understanding and data_understanding.columns:
            field_list = ", ".join([f"{c.name}({c.business_meaning})" for c in data_understanding.columns[:10]])
        elif data_profile and hasattr(data_profile, 'df') and data_profile.df is not None:
            field_list = ", ".join(data_profile.df.columns)
        
        # 数据理解摘要
        du_summary = ""
        if data_understanding:
            du_summary = f"""
【业务理解】
领域: {data_understanding.business_domain}
场景: {data_understanding.business_scenario}
描述: {data_understanding.table_description}
核心指标: {', '.join(data_understanding.key_metrics[:5])}
核心维度: {', '.join(data_understanding.key_dimensions[:5])}
"""
        
        # 故事弧线
        story_arc = ""
        if strategy and strategy.story_arc:
            arc = strategy.story_arc
            story_arc = f"起:{arc.setup} 承:{arc.conflict} 转:{arc.climax} 合:{arc.resolution}"
        
        prompt = self.outline_prompt.format(
            role=getattr(user_profile, 'role', '未知') or '未知',
            industry=getattr(user_profile, 'industry', '未知') or '未知',
            goal=getattr(user_profile, 'goal', '未知') or '未知',
            expertise_level=getattr(user_profile, 'expertise_level', 'intermediate'),
            source_name=getattr(data_profile, 'source_name', 'unknown'),
            row_count=getattr(data_profile, 'row_count', 0),
            column_count=getattr(data_profile, 'col_count', 0),
            field_list=field_list,
            stats_summary=stats_summary,
            insights_text=insights_text,
            narrative_type=strategy.narrative_type.value if strategy else "unknown",
            strategy_title=strategy.title if strategy else "数据洞察",
            story_arc=story_arc,
            data_understanding=du_summary,
        )
        
        response = self.llm.chat([
            {"role": "system", "content": "你是数据叙事导演。请严格输出 JSON 格式。"},
            {"role": "user", "content": prompt}
        ], temperature=0.4)
        
        data = self._extract_json(response)
        
        return StoryOutline(
            title=data.get("title", "数据洞察报告"),
            subtitle=data.get("subtitle", ""),
            tone=data.get("tone", "data_driven"),
            target_audience=data.get("target_audience", "intermediate"),
            chapters=data.get("chapters", []),
            data_hooks=data.get("data_hooks", [])
        )
    
    # ───────────── 章节撰写 ─────────────
    
    def _compose_chapter(self,
                        chapter: Dict[str, Any],
                        outline: StoryOutline,
                        insights: List[DataInsight],
                        data_profile: Any,
                        user_profile: Any,
                        data_understanding: Any = None,
                        verbose: bool = False) -> str:
        """LLM撰写单个章节"""
        
        # 提取本章引用的洞察
        refs = chapter.get("insights_refs", [])
        chapter_insights = []
        if isinstance(refs, list) and insights:
            for ref in refs:
                idx = ref - 1 if isinstance(ref, int) and ref > 0 else None
                if idx is not None and idx < len(insights):
                    chapter_insights.append(insights[idx])
        
        # 如果没有指定引用，智能选择最相关的
        if not chapter_insights and insights:
            chapter_insights = insights[:3]
        
        insights_text = self._format_insights_for_prompt(chapter_insights, numbered=False)
        
        # 字段列表使用数据理解的业务含义
        field_list = ""
        if data_understanding and data_understanding.columns:
            field_list = ", ".join([f"{c.name}({c.business_meaning})" for c in data_understanding.columns[:10]])
        elif data_profile and hasattr(data_profile, 'df') and data_profile.df is not None:
            field_list = ", ".join(data_profile.df.columns)
        
        # 业务场景
        business_scenario = data_understanding.business_scenario if data_understanding else "数据分析"
        
        prompt = self.chapter_prompt.format(
            story_title=outline.title,
            chapter_title=chapter["title"],
            chapter_type=chapter.get("type", "analysis"),
            key_message=chapter.get("key_message", ""),
            target_audience=outline.target_audience,
            expertise_level=getattr(user_profile, 'expertise_level', 'intermediate'),
            tone=outline.tone,
            source_name=getattr(data_profile, 'source_name', 'unknown'),
            field_list=field_list,
            insights_text=insights_text,
            data_hooks="\n".join(f"- {h}" for h in chapter.get("data_hooks", [])),
            estimated_length=chapter.get("estimated_length", 300),
            business_scenario=business_scenario,
        )
        
        response = self.llm.chat([
            {"role": "system", "content": "你是数据叙事写手。请用中文撰写引人入胜的数据故事章节。"},
            {"role": "user", "content": prompt}
        ], temperature=0.5)
        
        return response.strip()
    
    # ───────────── 辅助方法 ─────────────
    
    def _format_insights_for_prompt(self, insights: List[DataInsight], numbered: bool = True) -> str:
        """将洞察格式化为LLM prompt文本"""
        if not insights:
            return "（无洞察数据）"
        
        lines = []
        for i, insight in enumerate(insights, 1):
            prefix = f"{i}. " if numbered else "• "
            sev = getattr(insight, 'severity', None)
            sev_label = sev.value if sev else "medium"
            lines.append(
                f"{prefix}[{sev_label}] {getattr(insight, 'title', '')}: "
                f"{getattr(insight, 'description', '')}"
            )
            if getattr(insight, 'recommendation', None):
                lines.append(f"   建议: {insight.recommendation}")
        
        return "\n".join(lines)
    
    def _format_stats_for_prompt(self, stats: Dict[str, Any]) -> str:
        """将统计信息格式化为简短摘要"""
        if not stats:
            return "（无统计摘要）"
        
        parts = []
        basic = stats.get("basic", {})
        if basic:
            parts.append(f"行数: {basic.get('row_count', 'N/A')}, 列数: {basic.get('column_count', 'N/A')}")
        
        dist = stats.get("distributions", {})
        if dist:
            numeric_summary = dist.get("numeric_summary", {})
            if numeric_summary:
                cols = list(numeric_summary.keys())[:3]
                parts.append(f"数值列示例: {', '.join(cols)}")
        
        return "; ".join(parts) if parts else str(stats)[:200]
    
    def _extract_json(self, text: str) -> dict:
        """从LLM响应中提取JSON"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    
    def _fallback_outline(self, insights: List[DataInsight], 
                         strategy: NarrativeStrategy) -> StoryOutline:
        """LLM不可用时的默认大纲"""
        chapters = [
            {"title": "📖 数据故事", "type": "intro", "key_message": "引入数据背景", 
             "insights_refs": [], "data_hooks": [], "estimated_length": 250},
            {"title": "🔍 数据概览", "type": "discovery", "key_message": "展示数据全貌",
             "insights_refs": [], "data_hooks": [], "estimated_length": 200},
        ]
        
        if insights:
            chapters.append({
                "title": "⭐ 核心发现", "type": "analysis", 
                "key_message": "呈现最重要的数据洞察",
                "insights_refs": list(range(1, min(len(insights)+1, 4))),
                "data_hooks": [], "estimated_length": 350
            })
        
        chapters.append({
            "title": "📝 总结与建议", "type": "conclusion",
            "key_message": "总结并给出行动建议",
            "insights_refs": [], "data_hooks": [], "estimated_length": 250
        })
        
        return StoryOutline(
            title=strategy.title if strategy else "数据洞察报告",
            subtitle="",
            tone="data_driven",
            target_audience="intermediate",
            chapters=chapters,
            data_hooks=[]
        )


__all__ = ["NarrativeDirector", "StoryOutline"]
