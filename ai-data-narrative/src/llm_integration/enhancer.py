"""
LLM 集成增强 — 生成自然语言洞察、数据故事增强

使用大模型 API 将统计洞察转化为自然语言叙述，
将数据故事转化为面向特定受众的叙事。

使用方式:
    from src.llm_integration.enhancer import LLMInsightEnhancer, LLMStoryEnhancer
    
    enhancer = LLMInsightEnhancer()
    enhanced = enhancer.enhance(insights, context)
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import time

from src.llm_client import get_llm_client, LLMClient
from src.insights.engine import DataInsight
from src.narrative.storyteller import StorySection
from src.performance.optimizer import AnalysisCache


@dataclass
class EnhancedInsight:
    """增强后的洞察 — 包含自然语言描述"""
    original: DataInsight
    narrative: str  # 自然语言叙述
    implications: List[str]  # 业务含义
    recommendations: List[str]  # 行动建议
    confidence: float  # 生成置信度


@dataclass
class EnhancedStory:
    """增强后的故事"""
    original_sections: List[StorySection]
    enhanced_sections: List[StorySection]
    tone_adaptations: Dict[str, str]  # 针对不同受众的语调调整
    engagement_hooks: List[str]  # 吸引注意力的钩子


class LLMInsightEnhancer:
    """LLM 洞察增强器 — 将统计洞察转化为自然语言"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.llm = get_llm_client()
        self.cache = AnalysisCache(cache_dir) if cache_dir else None
        self.stats = {"api_calls": 0, "cache_hits": 0, "errors": 0}
    
    def enhance(self, insights: List[DataInsight], 
                data_context: Dict[str, Any]) -> List[EnhancedInsight]:
        """
        将统计洞察列表转化为自然语言洞察
        
        Args:
            insights: 原始洞察列表
            data_context: 数据上下文（如列名、数据量等）
        
        Returns:
            增强后的洞察列表
        """
        enhanced = []
        
        for insight in insights:
            # 尝试缓存
            cache_key = f"insight_{hash(insight.title)}"
            if self.cache:
                cached = self.cache.get("llm_enhance", cache_key)
                if cached:
                    self.stats["cache_hits"] += 1
                    enhanced.append(self._parse_cached(cached, insight))
                    continue
            
            try:
                enhanced_insight = self._enhance_single(insight, data_context)
                enhanced.append(enhanced_insight)
                
                # 缓存结果
                if self.cache:
                    self.cache.set("llm_enhance", cache_key, 
                                   self._serialize(enhanced_insight))
                
                self.stats["api_calls"] += 1
                
            except Exception as e:
                # 降级：返回基础版本
                enhanced.append(self._create_fallback(insight, str(e)))
                self.stats["errors"] += 1
        
        return enhanced
    
    def _enhance_single(self, insight: DataInsight, 
                        data_context: Dict[str, Any]) -> EnhancedInsight:
        """增强单个洞察"""
        # 构建 prompt
        prompt = self._build_insight_prompt(insight, data_context)
        
        # 调用 LLM（如果有）
        if self.llm and self.llm.api_key:
            response = self.llm.generate(prompt, max_tokens=500, temperature=0.7)
            parsed = self._parse_llm_response(response)
        else:
            # 无 LLM 时降级为模板生成
            parsed = self._generate_template(insight)
        
        return EnhancedInsight(
            original=insight,
            narrative=parsed["narrative"],
            implications=parsed["implications"],
            recommendations=parsed["recommendations"],
            confidence=parsed.get("confidence", 0.8)
        )
    
    def _build_insight_prompt(self, insight: DataInsight, 
                              data_context: Dict[str, Any]) -> str:
        """构建洞察增强 prompt"""
        data_desc = f"""
数据概况：
- 数据文件：{data_context.get('source_name', '未知')}
- 数据规模：{data_context.get('row_count', '?')} 行 × {data_context.get('column_count', '?')} 列
"""
        
        prompt = f"""你是一个数据分析师，擅长将数据洞察转化为通俗易懂的叙述。

{data_desc}

以下是一个基于统计分析发现的数据洞察：

洞察标题：{insight.title}
洞察类型：{insight.type.value}
重要性：{insight.severity.value}

请用通俗易懂的语言描述这个洞察，并提供业务含义和行动建议。输出格式：

叙述：
[用 2-3 句话描述这个洞察，让非技术人员也能理解]

业务含义：
1. [含义1]
2. [含义2]

行动建议：
1. [建议1]
2. [建议2]
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """解析 LLM 响应"""
        lines = response.strip().split('\n')
        
        narrative = []
        implications = []
        recommendations = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('叙述：') or line.startswith('叙述:'):
                current_section = 'narrative'
                continue
            elif line.startswith('业务含义：') or line.startswith('业务含义:'):
                current_section = 'implications'
                continue
            elif line.startswith('行动建议：') or line.startswith('行动建议:'):
                current_section = 'recommendations'
                continue
            elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.'):
                if current_section == 'implications':
                    implications.append(line[2:].strip())
                elif current_section == 'recommendations':
                    recommendations.append(line[2:].strip())
            else:
                if current_section == 'narrative':
                    narrative.append(line)
        
        return {
            "narrative": ' '.join(narrative) or "数据洞察发现：" + response[:200],
            "implications": implications or ["需要进一步分析"],
            "recommendations": recommendations or ["建议结合业务场景解读"],
            "confidence": 0.85
        }
    
    def _generate_template(self, insight: DataInsight) -> Dict:
        """无 LLM 时的模板生成"""
        templates = {
            "trend": "数据整体呈现{trend}趋势，这可能表明{implication}",
            "distribution": "数据分布{shape}，提示{implication}",
            "comparison": "对比发现{comparison}，意味着{implication}",
            "relationship": "分析显示{relationship}，建议{recommendation}",
            "composition": "构成分析表明{composition}，建议关注{recommendation}",
            "anomaly": "检测到{anomaly}，需要{recommendation}"
        }
        
        itype = insight.type.value if hasattr(insight.type, 'value') else str(insight.type)
        template = templates.get(itype, "数据洞察：{title}")
        
        narrative = template.format(
            trend="明显的" if "上升" in insight.title else "平稳的" if "稳定" in insight.title else "变化的",
            shape=insight.title.split("呈")[-1] if "呈" in insight.title else "非对称",
            comparison=insight.title,
            relationship=insight.title,
            composition=insight.title,
            anomaly=insight.title,
            title=insight.title,
            implication="业务可能正在经历结构性变化",
            recommendation="进一步深入分析相关维度"
        )
        
        return {
            "narrative": narrative,
            "implications": ["统计规律反映的业务现象"],
            "recommendations": ["结合业务场景验证"],
            "confidence": 0.6
        }
    
    def _parse_cached(self, data: Dict, original: DataInsight) -> EnhancedInsight:
        """从缓存解析"""
        return EnhancedInsight(
            original=original,
            narrative=data.get("narrative", ""),
            implications=data.get("implications", []),
            recommendations=data.get("recommendations", []),
            confidence=data.get("confidence", 0.8)
        )
    
    def _serialize(self, insight: EnhancedInsight) -> Dict:
        """序列化缓存"""
        return {
            "narrative": insight.narrative,
            "implications": insight.implications,
            "recommendations": insight.recommendations,
            "confidence": insight.confidence
        }
    
    def _create_fallback(self, insight: DataInsight, error: str) -> EnhancedInsight:
        """创建降级版本"""
        return EnhancedInsight(
            original=insight,
            narrative=f"基于统计发现：{insight.title}",
            implications=["（LLM 增强失败，使用统计版本）"],
            recommendations=["请检查 LLM 配置"],
            confidence=0.3
        )
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return dict(self.stats)


class LLMStoryEnhancer:
    """LLM 故事增强器 — 将故事章节转化为更吸引人的叙事"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.llm = get_llm_client()
        self.cache = AnalysisCache(cache_dir) if cache_dir else None
        self.stats = {"api_calls": 0, "cache_hits": 0, "errors": 0}
    
    def enhance(self, sections: List[StorySection], 
                audience: str = "technical",
                tone: str = "professional") -> EnhancedStory:
        """
        增强故事章节
        
        Args:
            sections: 原始故事章节
            audience: 受众类型（technical / business / general）
            tone: 语调（professional / casual / dramatic）
        
        Returns:
            增强后的故事
        """
        enhanced_sections = []
        tone_adaptations = {}
        engagement_hooks = []
        
        for i, section in enumerate(sections):
            # 尝试缓存
            cache_key = f"story_{hash(section.title)}_{audience}_{tone}"
            if self.cache:
                cached = self.cache.get("llm_story", cache_key)
                if cached:
                    self.stats["cache_hits"] += 1
                    enhanced_sections.append(StorySection(
                        title=cached.get("title", section.title),
                        content=cached.get("content", section.content)
                    ))
                    continue
            
            try:
                enhanced = self._enhance_section(section, audience, tone)
                enhanced_sections.append(enhanced)
                
                if self.cache:
                    self.cache.set("llm_story", cache_key, {
                        "title": enhanced.title,
                        "content": enhanced.content
                    })
                
                self.stats["api_calls"] += 1
                
                # 生成钩子（用于引言章节）
                if i == 0:
                    engagement_hooks = self._generate_hooks(section.content)
                
            except Exception as e:
                enhanced_sections.append(section)
                self.stats["errors"] += 1
        
        # 生成不同受众版本
        tone_adaptations = self._generate_audience_versions(sections, audience)
        
        return EnhancedStory(
            original_sections=sections,
            enhanced_sections=enhanced_sections,
            tone_adaptations=tone_adaptations,
            engagement_hooks=engagement_hooks
        )
    
    def _enhance_section(self, section: StorySection, 
                        audience: str, tone: str) -> StorySection:
        """增强单个章节"""
        if not self.llm or not self.llm.api_key:
            return self._template_enhance(section, audience)
        
        prompt = f"""请将以下数据故事章节改写为面向{audience}受众、采用{tone}语调的风格。

原标题：{section.title}

原内容：
{section.content}

要求：
1. 保持数据准确性，不改变任何数字或事实
2. 语言更生动、有吸引力
3. 让{audience}读者容易理解
4. 使用{tone}的语调

请直接输出改写后的标题和内容，格式：
标题：[改写后的标题]
内容：[改写后的内容]
"""
        
        response = self.llm.generate(prompt, max_tokens=1000, temperature=0.8)
        
        # 解析响应
        title = section.title
        content = section.content
        
        lines = response.strip().split('\n')
        for i, line in enumerate(lines):
            if line.startswith('标题：') or line.startswith('标题:'):
                title = line[3:].strip()
            elif line.startswith('内容：') or line.startswith('内容:'):
                content = '\n'.join(lines[i+1:]).strip()
        
        return StorySection(title=title, content=content)
    
    def _template_enhance(self, section: StorySection, audience: str) -> StorySection:
        """无 LLM 时的模板增强"""
        if audience == "general":
            # 通俗化
            content = section.content.replace("显著性差异", "明显差异")
            content = content.replace("相关性", "关联")
            content = content.replace("p值", "显著程度")
            return StorySection(title=f"[通俗版] {section.title}", content=content)
        elif audience == "business":
            # 业务化
            content = section.content + "\n\n💡 **业务建议**：基于以上分析，建议关注核心指标变化，及时调整策略。"
            return StorySection(title=section.title, content=content)
        else:
            return section
    
    def _generate_hooks(self, intro_content: str) -> List[str]:
        """生成吸引注意力的钩子"""
        if not self.llm or not self.llm.api_key:
            return [
                "🔍 数据背后隐藏着什么秘密？",
                "📊 这组数据揭示了一个有趣的趋势...",
                "💡 你可能没想到，数据告诉我们..."
            ]
        
        prompt = f"""基于以下数据内容，生成 3 个吸引读者注意力的开头钩子（hook）。每个钩子 1-2 句话，有趣但保持准确。

内容：{intro_content[:500]}

输出格式：
1. [钩子1]
2. [钩子2]
3. [钩子3]
"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=300, temperature=0.9)
            hooks = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line.startswith(('1.', '2.', '3.')):
                    hooks.append(line[2:].strip())
            return hooks[:3] or ["数据洞察：新发现！"]
        except:
            return ["数据背后隐藏着有趣的故事..."]
    
    def _generate_audience_versions(self, sections: List[StorySection], 
                                    audience: str) -> Dict[str, str]:
        """生成不同受众版本"""
        versions = {
            "technical": "保留所有统计术语和详细数据",
            "business": "强调业务影响和行动建议",
            "general": "用通俗语言解释，减少技术术语"
        }
        
        return versions
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return dict(self.stats)


class LLMReportSummarizer:
    """LLM 报告摘要器 — 生成报告摘要和标题"""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    def generate_summary(self, report_data: Dict[str, Any]) -> str:
        """生成报告摘要"""
        prompt = f"""基于以下数据分析报告，生成一段 150-200 字的摘要。

报告信息：
- 数据文件：{report_data.get('source_name', '未知')}
- 数据规模：{report_data.get('row_count', '?')} 行 × {report_data.get('column_count', '?')} 列
- 质量评分：{report_data.get('quality_score', 'N/A')}
- 洞察数量：{report_data.get('insights_count', 0)}
- 分析数量：{report_data.get('analysis_count', 0)}
- 图表数量：{report_data.get('charts_count', 0)}
- 故事章节：{report_data.get('story_sections', 0)}
- 叙事策略：{report_data.get('strategy', '未知')}

请用简洁专业的语言总结报告核心发现。不超过 200 字。
"""
        
        if not self.llm or not self.llm.api_key:
            return self._template_summary(report_data)
        
        try:
            response = self.llm.generate(prompt, max_tokens=300, temperature=0.5)
            return response.strip()[:300]
        except:
            return self._template_summary(report_data)
    
    def generate_title(self, report_data: Dict[str, Any]) -> str:
        """生成报告标题"""
        source = report_data.get('source_name', '数据')
        strategy = report_data.get('strategy', '分析')
        
        titles = [
            f"{strategy}：{source}深度洞察",
            f"{source}数据叙事报告",
            f"从数据到故事：{source}分析",
        ]
        
        return titles[0]
    
    def _template_summary(self, report_data: Dict[str, Any]) -> str:
        """模板摘要"""
        source = report_data.get('source_name', '数据')
        rows = report_data.get('row_count', '?')
        cols = report_data.get('column_count', '?')
        quality = report_data.get('quality_score', 'N/A')
        insights = report_data.get('insights_count', 0)
        
        return (
            f"本报告基于 {source}（{rows} 行 × {cols} 列）进行数据分析。"
            f"数据质量评分 {quality}。"
            f"通过统计分析发现 {insights} 条关键洞察，"
            f"涵盖趋势、分布、对比、关系等多个维度。"
            f"报告采用叙事策略组织内容，便于理解数据背后的业务含义。"
        )


class LLMIntegrationPipeline:
    """LLM 集成流水线 — 将 LLM 增强融入主流程"""
    
    def __init__(self, cache_dir: Optional[Path] = None, 
                 enable_llm: bool = True):
        self.enable_llm = enable_llm
        self.insight_enhancer = LLMInsightEnhancer(cache_dir)
        self.story_enhancer = LLMStoryEnhancer(cache_dir)
        self.summarizer = LLMReportSummarizer()
    
    def enhance_insights(self, insights: List[DataInsight],
                        data_context: Dict[str, Any]) -> Tuple[List[EnhancedInsight], Dict]:
        """增强洞察"""
        if not self.enable_llm:
            # 返回基础版本
            enhanced = [self.insight_enhancer._create_fallback(i, "LLM disabled") 
                       for i in insights]
            return enhanced, {"status": "disabled"}
        
        enhanced = self.insight_enhancer.enhance(insights, data_context)
        stats = self.insight_enhancer.get_stats()
        
        return enhanced, {
            "status": "success",
            "api_calls": stats["api_calls"],
            "cache_hits": stats["cache_hits"],
            "errors": stats["errors"]
        }
    
    def enhance_story(self, sections: List[StorySection],
                      audience: str = "general") -> Tuple[EnhancedStory, Dict]:
        """增强故事"""
        if not self.enable_llm:
            return EnhancedStory(
                original_sections=sections,
                enhanced_sections=sections,
                tone_adaptations={},
                engagement_hooks=[]
            ), {"status": "disabled"}
        
        enhanced = self.story_enhancer.enhance(sections, audience=audience)
        stats = self.story_enhancer.get_stats()
        
        return enhanced, {
            "status": "success",
            "api_calls": stats["api_calls"],
            "cache_hits": stats["cache_hits"],
            "errors": stats["errors"]
        }
    
    def generate_summary(self, report_data: Dict[str, Any]) -> str:
        """生成报告摘要"""
        return self.summarizer.generate_summary(report_data)
    
    def generate_title(self, report_data: Dict[str, Any]) -> str:
        """生成报告标题"""
        return self.summarizer.generate_title(report_data)
