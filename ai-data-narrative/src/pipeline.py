"""
AI数据叙事系统 — 主入口与流水线编排

使用方式:
    from src.pipeline import DataNarrativePipeline
    
    pipeline = DataNarrativePipeline()
    result = pipeline.run("data.csv")
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from datetime import datetime

from src.data_input.loader import DataLoader, DataProfile
from src.data_understand.quality import QualityChecker
from src.data_understand.statistics import StatisticExtractor
from src.narrative.strategy import NarrativeStrategyEngine, NarrativeStrategy
from src.narrative.storyteller import StorytellerEngine, StorySection, StrategyScorer, StrategyConflictDetector
from src.visualization.recommender import ChartRecommender
from src.visualization.engine import ChartEngine
from src.visualization.advanced_charts import AdvancedChartEngine, AdvancedChartType
from src.report.builder import ReportBuilder
from src.report.enhanced_builder import EnhancedReportBuilder
from src.insights.engine import InsightEngine, DataInsight
from src.cleaning.engine import DataCleaner
from src.analysis.engine import MultiDimensionAnalyzer, AnalysisType
from src.publishing.adapters import PublishingOrchestrator, Platform
from src.performance.optimizer import MemoryOptimizer, SamplingAnalyzer, ProgressTracker
from src.llm_integration.enhancer import LLMIntegrationPipeline
from src.monitoring.logger import PipelineLogger, PerformanceMonitor, MetricsCollector
from src.api_publish.publisher import PlatformPublisher, PublishOrchestrator
from src.llm_client import get_llm_client
from src.config import OUTPUT_DIR

# 第五阶段
from src.analysis.ml_engine import AdvancedAnalyzer
from src.data_input.connectors import DataSourceManager
from src.plugins.manager import PluginManager
from src.i18n.translator import Translator


class DataNarrativePipeline:
    """数据叙事主流水线 — 第四阶段完整版"""
    
    def __init__(self, max_charts: int = 5, output_dir: str = None, 
                 auto_clean: bool = False, aggressive_clean: bool = False,
                 enable_advanced_charts: bool = True,
                 enable_storytelling: bool = True,
                 enable_publishing: bool = True,
                 sample_size: int = None,
                 enable_llm_enhance: bool = False,
                 enable_monitoring: bool = True,
                 enable_auto_publish: bool = False,
                 enable_ml_analysis: bool = True,
                 plugin_dir: str = None,
                 locale: str = "zh"):
        self.max_charts = max_charts
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.auto_clean = auto_clean
        self.aggressive_clean = aggressive_clean
        self.enable_advanced_charts = enable_advanced_charts
        self.enable_storytelling = enable_storytelling
        self.enable_publishing = enable_publishing
        self.sample_size = sample_size
        self.enable_llm_enhance = enable_llm_enhance
        self.enable_monitoring = enable_monitoring
        self.enable_auto_publish = enable_auto_publish
        self.enable_ml_analysis = enable_ml_analysis
        self.locale = locale
        
        self.chart_engine = ChartEngine()
        self.advanced_chart_engine = AdvancedChartEngine()
        self.storyteller = StorytellerEngine()
        self.publisher = PublishingOrchestrator()
        self.sampling_analyzer = SamplingAnalyzer(sample_size) if sample_size else None
        self.llm = get_llm_client()
        
        # 第四阶段组件
        self.llm_pipeline = LLMIntegrationPipeline(
            cache_dir=self.output_dir / ".cache",
            enable_llm=enable_llm_enhance
        )
        self.logger = PipelineLogger(
            log_dir=self.output_dir / "logs",
            console_output=False
        ) if enable_monitoring else None
        self.perf_monitor = PerformanceMonitor() if enable_monitoring else None
        self.metrics = MetricsCollector() if enable_monitoring else None
        self.platform_publisher = PlatformPublisher() if enable_auto_publish else None
        
        # 第五阶段组件
        self.translator = Translator(locale)
        self.plugin_manager = PluginManager(Path(plugin_dir) if plugin_dir else None)
        self.data_source_manager = DataSourceManager()
    
    def run(self, file_path: str, narrative_hint: str = None) -> Dict[str, Any]:
        """
        执行完整的数据叙事流水线（第四阶段完整版）
        
        Args:
            file_path: 数据文件路径
            narrative_hint: 用户叙事意图提示（可选）
            
        Returns:
            包含报告路径、分析结果等信息的字典
        """
        # 第四阶段：启动监控
        if self.perf_monitor:
            self.perf_monitor.start()
        
        if self.logger:
            self.logger.info("pipeline", f"开始处理: {file_path}")
        
        print(f"[START] 开始处理: {file_path}")
        
        # Step 1: 数据加载
        print("[LOAD] 加载数据...")
        if self.logger:
            with self.logger.timed("load", "加载数据"):
                profile = DataLoader.load(file_path)
        else:
            profile = DataLoader.load(file_path)
        print(f"   [OK] 数据维度: {profile.row_count} 行 x {profile.col_count} 列")
        
        # 第五阶段：加载插件
        if self.plugin_manager.plugin_dir and self.plugin_manager.plugin_dir.exists():
            self.plugin_manager.load_plugins()
            profile_dict = profile.get_summary() if hasattr(profile, 'get_summary') else {}
            profile_dict = self.plugin_manager.run_hook("on_load", profile_dict)
        
        # Step 2: 数据清洗（可选）
        if self.auto_clean:
            print("[CLEAN] 自动清洗数据...")
            if self.logger:
                with self.logger.timed("clean", "自动清洗数据"):
                    cleaner = DataCleaner(profile.df)
                    cleaned_df = cleaner.auto_clean(aggressive=self.aggressive_clean)
                    cleaning_report = cleaner.get_cleaning_report()
                    profile.df = cleaned_df
                    profile.row_count = len(cleaned_df)
            else:
                cleaner = DataCleaner(profile.df)
                cleaned_df = cleaner.auto_clean(aggressive=self.aggressive_clean)
                cleaning_report = cleaner.get_cleaning_report()
                profile.df = cleaned_df
                profile.row_count = len(cleaned_df)
            print(f"   [OK] 清洗后: {profile.row_count} 行 x {profile.col_count} 列")
            print(f"   [OK] 清洗动作: {len(cleaning_report['suggestions'])} 项")
        else:
            cleaning_report = None
        
        # Step 3: 质量检查
        print("[QUALITY] 检查数据质量...")
        if self.logger:
            with self.logger.timed("quality", "检查数据质量"):
                quality = QualityChecker.check_all(profile.df)
        else:
            quality = QualityChecker.check_all(profile.df)
        print(f"   [OK] 质量评分: {quality['grade']} ({quality['overall_score']:.1%})")
        
        # Step 4: 统计特征提取
        print("[STATS] 提取统计特征...")
        if self.logger:
            with self.logger.timed("stats", "提取统计特征"):
                stats = StatisticExtractor.extract_all(profile.df)
        else:
            stats = StatisticExtractor.extract_all(profile.df)
        
        # Step 5: 数据洞察（基于统计规则）
        print("[INSIGHTS] 生成数据洞察...")
        if self.logger:
            with self.logger.timed("insights", "生成数据洞察"):
                insight_engine = InsightEngine(profile.df, profile.get_column_types())
                insights = insight_engine.generate_all()
        else:
            insight_engine = InsightEngine(profile.df, profile.get_column_types())
            insights = insight_engine.generate_all()
        print(f"   [OK] 发现 {len(insights)} 条洞察")
        for i, ins in enumerate(insights[:3]):
            print(f"      - [{ins.severity.value}] {ins.title}")
        
        # 第四阶段：LLM 洞察增强
        enhanced_insights = None
        if self.enable_llm_enhance and insights:
            print("[LLM] 增强数据洞察...")
            data_context = {
                "source_name": profile.source_name,
                "row_count": profile.row_count,
                "column_count": profile.col_count
            }
            enhanced_insights, enhance_stats = self.llm_pipeline.enhance_insights(
                insights, data_context
            )
            print(f"   [OK] LLM 增强完成 (API: {enhance_stats.get('api_calls', 0)}, 缓存: {enhance_stats.get('cache_hits', 0)})")
        
        # Step 6: 多维度分析
        print("[ANALYSIS] 多维度分析...")
        if self.logger:
            with self.logger.timed("analysis", "多维度分析"):
                analyzer = MultiDimensionAnalyzer(profile.df, profile.get_column_types())
                analysis_results = analyzer.analyze()
        else:
            analyzer = MultiDimensionAnalyzer(profile.df, profile.get_column_types())
            analysis_results = analyzer.analyze()
        print(f"   [OK] 完成 {len(analysis_results)} 项分析")
        
        # 第五阶段：高级 ML 分析
        ml_results = {}
        if self.enable_ml_analysis:
            print("[ML] 高级机器学习分析...")
            if self.logger:
                with self.logger.timed("ml_analysis", "高级 ML 分析"):
                    ml_analyzer = AdvancedAnalyzer(profile.df)
                    numeric_cols = [c for c, t in profile.get_column_types().items() if t == 'numeric']
                    target_col = numeric_cols[0] if numeric_cols else None
                    ml_results = ml_analyzer.analyze_all(
                        target_column=target_col,
                        segment_column=next((c for c, t in profile.get_column_types().items() if t == 'categorical'), None)
                    )
            else:
                ml_analyzer = AdvancedAnalyzer(profile.df)
                numeric_cols = [c for c, t in profile.get_column_types().items() if t == 'numeric']
                target_col = numeric_cols[0] if numeric_cols else None
                ml_results = ml_analyzer.analyze_all(
                    target_column=target_col,
                    segment_column=next((c for c, t in profile.get_column_types().items() if t == 'categorical'), None)
                )
            
            if ml_results.get('anomalies'):
                print(f"   [OK] 异常检测: {len(ml_results['anomalies'])} 列")
            if ml_results.get('clusters'):
                print(f"   [OK] 聚类分析: {ml_results['clusters']['n_clusters']} 类")
            if ml_results.get('prediction'):
                print(f"   [OK] 趋势预测: {ml_results['prediction']['horizon']} 步")
            if ml_results.get('feature_importance'):
                top_feature = list(ml_results['feature_importance'].keys())[0]
                print(f"   [OK] 特征重要性: Top 1 = {top_feature}")
        
        # Step 7: 叙事策略分析
        print("[NARRATIVE] 分析叙事策略...")
        if self.logger:
            with self.logger.timed("narrative", "分析叙事策略"):
                strategies = NarrativeStrategyEngine.analyze(
                    profile.get_column_types(), 
                    statistics=stats
                )
                scored_strategies = StrategyScorer.score_strategies(
                    profile.df, profile.get_column_types(), stats
                )
                top_strategy = StrategyScorer.select_best_strategy(scored_strategies)
                top_strategies = StrategyScorer.select_top_strategies(scored_strategies, top_n=3)
                conflicts = StrategyConflictDetector.check_conflicts(top_strategies)
                if conflicts:
                    strategy_scores = {id(s): sc for s, sc in scored_strategies}
                    top_strategies = StrategyConflictDetector.resolve_conflicts(
                        top_strategies, strategy_scores
                    )
        else:
            strategies = NarrativeStrategyEngine.analyze(
                profile.get_column_types(), 
                statistics=stats
            )
            scored_strategies = StrategyScorer.score_strategies(
                profile.df, profile.get_column_types(), stats
            )
            top_strategy = StrategyScorer.select_best_strategy(scored_strategies)
            top_strategies = StrategyScorer.select_top_strategies(scored_strategies, top_n=3)
            conflicts = StrategyConflictDetector.check_conflicts(top_strategies)
            if conflicts:
                strategy_scores = {id(s): sc for s, sc in scored_strategies}
                top_strategies = StrategyConflictDetector.resolve_conflicts(
                    top_strategies, strategy_scores
                )
        
        if top_strategy:
            top_score = next((sc for s, sc in scored_strategies if s == top_strategy), 0)
            print(f"   [OK] 最佳策略: {top_strategy.title} (得分: {top_score:.2f})")
        else:
            top_strategy = strategies[0] if strategies else None
            print(f"   [OK] 推荐策略: {top_strategy.title if top_strategy else '通用分析'}")
        
        # Step 8: 图表推荐与生成（基础图表）
        print("[CHARTS] 生成基础图表...")
        generated_charts = []
        if self.logger:
            with self.logger.timed("charts", "生成基础图表"):
                chart_recs = ChartRecommender.recommend(
                    profile.get_column_types(),
                    statistics=stats,
                    top_k=self.max_charts
                )
                for i, rec in enumerate(chart_recs):
                    try:
                        img_data = self.chart_engine.generate(
                            profile.df, 
                            rec.chart_type, 
                            rec.columns, 
                            title=rec.title
                        )
                        if not img_data.startswith("["):
                            generated_charts.append({
                                "type": rec.chart_type.value,
                                "title": rec.title,
                                "data": img_data,
                                "description": rec.description
                            })
                            print(f"   [OK] 图表 {i+1}: {rec.title}")
                    except Exception as e:
                        print(f"   [ERR] 图表 {i+1} 生成失败: {e}")
        else:
            chart_recs = ChartRecommender.recommend(
                profile.get_column_types(),
                statistics=stats,
                top_k=self.max_charts
            )
            for i, rec in enumerate(chart_recs):
                try:
                    img_data = self.chart_engine.generate(
                        profile.df, 
                        rec.chart_type, 
                        rec.columns, 
                        title=rec.title
                    )
                    if not img_data.startswith("["):
                        generated_charts.append({
                            "type": rec.chart_type.value,
                            "title": rec.title,
                            "data": img_data,
                            "description": rec.description
                        })
                        print(f"   [OK] 图表 {i+1}: {rec.title}")
                except Exception as e:
                    print(f"   [ERR] 图表 {i+1} 生成失败: {e}")
        
        # Step 9: 高级图表生成
        if self.enable_advanced_charts:
            print("[ADVANCED] 生成高级图表...")
            advanced_recs = self.advanced_chart_engine.recommend_advanced(
                profile.df, profile.get_column_types(), top_k=3
            )
            
            for i, rec in enumerate(advanced_recs):
                try:
                    img_data = self.advanced_chart_engine.generate(
                        profile.df,
                        rec["chart_type"],
                        rec["columns"],
                        title=rec["title"]
                    )
                    if not img_data.startswith("["):
                        generated_charts.append({
                            "type": rec["chart_type"].value,
                            "title": rec["title"],
                            "data": img_data,
                            "description": rec["description"]
                        })
                        print(f"   [OK] 高级图表 {i+1}: {rec['title']}")
                except Exception as e:
                    print(f"   [ERR] 高级图表 {i+1} 生成失败: {e}")
        
        # Step 10: 故事生成
        story_sections = []
        if self.enable_storytelling and insights:
            print("[STORY] 生成数据故事...")
            story_sections = self.storyteller.generate_story(
                profile, insights, top_strategy, stats
            )
            print(f"   [OK] 生成 {len(story_sections)} 个故事章节")
            
            # 第四阶段：LLM 故事增强
            if self.enable_llm_enhance and story_sections:
                print("[LLM] 增强数据故事...")
                enhanced_story, story_stats = self.llm_pipeline.enhance_story(
                    story_sections, audience="general"
                )
                story_sections = enhanced_story.enhanced_sections
                print(f"   [OK] 故事增强完成 (API: {story_stats.get('api_calls', 0)})")
        
        # Step 11: 组装增强报告
        print("[REPORT] 组装增强报告...")
        report_path = self._build_enhanced_report(
            profile, quality, stats, top_strategy, insights, analysis_results,
            generated_charts, cleaning_report, story_sections
        )
        print(f"   [OK] 报告已保存: {report_path}")
        
        # Step 12: 平台发布适配
        platform_contents = {}
        if self.enable_publishing and insights:
            print("[PUBLISH] 生成平台适配内容...")
            platform_contents = self.publisher.publish_to_all(
                title=f"数据叙事报告: {profile.source_name}",
                story_sections=story_sections,
                insights=insights,
                charts=generated_charts
            )
            
            for platform, content in platform_contents.items():
                if content:
                    saved_path = self.publisher.save_platform_content(content, self.output_dir)
                    print(f"   [OK] {platform.value}: {saved_path.name} ({content.word_count} 字)")
            
            # 第四阶段：自动发布到实际平台
            if self.enable_auto_publish and platform_contents:
                print("[API] 自动发布到平台...")
                for platform, content in platform_contents.items():
                    if platform == Platform.XIAOHONGSHU and content:
                        result = self.platform_publisher.publish_xiaohongshu(
                            content.content, content.title
                        )
                        print(f"   [OK] 小红书发布: {result['status']}")
                    elif platform == Platform.WECHAT_MP and content:
                        result = self.platform_publisher.publish_wechat(
                            content.content, content.title
                        )
                        print(f"   [OK] 微信发布: {result['status']}")
        
        # 第四阶段：生成报告摘要
        report_summary = ""
        if self.enable_llm_enhance:
            report_data = {
                "source_name": profile.source_name,
                "row_count": profile.row_count,
                "column_count": profile.col_count,
                "quality_score": quality.get("grade", "N/A"),
                "insights_count": len(insights),
                "analysis_count": len(analysis_results),
                "charts_count": len(generated_charts),
                "story_sections": len(story_sections),
                "strategy": top_strategy.title if top_strategy else "未知"
            }
            report_summary = self.llm_pipeline.generate_summary(report_data)
        
        # 第四阶段：收集监控数据
        perf_report = None
        log_summary = None
        if self.perf_monitor:
            self.perf_monitor.snapshot("pipeline_end")
            perf_report = self.perf_monitor.get_report()
        if self.logger:
            log_summary = self.logger.get_summary()
        
        result = {
            "status": "success",
            "report_path": str(report_path),
            "report_summary": report_summary,
            "data_profile": profile.get_summary(),
            "quality": quality,
            "strategy": {
                "type": top_strategy.narrative_type.value if top_strategy else None,
                "title": top_strategy.title if top_strategy else None,
                "confidence": top_strategy.confidence if top_strategy else 0,
                "score": next((sc for s, sc in scored_strategies if s == top_strategy), 0) if top_strategy else 0
            },
            "strategies_count": len(top_strategies),
            "insights_count": len(insights),
            "insights": [i.title for i in insights[:5]],
            "analysis_count": len(analysis_results),
            "charts_count": len(generated_charts),
            "story_sections": len(story_sections),
            "platforms": [p.value for p in platform_contents.keys()],
            "cleaning": cleaning_report,
            "performance": perf_report,
            "log_summary": log_summary,
            "ml_analysis": ml_results,
            "plugins": self.plugin_manager.list_plugins() if self.plugin_manager.plugins else []
        }
        
        # 第四阶段：保存日志和指标
        if self.logger:
            log_file = self.logger.save_json(self.output_dir / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        if self.perf_monitor:
            perf_file = self.perf_monitor.save_report(self.output_dir / f"perf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        return result
    
    def _build_enhanced_report(self, profile: DataProfile, quality: Dict, stats: Dict,
                                strategy: NarrativeStrategy, insights: List[DataInsight],
                                analysis_results: List[AnalysisResult], charts: List[Dict],
                                cleaning_report: Optional[Dict], story_sections: List[Any] = None) -> Path:
        """构建增强报告（第三阶段 — 支持故事章节）"""
        builder = EnhancedReportBuilder(
            title=f"数据叙事报告: {profile.source_name}",
            author="AI数据叙事系统 v3.0"
        )
        
        # 1. 数据概览
        builder.add_text("数据概览", profile.to_markdown(), level=2)
        
        # 2. 质量评估
        quality_text = f"""
**综合评分**: {quality['grade']} ({quality['overall_score']:.1%})

**问题汇总**:
"""
        for issue in quality['issues']:
            emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(issue['severity'], "⚪")
            quality_text += f"\n{emoji} **{issue['type']}** ({issue['column']}): {issue['suggestion']}"
        
        builder.add_text("数据质量评估", quality_text, level=2)
        
        # 3. 清洗记录
        if cleaning_report and cleaning_report['suggestions']:
            builder.add_cleaning_log(cleaning_report['log'])
        
        # 4. 叙事策略
        if strategy:
            story = strategy.story_arc
            strategy_text = f"""
**推荐叙事类型**: {strategy.title}

**故事线**:
- **起**: {story.setup}
- **承**: {story.conflict}
- **转**: {story.climax}
- **合**: {story.resolution}

**关键洞察点**:
"""
            for point in strategy.key_points:
                strategy_text += f"\n- {point}"
            
            builder.add_text("叙事策略", strategy_text, level=2)
        
        # 5. 数据洞察
        if insights:
            builder.add_text("AI 数据洞察", "基于统计规则自动发现的数据洞察：", level=2)
            builder.add_insights(insights)
        
        # 6. 数据故事（第三阶段新增）
        if story_sections:
            builder.add_text("数据故事", "AI 生成的数据叙事：", level=2)
            for section in story_sections:
                section_title = getattr(section, 'title', '')
                section_content = getattr(section, 'content', '')
                builder.add_text(section_title, section_content, level=3)
        
        # 7. 多维度分析
        if analysis_results:
            builder.add_text("多维度分析", "", level=2)
            builder.add_analysis(analysis_results)
        
        # 7. 可视化图表
        for chart in charts:
            builder.add_chart(
                chart["data"],
                chart["title"],
                chart["description"]
            )
        
        # 8. 统计摘要
        basic = stats.get("basic", {})
        stats_text = f"""
- **行数**: {basic.get('row_count', 'N/A'):,}
- **列数**: {basic.get('column_count', 'N/A')}
- **内存占用**: {basic.get('memory_usage_mb', 'N/A')} MB
- **数据密度**: {basic.get('density', 'N/A')}%
"""
        builder.add_text("统计摘要", stats_text, level=2)
        
        # 保存
        report_path = self.output_dir / f"report_{profile.source_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        return builder.save(report_path, format="html")
    
    # 保留旧方法用于兼容
    def _generate_insights(self, profile: DataProfile, quality: Dict, stats: Dict, strategy: NarrativeStrategy) -> List[str]:
        """使用 LLM 生成数据洞察"""
        # 构建数据描述
        data_desc = f"""
数据文件: {profile.source_name}
数据维度: {profile.row_count} 行 × {profile.col_count} 列

列类型分布:
"""
        for col, info in profile.column_profiles.items():
            data_desc += f"- {col}: {info['type']}/{info.get('subtype', '')}\n"
        
        data_desc += f"\n质量评分: {quality['grade']} ({quality['overall_score']:.1%})\n"
        
        if quality['issues']:
            data_desc += "\n发现的问题:\n"
            for issue in quality['issues'][:5]:
                data_desc += f"- [{issue['severity']}] {issue['suggestion']}\n"
        
        if strategy:
            data_desc += f"\n推荐叙事策略: {strategy.title}\n"
            data_desc += f"故事线: {strategy.story_arc.setup}\n"
        
        try:
            insight_text = self.llm.analyze_data(data_desc, task="generate_insights")
            # 简单拆分为多条洞察
            insights = [line.strip() for line in insight_text.split('\n') if line.strip() and len(line) > 10]
            return insights[:5]  # 最多5条
        except Exception:
            return ["数据洞察生成暂时不可用，请查看详细统计信息。"]
    
    def _build_report(self, profile: DataProfile, quality: Dict, stats: Dict, 
                      strategy: NarrativeStrategy, insights: List[str], charts: List[Dict]) -> Path:
        """构建完整报告"""
        builder = ReportBuilder(
            title=f"数据叙事报告: {profile.source_name}",
            author="AI数据叙事系统"
        )
        
        # 1. 数据概览
        builder.add_section("数据概览", profile.to_markdown(), level=2)
        
        # 2. 质量评估
        quality_text = f"""
**综合评分**: {quality['grade']} ({quality['overall_score']:.1%})

**问题汇总**:
"""
        for issue in quality['issues']:
            emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(issue['severity'], "⚪")
            quality_text += f"\n{emoji} **{issue['type']}** ({issue['column']}): {issue['suggestion']}"
        
        builder.add_section("数据质量评估", quality_text, level=2)
        
        # 3. 叙事策略
        if strategy:
            story = strategy.story_arc
            strategy_text = f"""
**推荐叙事类型**: {strategy.title}

**故事线**:
- **起**: {story.setup}
- **承**: {story.conflict}
- **转**: {story.climax}
- **合**: {story.resolution}

**关键洞察点**:
"""
            for point in strategy.key_points:
                strategy_text += f"\n- {point}"
            
            builder.add_section("叙事策略", strategy_text, level=2)
        
        # 4. 数据洞察
        insights_text = "\n\n".join([f"{i+1}. {insight}" for i, insight in enumerate(insights)])
        builder.add_section("AI 数据洞察", insights_text, level=2)
        
        # 5. 可视化图表
        for chart in charts:
            builder.add_chart(
                chart["data"],
                chart["title"],
                chart["description"]
            )
        
        # 6. 统计摘要
        basic = stats.get("basic", {})
        stats_text = f"""
- **行数**: {basic.get('row_count', 'N/A'):,}
- **列数**: {basic.get('column_count', 'N/A')}
- **内存占用**: {basic.get('memory_usage_mb', 'N/A')} MB
- **数据密度**: {basic.get('density', 'N/A')}%
"""
        builder.add_section("统计摘要", stats_text, level=2)
        
        # 保存
        report_path = self.output_dir / f"report_{profile.source_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        return builder.save(report_path, format="html")


# CLI 入口
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="AI数据叙事系统")
    parser.add_argument("file", help="数据文件路径 (CSV/Excel/JSON)")
    parser.add_argument("--output", "-o", default=None, help="输出目录")
    parser.add_argument("--max-charts", "-c", type=int, default=5, help="最大图表数量")
    parser.add_argument("--hint", "-t", default=None, help="叙事意图提示")
    parser.add_argument("--auto-clean", action="store_true", help="启用自动清洗")
    parser.add_argument("--aggressive", action="store_true", help="激进清洗模式")
    
    args = parser.parse_args()
    
    pipeline = DataNarrativePipeline(
        max_charts=args.max_charts,
        output_dir=args.output,
        auto_clean=args.auto_clean,
        aggressive_clean=args.aggressive
    )
    
    result = pipeline.run(args.file, narrative_hint=args.hint)
    
    print("\n" + "="*60)
    print("[DONE] 处理完成!")
    print(f"[REPORT] 报告路径: {result['report_path']}")
    print(f"[CHARTS] 生成图表: {result['charts_count']} 张")
    print(f"[INSIGHTS] 数据洞察: {result['insights_count']} 条")
    print(f"[ANALYSIS] 多维分析: {result['analysis_count']} 项")
    print(f"[STRATEGY] 叙事策略: {result['strategy']['title']}")
    print("="*60)
