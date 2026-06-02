"""
第四阶段测试 — LLM集成、自动化调度、监控日志、发布API
"""

import unittest
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_integration.enhancer import (
    LLMInsightEnhancer, LLMStoryEnhancer, LLMReportSummarizer,
    LLMIntegrationPipeline, EnhancedInsight, EnhancedStory
)
from src.insights.engine import DataInsight, InsightCategory, InsightSeverity
from src.narrative.storyteller import StorySection, StorytellerEngine

from src.automation.scheduler import (
    TaskScheduler, DataWatcher, BatchProcessor, AutomationManager
)

from src.monitoring.logger import (
    PipelineLogger, PerformanceMonitor, HealthChecker, MetricsCollector
)

from src.api_publish.publisher import (
    PlatformPublisher, PublishOrchestrator, PublishTask
)


class TestLLMIntegration(unittest.TestCase):
    """测试 LLM 集成增强"""
    
    def setUp(self):
        self.insights = [
            DataInsight(
                category=InsightCategory.TREND,
                title="销售额呈上升趋势",
                description="近3个月销售额持续增长",
                severity=InsightSeverity.HIGH
            ),
            DataInsight(
                category=InsightCategory.ANOMALY,
                title="11月订单量异常下降",
                description="11月订单量同比下降20%",
                severity=InsightSeverity.CRITICAL
            )
        ]
        self.data_context = {
            "source_name": "sales_data.csv",
            "row_count": 500,
            "column_count": 7
        }
    
    def test_insight_enhancer(self):
        """测试洞察增强器"""
        enhancer = LLMInsightEnhancer()
        enhanced = enhancer.enhance(self.insights, self.data_context)
        
        self.assertEqual(len(enhanced), 2)
        for e in enhanced:
            self.assertIsInstance(e, EnhancedInsight)
            self.assertTrue(len(e.narrative) > 0)
            self.assertIsInstance(e.implications, list)
            self.assertIsInstance(e.recommendations, list)
    
    def test_story_enhancer(self):
        """测试故事增强器"""
        engine = StorytellerEngine()
        sections = engine.generate_story(
            type("obj", (), {"source_name": "test.csv", "row_count": 100, "col_count": 4}),
            self.insights, None, {"basic": {"row_count": 100, "column_count": 4}}
        )
        
        enhancer = LLMStoryEnhancer()
        enhanced = enhancer.enhance(sections, audience="general")
        
        self.assertIsInstance(enhanced, EnhancedStory)
        self.assertEqual(len(enhanced.enhanced_sections), len(sections))
    
    def test_summarizer(self):
        """测试报告摘要器"""
        summarizer = LLMReportSummarizer()
        
        report_data = {
            "source_name": "sales.csv",
            "row_count": 500,
            "column_count": 7,
            "quality_score": "A+",
            "insights_count": 3,
            "analysis_count": 10,
            "charts_count": 5,
            "story_sections": 4,
            "strategy": "数据趋势洞察"
        }
        
        summary = summarizer.generate_summary(report_data)
        self.assertTrue(len(summary) > 0)
        self.assertIn("sales.csv", summary)
        
        title = summarizer.generate_title(report_data)
        self.assertTrue(len(title) > 0)
    
    def test_pipeline(self):
        """测试 LLM 集成流水线"""
        pipeline = LLMIntegrationPipeline(enable_llm=False)
        
        enhanced, stats = pipeline.enhance_insights(self.insights, self.data_context)
        self.assertEqual(len(enhanced), 2)
        self.assertEqual(stats["status"], "disabled")
        
        sections = [StorySection(title="测试", content="内容")]
        enhanced_story, stats = pipeline.enhance_story(sections, audience="general")
        self.assertEqual(stats["status"], "disabled")
        
        summary = pipeline.generate_summary({"source_name": "test"})
        self.assertTrue(len(summary) > 0)


class TestAutomationScheduler(unittest.TestCase):
    """测试自动化调度"""
    
    def test_scheduler_creation(self):
        """测试调度器创建"""
        scheduler = TaskScheduler()
        self.assertEqual(len(scheduler.tasks), 0)
    
    def test_schedule_daily(self):
        """测试每日任务"""
        scheduler = TaskScheduler()
        
        def dummy_task(**kwargs):
            return "done"
        
        task_id = scheduler.schedule_daily(hour=9, task=dummy_task, name="test")
        self.assertIn("test", scheduler.tasks)
        self.assertEqual(scheduler.tasks[task_id].schedule, "daily")
    
    def test_schedule_interval(self):
        """测试间隔任务"""
        scheduler = TaskScheduler()
        
        task_id = scheduler.schedule_interval(minutes=30)
        self.assertIn(task_id, scheduler.tasks)
    
    def test_run_task(self):
        """测试运行任务"""
        scheduler = TaskScheduler()
        
        def test_task(value=0):
            return value + 1
        
        scheduler.schedule_interval(minutes=60, task=test_task, name="run_test")
        result = scheduler.run_task("run_test")
        self.assertEqual(result, 1)
        self.assertEqual(scheduler.tasks["run_test"].run_count, 1)
    
    def test_data_watcher(self):
        """测试数据监控"""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = DataWatcher(Path(tmpdir), "*.csv")
            
            # 初始扫描
            changes = watcher.scan()
            self.assertEqual(len(changes), 0)
            
            # 创建新文件
            test_file = Path(tmpdir) / "test.csv"
            test_file.write_text("a,b\n1,2\n")
            
            changes = watcher.scan()
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]["status"], "new")
    
    def test_batch_processor(self):
        """测试批量处理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            (Path(tmpdir) / "data1.csv").write_text("a,b\n1,2\n")
            (Path(tmpdir) / "data2.csv").write_text("x,y\n3,4\n")
            
            def factory():
                return type("MockPipeline", (), {
                    "run": lambda self, file, **kw: {"file": file, "status": "ok"}
                })()
            
            batch = BatchProcessor(factory)
            results = batch.process_directory(Path(tmpdir), "*.csv")
            
            self.assertEqual(len(results), 2)
            summary = batch.get_summary()
            self.assertEqual(summary["total"], 2)
            self.assertEqual(summary["success"], 2)


class TestMonitoring(unittest.TestCase):
    """测试监控与日志"""
    
    def test_pipeline_logger(self):
        """测试流水线日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = PipelineLogger(log_dir=Path(tmpdir), console_output=False)
            
            logger.info("test", "测试消息")
            logger.success("test", "成功消息", duration_ms=100)
            logger.warning("test", "警告消息")
            
            events = logger.get_events()
            self.assertGreaterEqual(len(events), 3)
            
            summary = logger.get_summary()
            self.assertEqual(summary["total_events"], 3)
            self.assertEqual(summary["errors"], 0)
    
    def test_logger_timed(self):
        """测试计时上下文"""
        logger = PipelineLogger(console_output=False)
        
        with logger.timed("test_step", "测试步骤"):
            pass
        
        events = logger.get_events(step="test_step")
        self.assertGreaterEqual(len(events), 2)
    
    def test_performance_monitor(self):
        """测试性能监控"""
        monitor = PerformanceMonitor()
        monitor.start()
        
        import time
        time.sleep(0.1)
        
        snapshot = monitor.snapshot("test")
        self.assertIn("memory_mb", snapshot)
        self.assertIn("elapsed_seconds", snapshot)
        
        report = monitor.get_report()
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["measurements_count"], 1)
    
    def test_health_checker(self):
        """测试健康检查"""
        checker = HealthChecker()
        report = checker.check_all()
        
        self.assertIn("status", report)
        self.assertIn("summary", report)
        self.assertIn("checks", report)
        
        # 检查 Python 版本
        self.assertIn("python_version", report["checks"])
        
        # 检查 pandas
        self.assertIn("pandas", report["checks"])
    
    def test_metrics_collector(self):
        """测试指标收集"""
        collector = MetricsCollector()
        
        collector.record("processing_time", 1.5)
        collector.record("processing_time", 2.0)
        collector.record("processing_time", 1.8)
        
        stats = collector.get_stats("processing_time")
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["min"], 1.5)
        self.assertEqual(stats["max"], 2.0)


class TestPublishAPI(unittest.TestCase):
    """测试发布 API"""
    
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.config_dir = Path(tmpdir)
        self.publisher = PlatformPublisher(config_dir=self.config_dir)
    
    def test_platform_config(self):
        """测试平台配置"""
        self.publisher.configure_platform("xiaohongshu", "test_key", enabled=True)
        
        self.assertTrue(self.publisher.config["xiaohongshu"]["enabled"])
        self.assertEqual(self.publisher.config["xiaohongshu"]["api_key"], "test_key")
    
    def test_publish_xiaohongshu(self):
        """测试小红书发布"""
        self.publisher.configure_platform("xiaohongshu", "test_key", enabled=True)
        
        result = self.publisher.publish_xiaohongshu(
            content="这是一篇测试内容",
            title="测试标题"
        )
        
        self.assertEqual(result["platform"], "xiaohongshu")
        self.assertEqual(result["status"], "published")
        self.assertIsNotNone(result["publish_id"])
    
    def test_publish_disabled(self):
        """测试未启用平台"""
        result = self.publisher.publish_wechat(
            content="测试内容",
            title="测试标题"
        )
        
        self.assertEqual(result["status"], "failed")
        self.assertIn("未启用", result["error"])
    
    def test_content_validation(self):
        """测试内容验证"""
        self.publisher.configure_platform("xiaohongshu", "key", enabled=True)
        
        # 超长内容
        long_content = "测试" * 1000
        result = self.publisher.publish_xiaohongshu(content=long_content)
        self.assertEqual(result["status"], "failed")
    
    def test_get_status(self):
        """测试获取状态"""
        self.publisher.configure_platform("xiaohongshu", "key", enabled=True)
        self.publisher.publish_xiaohongshu(content="测试")
        
        status = self.publisher.get_status()
        self.assertEqual(status["total"], 1)
        self.assertEqual(status["published"], 1)
    
    def test_batch_publish(self):
        """测试批量发布"""
        self.publisher.configure_platform("xiaohongshu", "key", enabled=True)
        
        contents = [
            {"platform": "xiaohongshu", "content": "内容1", "title": "标题1"},
            {"platform": "xiaohongshu", "content": "内容2", "title": "标题2"}
        ]
        
        results = self.publisher.batch_publish(contents)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status"], "published")


if __name__ == "__main__":
    unittest.main(verbosity=2)
