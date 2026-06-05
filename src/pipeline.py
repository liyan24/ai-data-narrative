"""AI数据叙事系统 — 新架构流水线 (v6.0)

核心流程:
  Phase 0: 用户意图理解 → 数据加载 → Schema理解
  Phase 1: 技能导演制定计划
  Phase 2+: 技能执行 → 叙事导演 → 输出生成（后续阶段实现）

设计理念: 大模型驱动 (LLM-First) + 技能即代码 (Skills-as-Code)
"""

from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

from src.config import OUTPUT_DIR, SKILLS_DIR

# 新架构模块
from src.data_schema import TypeRegistry, SchemaEngine, DataProfile
from src.user_intent import (
    UserProfile, UserIntent, ValueMatrix,
    UserProfileGenerator, IntentEngine, ValueAssessor
)
from src.skills import (
    SkillContext, SkillExecutionPlan, SkillResult,
    SkillRegistry, SkillDirector, SkillExecutor, SkillGenerator
)
from src.analysis.data_understanding_agent import DataUnderstandingAgent, DataUnderstandingResult

# 保留旧模块兼容（后续逐步迁移）
from src.data_input.loader import DataLoader as OldDataLoader
from src.data_understand.quality import QualityChecker
from src.data_understand.statistics import StatisticExtractor
from src.cleaning.engine import DataCleaner
from src.insights.engine import InsightEngine
from src.narrative.strategy import NarrativeStrategyEngine
from src.narrative.storyteller import StorytellerEngine, StrategyScorer, StrategyConflictDetector
from src.visualization.recommender import ChartRecommender
from src.visualization.engine import ChartEngine
from src.visualization.advanced_charts import AdvancedChartEngine
from src.report.builder import ReportBuilder
from src.report.enhanced_builder import EnhancedReportBuilder
from src.publishing.adapters import PublishingOrchestrator, Platform
from src.llm_client import get_llm_client
from src.monitoring.logger import PipelineLogger, PerformanceMonitor


class DataNarrativePipeline:
    """数据叙事新架构流水线 — LLM-First + Skills-as-Code"""
    
    def __init__(
        self,
        output_dir: Optional[str] = None,
        max_charts: int = 5,
        enable_llm_enhance: bool = True,
        enable_user_intent: bool = True,
        enable_schema_llm: bool = True,
        enable_skill_director: bool = True,
        locale: str = "zh",
        verbose: bool = True,
        # 兼容旧参数
        auto_clean: bool = False,
        aggressive_clean: bool = False,
        enable_advanced_charts: bool = True,
        enable_storytelling: bool = True,
        enable_publishing: bool = True,
        enable_monitoring: bool = True,
        enable_ml_analysis: bool = True,
    ):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_charts = max_charts
        self.enable_llm_enhance = enable_llm_enhance
        self.enable_user_intent = enable_user_intent
        self.enable_schema_llm = enable_schema_llm
        self.enable_skill_director = enable_skill_director
        self.locale = locale
        self.verbose = verbose
        
        # 兼容旧参数
        self.auto_clean = auto_clean
        self.aggressive_clean = aggressive_clean
        self.enable_advanced_charts = enable_advanced_charts
        self.enable_storytelling = enable_storytelling
        self.enable_publishing = enable_publishing
        self.enable_monitoring = enable_monitoring
        self.enable_ml_analysis = enable_ml_analysis
        
        # === 新架构组件 ===
        # 数据层
        self.type_registry = TypeRegistry()
        self.schema_engine = SchemaEngine()
        
        # 用户意图层
        self.profile_generator = UserProfileGenerator()
        self.intent_engine = IntentEngine()
        self.value_assessor = ValueAssessor()
        
        # 技能层
        self.skill_registry = SkillRegistry(skills_dir=SKILLS_DIR)
        self.skill_director = SkillDirector(self.skill_registry)
        from src.config import SKILL_EXECUTOR_CONFIG
        self.skill_executor = SkillExecutor(
            self.skill_registry,
            max_workers=SKILL_EXECUTOR_CONFIG["max_workers"]
        )
        self.skill_generator = SkillGenerator(self.skill_registry)
        
        # 兼容旧组件
        self.chart_engine = ChartEngine()
        self.advanced_chart_engine = AdvancedChartEngine()
        self.storyteller = StorytellerEngine()
        self.publisher = PublishingOrchestrator()
        
        if enable_monitoring:
            self.logger = PipelineLogger(
                log_dir=self.output_dir / "logs",
                console_output=False
            )
            self.perf_monitor = PerformanceMonitor()
        else:
            self.logger = None
            self.perf_monitor = None
    
    def run(self, 
            source: str,
            user_input: str = "",
            progress_callback: Optional[Callable[[str, str, str], None]] = None,
            **kwargs) -> Dict[str, Any]:
        """
        执行完整的数据叙事流水线（新架构）
        
        Args:
            source: 数据源（文件路径/URL/连接字符串）
            user_input: 用户的自然语言描述（角色/需求/目标）
            progress_callback: 进度回调函数(phase_name, status, message)
            **kwargs: 额外参数（兼容旧接口）
            
        Returns:
            包含所有阶段结果的字典
        """
        result = {
            "status": "success",
            "pipeline_version": "6.0",
            "phases": {},
        }
        
        def _progress(phase: str, status: str, msg: str):
            if progress_callback:
                progress_callback(phase, status, msg)
        
        if self.perf_monitor:
            self.perf_monitor.start()
        
        # ==================== Phase 0: 用户意图理解 ====================
        if self.enable_user_intent:
            _progress("phase_0", "running", "正在理解用户需求...")
            print("\n" + "=" * 60)
            print("[PHASE 0] 用户意图理解")
            print("=" * 60)
            
            user_profile, user_intent, value_matrix = self._phase_user_intent(
                source, user_input
            )
            
            result["phases"]["user_intent"] = {
                "user_profile": user_profile.to_dict(),
                "user_intent": user_intent.to_dict(),
                "value_matrix": value_matrix.to_dict(),
            }
            
            print(f"  [OK] 角色: {user_profile.role or 'unknown'}")
            print(f"  [OK] 意图: {user_intent.intent_type.value}")
            print(f"  [OK] 目标: {user_profile.goal or 'unknown'}")
            print(f"  [OK] 专业水平: {user_profile.expertise_level.value}")
            _progress("phase_0", "success", f"角色: {user_profile.role}, 意图: {user_intent.intent_type.value}")
        else:
            # 禁用意图理解时使用默认值
            from src.user_intent.models import ExpertiseLevel, DecisionScope
            user_profile = UserProfile(
                role="", industry="", goal="",
                expertise_level=ExpertiseLevel.INTERMEDIATE,
                decision_scope=DecisionScope.TACTICAL,
            )
            user_intent = None
            value_matrix = ValueMatrix()
            _progress("phase_0", "skipped", "用户意图理解已禁用")
        
        # ==================== Phase 1: 数据加载与Schema理解 ====================
        _progress("phase_1", "running", "正在加载数据并理解结构...")
        print("\n" + "=" * 60)
        print("[PHASE 1] 数据加载与Schema理解")
        print("=" * 60)
        
        data_profile = self._phase_data_load(source)
        print(f"  [OK] 数据: {data_profile.source_name}")
        print(f"  [OK] 维度: {data_profile.row_count} 行 × {data_profile.col_count} 列")
        
        # Schema 理解
        schema = self.schema_engine.analyze(data_profile)
        data_profile.schema = schema
        print(f"  [OK] Schema: {len(schema.fields)} 个字段已理解")
        if schema.llm_summary:
            print(f"      {schema.llm_summary[:100]}...")
        
        result["phases"]["data_load"] = {
            "source_name": data_profile.source_name,
            "shape": {"rows": data_profile.row_count, "columns": data_profile.col_count},
            "schema": schema.to_dict() if schema else None,
        }
        _progress("phase_1", "success", f"{data_profile.row_count} 行 × {data_profile.col_count} 列, {len(schema.fields)} 个字段")
        
        # 如果没有在 Phase 0 中做意图理解（比如禁用了），现在基于数据补做
        if not self.enable_user_intent:
            user_profile, user_intent, value_matrix = self._phase_user_intent(
                source, user_input, data_profile
            )
        
        # ==================== Phase 1.5: 数据理解（大模型理解业务含义） ====================
        _progress("phase_1_5", "running", "正在理解数据的业务含义...")
        print("\n" + "=" * 60)
        print("[PHASE 1.5] 数据理解 — 大模型理解业务含义")
        print("=" * 60)
        
        du_agent = DataUnderstandingAgent()
        data_understanding = du_agent.analyze(
            df=data_profile.df,
            source_name=data_profile.source_name,
            user_input=user_input,
            schema=schema,
        )
        
        print(f"  [OK] 业务领域: {data_understanding.business_domain}")
        print(f"  [OK] 业务场景: {data_understanding.business_scenario}")
        print(f"  [OK] 数据描述: {data_understanding.table_description[:80]}...")
        print(f"  [OK] 列理解: {len(data_understanding.columns)} 个字段")
        for col in data_understanding.columns[:5]:
            print(f"      - {col.name}: {col.business_meaning} ({col.business_role})")
        if len(data_understanding.columns) > 5:
            print(f"      ... 还有 {len(data_understanding.columns) - 5} 个字段")
        
        if data_understanding.time_column:
            print(f"  [OK] 时间列: {data_understanding.time_column}")
        if data_understanding.key_metrics:
            print(f"  [OK] 核心指标: {', '.join(data_understanding.key_metrics[:5])}")
        if data_understanding.key_dimensions:
            print(f"  [OK] 核心维度: {', '.join(data_understanding.key_dimensions[:5])}")
        
        result["phases"]["data_understanding"] = {
            "business_domain": data_understanding.business_domain,
            "business_scenario": data_understanding.business_scenario,
            "table_description": data_understanding.table_description,
            "columns": [
                {
                    "name": c.name,
                    "business_meaning": c.business_meaning,
                    "data_type": c.data_type,
                    "business_role": c.business_role,
                    "suggested_aggregations": c.suggested_aggregations,
                }
                for c in data_understanding.columns
            ],
            "key_metrics": data_understanding.key_metrics,
            "key_dimensions": data_understanding.key_dimensions,
            "time_column": data_understanding.time_column,
            "id_column": data_understanding.id_column,
            "relationships": data_understanding.relationships,
        }
        _progress("phase_1_5", "success", 
                    f"领域: {data_understanding.business_domain}, "
                    f"场景: {data_understanding.business_scenario}, "
                    f"{len(data_understanding.columns)} 个字段已理解")
        
        # ==================== Phase 2: 技能导演制定计划 ====================
        print("\n" + "=" * 60)
        print("[PHASE 2] 技能导演制定计划")
        print("=" * 60)
        
        # 构建 SkillContext
        context = SkillContext(
            user_profile=user_profile,
            user_intent=user_intent,
            value_matrix=value_matrix,
            data_profile=data_profile,
            schema=schema,
            data_understanding=data_understanding,  # 数据理解结果
            output_dir=self.output_dir,
            locale=self.locale,
            verbose=self.verbose,
        )
        
        # ==================== Phase 2: 技能导演制定计划 ====================
        _progress("phase_2", "running", "正在制定技能执行计划...")
        print("\n" + "=" * 60)
        print("[PHASE 2] 技能导演制定计划")
        print("=" * 60)
        
        # 检查是否需要动态生成技能
        # （Phase 1 框架，返回 False）
        missing_skills = []
        
        # 制定执行计划
        if self.enable_skill_director:
            plan = self.skill_director.create_plan(context)
        else:
            # 默认计划
            from src.skills.director import SkillDirector
            plan = SkillDirector(self.skill_registry)._fallback_plan(context)
        
        result["phases"]["skill_plan"] = plan.to_dict()
        
        print(f"  [OK] 计划: {len(plan.phases)} 个阶段")
        for phase in plan.phases:
            print(f"      - {phase['name']}: {len(phase.get('skills', []))} 个技能")
        if plan.skip_reasons:
            print(f"  [INFO] 跳过: {', '.join(plan.skip_reasons.keys())}")
        
        _progress("phase_2", "success", f"{len(plan.phases)} 个阶段, {sum(len(p.get('skills', [])) for p in plan.phases)} 个技能")
        
        # ==================== Phase 3: 技能执行 ====================
        _progress("phase_3", "running", "正在执行技能...")
        print("\n" + "=" * 60)
        print("[PHASE 3] 技能执行")
        print("=" * 60)
        
        # 使用 SkillExecutor 按执行计划执行技能
        try:
            skill_results = self.skill_executor.execute(plan, context)
            result["phases"]["skill_execution"] = {
                name: sr.to_dict() for name, sr in skill_results.items()
            }
            
            # 统计成功/失败
            success_count = sum(1 for sr in skill_results.values() if sr.status == "success")
            error_count = sum(1 for sr in skill_results.values() if sr.status == "error")
            skip_count = sum(1 for sr in skill_results.values() if sr.status == "skipped")
            print(f"  [OK] 执行完成: {success_count} 成功, {error_count} 失败, {skip_count} 跳过")
            _progress("phase_3", "success", f"{success_count} 成功, {error_count} 失败, {skip_count} 跳过")
            
            # 如果关键技能失败，降级到旧版兼容执行
            critical_skills = ["data-quality-check", "stat-extraction", "insight-generation"]
            critical_failed = any(
                skill_results.get(s, SkillResult("", "error")).status == "error"
                for s in critical_skills
            )
            
            if critical_failed:
                print("  [WARN] 关键技能执行失败，降级到兼容模式...")
                _progress("phase_3", "warning", "关键技能失败，降级到兼容模式")
                legacy_result = self._legacy_execute(data_profile, user_profile, user_intent, value_matrix)
                result["phases"]["legacy_fallback"] = legacy_result
                report_path = legacy_result.get("report_path")
                charts_count = legacy_result.get("charts_count", 0)
                insights_count = legacy_result.get("insights_count", 0)
            else:
                # 从 SkillResult 中提取结果
                report_result = skill_results.get("report-builder")
                chart_result = skill_results.get("chart-generation")
                insight_result = skill_results.get("insight-generation")
                
                report_path = None
                if report_result and report_result.data:
                    report_path = report_result.data.get("report_path")
                
                charts_count = 0
                if chart_result and chart_result.data:
                    charts_count = chart_result.data.get("count", 0)
                
                insights_count = 0
                if insight_result and insight_result.data:
                    insights_count = insight_result.data.get("count", 0)
        
        except Exception as e:
            print(f"  [FAIL] SkillExecutor 执行失败: {e}")
            print("  [WARN] 降级到兼容模式...")
            _progress("phase_3", "error", f"执行失败: {e}")
            legacy_result = self._legacy_execute(data_profile, user_profile, user_intent, value_matrix)
            result["phases"]["legacy_fallback"] = legacy_result
            report_path = legacy_result.get("report_path")
            charts_count = legacy_result.get("charts_count", 0)
            insights_count = legacy_result.get("insights_count", 0)
        
        # ==================== Phase 4: 收集结果 ====================
        _progress("phase_4", "running", "正在汇总结果...")
        perf_report = None
        if self.perf_monitor:
            self.perf_monitor.snapshot("pipeline_end")
            perf_report = self.perf_monitor.get_report()
            result["performance"] = perf_report
        
        if self.logger:
            log_file = self.logger.save_json(
                self.output_dir / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            result["log_path"] = str(log_file) if log_file else None
        
        # 保存完整上下文（供后续阶段使用）
        self._save_context(context, result)
        
        result["report_path"] = report_path
        result["charts_count"] = charts_count
        result["insights_count"] = insights_count
        result["output_dir"] = str(self.output_dir)
        
        _progress("phase_4", "success", f"图表: {charts_count}, 洞察: {insights_count}")
        
        print("\n" + "=" * 60)
        print("[DONE] 流水线执行完成")
        print("=" * 60)
        print(f"  报告: {report_path or 'N/A'}")
        print(f"  图表: {charts_count} 张")
        print(f"  洞察: {insights_count} 条")
        
        return result
    
    # ==================== Phase 0: 用户意图理解 ====================
    
    def _phase_user_intent(
        self,
        source: str,
        user_input: str = "",
        data_profile: Optional[DataProfile] = None
    ) -> tuple:
        """Phase 0: 用户意图理解"""
        
        # 获取数据样本
        data_sample = ""
        if data_profile and data_profile.df is not None:
            data_sample = data_profile.df.head(3).to_string()
        
        # 1. 生成用户画像
        file_path = Path(source) if not str(source).startswith("http") else None
        user_profile = self.profile_generator.generate(
            user_input=user_input,
            file_path=file_path,
            data_sample=data_sample,
        )
        
        # 2. 识别用户意图
        data_summary = data_profile.get_summary() if data_profile else {}
        user_intent = self.intent_engine.analyze(
            user_input=user_input,
            user_profile=user_profile,
            data_profile=data_summary,
        )
        
        # 3. 评估数据价值
        fields_info = ""
        if data_profile and data_profile.schema:
            fields_info = data_profile.schema.to_markdown()
        elif data_profile and data_profile.df is not None:
            fields_info = ", ".join(data_profile.df.columns)
        
        value_matrix = self.value_assessor.assess(
            user_profile=user_profile,
            fields_info=fields_info,
            data_profile=data_summary,
        )
        
        return user_profile, user_intent, value_matrix
    
    # ==================== Phase 1: 数据加载 ====================
    
    def _phase_data_load(self, source: str) -> DataProfile:
        """Phase 1: 加载数据"""
        return self.type_registry.load(source)
    
    # ==================== Phase 3: 旧版兼容执行 ====================
    
    def _legacy_execute(
        self,
        data_profile: DataProfile,
        user_profile: Optional[Any] = None,
        user_intent: Optional[Any] = None,
        value_matrix: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        旧版兼容执行 — 保持原有分析能力
        
        后续 Phase 2-3 将逐步迁移为 Skill 执行
        """
        df = data_profile.df
        profile = data_profile  # 兼容旧接口
        
        # 数据清洗
        cleaning_report = None
        if self.auto_clean:
            print("  [CLEAN] 自动清洗数据...")
            cleaner = DataCleaner(df)
            cleaned_df = cleaner.auto_clean(aggressive=self.aggressive_clean)
            cleaning_report = cleaner.get_cleaning_report()
            df = cleaned_df
            profile.df = cleaned_df
            print(f"    [OK] 清洗后: {len(df)} 行")
        
        # 质量检查
        print("  [QUALITY] 检查数据质量...")
        quality = QualityChecker.check_all(df)
        print(f"    [OK] 评分: {quality['grade']} ({quality['overall_score']:.1%})")
        
        # 统计特征
        print("  [STATS] 提取统计特征...")
        stats = StatisticExtractor.extract_all(df)
        
        # 数据洞察
        print("  [INSIGHTS] 生成数据洞察...")
        col_types = profile.get_column_types()
        insight_engine = InsightEngine(df, col_types)
        insights = insight_engine.generate_all()
        print(f"    [OK] 发现 {len(insights)} 条洞察")
        
        # 叙事策略
        print("  [NARRATIVE] 分析叙事策略...")
        strategies = NarrativeStrategyEngine.analyze(col_types, statistics=stats)
        scored = StrategyScorer.score_strategies(df, col_types, stats)
        top_strategy = StrategyScorer.select_best_strategy(scored)
        print(f"    [OK] 最佳: {top_strategy.title if top_strategy else '通用分析'}")
        
        # 图表生成
        print("  [CHARTS] 生成图表...")
        chart_recs = ChartRecommender.recommend(col_types, statistics=stats, top_k=self.max_charts)
        charts = []
        for rec in chart_recs:
            try:
                img = self.chart_engine.generate(df, rec.chart_type, rec.columns, title=rec.title)
                if not img.startswith("["):
                    charts.append({"type": rec.chart_type.value, "title": rec.title, "data": img})
            except Exception as e:
                pass
        if self.enable_advanced_charts:
            adv_recs = self.advanced_chart_engine.recommend_advanced(df, col_types, top_k=3)
            for rec in adv_recs:
                try:
                    img = self.advanced_chart_engine.generate(df, rec["chart_type"], rec["columns"], title=rec["title"])
                    if not img.startswith("["):
                        charts.append({"type": rec["chart_type"].value, "title": rec["title"], "data": img})
                except Exception:
                    pass
        print(f"    [OK] 生成 {len(charts)} 张图表")
        
        # 故事生成
        story_sections = []
        if self.enable_storytelling and insights:
            print("  [STORY] 生成数据故事...")
            # 适配旧接口
            story_sections = self.storyteller.generate_story(
                profile, insights, top_strategy, stats
            )
            print(f"    [OK] {len(story_sections)} 个章节")
        
        # 报告组装
        print("  [REPORT] 组装报告...")
        report_path = self._build_legacy_report(profile, quality, stats, top_strategy, insights, charts, cleaning_report, story_sections)
        print(f"    [OK] {report_path}")
        
        # 平台适配
        platform_contents = {}
        if self.enable_publishing and insights:
            print("  [PUBLISH] 生成平台内容...")
            platform_contents = self.publisher.publish_to_all(
                title=f"数据叙事报告: {profile.source_name}",
                story_sections=story_sections,
                insights=insights,
                charts=charts,
            )
            for platform, content in platform_contents.items():
                if content:
                    saved = self.publisher.save_platform_content(content, self.output_dir)
                    print(f"    [OK] {platform.value}: {saved.name}")
        
        return {
            "status": "success",
            "report_path": str(report_path),
            "quality": quality,
            "strategy": {
                "title": top_strategy.title if top_strategy else None,
                "type": top_strategy.narrative_type.value if top_strategy else None,
            },
            "insights_count": len(insights),
            "charts_count": len(charts),
            "story_sections": len(story_sections),
            "platforms": [p.value for p in platform_contents.keys()],
        }
    
    def _build_legacy_report(self, profile, quality, stats, strategy, insights, charts, cleaning_report, story_sections):
        """构建旧版兼容报告"""
        builder = EnhancedReportBuilder(
            title=f"数据叙事报告: {profile.source_name}",
            author="AI数据叙事系统 v6.0"
        )
        
        builder.add_text("数据概览", profile.to_markdown(), level=2)
        
        # 质量评估
        quality_text = f"**综合评分**: {quality['grade']} ({quality['overall_score']:.1%})\n\n**问题汇总**:\n"
        for issue in quality['issues']:
            emoji = {"critical": "[CRIT]", "warning": "[WARN]", "info": "[INFO2]"}.get(issue['severity'], "⚪")
            quality_text += f"\n{emoji} **{issue['type']}** ({issue['column']}): {issue['suggestion']}"
        builder.add_text("数据质量评估", quality_text, level=2)
        
        if cleaning_report:
            builder.add_cleaning_log(cleaning_report['log'])
        
        if strategy:
            story = strategy.story_arc
            strategy_text = f"""**推荐叙事类型**: {strategy.title}

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
        
        if insights:
            builder.add_text("AI 数据洞察", "基于统计规则自动发现的数据洞察：", level=2)
            builder.add_insights(insights)
        
        if story_sections:
            builder.add_text("数据故事", "AI 生成的数据叙事：", level=2)
            for section in story_sections:
                builder.add_text(getattr(section, 'title', ''), getattr(section, 'content', ''), level=3)
        
        for chart in charts:
            builder.add_chart(chart["data"], chart["title"], "")
        
        basic = stats.get("basic", {})
        stats_text = f"""
- **行数**: {basic.get('row_count', 'N/A'):,}
- **列数**: {basic.get('column_count', 'N/A')}
- **内存占用**: {basic.get('memory_usage_mb', 'N/A')} MB
- **数据密度**: {basic.get('density', 'N/A')}%
"""
        builder.add_text("统计摘要", stats_text, level=2)
        
        report_path = self.output_dir / f"report_{profile.source_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        return builder.save(report_path, format="html")
    
    def _save_context(self, context: SkillContext, result: Dict[str, Any]):
        """保存执行上下文，供后续阶段使用"""
        import json
        
        context_file = self.output_dir / f"pipeline_context_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 只保存可序列化的部分
        serializable = {
            "user_profile": context.user_profile.to_dict() if context.user_profile else None,
            "user_intent": context.user_intent.to_dict() if context.user_intent else None,
            "value_matrix": context.value_matrix.to_dict() if context.value_matrix else None,
            "data_summary": context.data_profile.get_summary() if context.data_profile else None,
            "schema": context.schema.to_dict() if context.schema else None,
            "execution_log": context.execution_log,
            "result_summary": {k: v for k, v in result.items() if k != "phases"},
        }
        
        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        
        if self.verbose:
            print(f"  [INFO] 上下文已保存: {context_file.name}")


# CLI 入口
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="AI数据叙事系统 v6.0 (LLM-First + Skills-as-Code)")
    parser.add_argument("source", help="数据源路径 (CSV/Excel/JSON/数据库等)")
    parser.add_argument("--user-input", "-u", default="", help="用户需求描述")
    parser.add_argument("--output", "-o", default=None, help="输出目录")
    parser.add_argument("--max-charts", "-c", type=int, default=5, help="最大图表数量")
    parser.add_argument("--no-intent", action="store_true", help="禁用用户意图理解")
    parser.add_argument("--no-director", action="store_true", help="禁用技能导演")
    parser.add_argument("--auto-clean", action="store_true", help="启用自动清洗")
    parser.add_argument("--aggressive", action="store_true", help="激进清洗模式")
    
    args = parser.parse_args()
    
    pipeline = DataNarrativePipeline(
        output_dir=args.output,
        max_charts=args.max_charts,
        enable_user_intent=not args.no_intent,
        enable_skill_director=not args.no_director,
        auto_clean=args.auto_clean,
        aggressive_clean=args.aggressive,
    )
    
    result = pipeline.run(args.source, user_input=args.user_input)
    
    print("\n" + "=" * 60)
    print("[SUMMARY] 执行摘要")
    print("=" * 60)
    for phase_name, phase_data in result.get("phases", {}).items():
        print(f"  {phase_name}: OK")
    print(f"\n完整结果已保存到 output 目录")
