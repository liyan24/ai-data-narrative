"""
第三阶段测试 — 高级图表、故事生成、平台发布、性能优化

运行方式:
    python tests/test_phase3.py
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.visualization.advanced_charts import AdvancedChartEngine, AdvancedChartType
from src.narrative.storyteller import StorytellerEngine, StoryTone, StrategyScorer, StrategyConflictDetector
from src.publishing.adapters import XiaohongshuAdapter, WechatMPAdapter, MarkdownAdapter, PublishingOrchestrator, Platform
from src.performance.optimizer import MemoryOptimizer, SamplingAnalyzer, AnalysisCache
from src.insights.engine import InsightEngine, DataInsight, InsightCategory, InsightSeverity


class TestAdvancedCharts(unittest.TestCase):
    """测试高级图表引擎"""
    
    def setUp(self):
        np.random.seed(42)
        self.df = pd.DataFrame({
            "A": np.random.normal(100, 15, 50),
            "B": np.random.normal(50, 10, 50),
            "C": np.random.normal(200, 30, 50),
            "类别": np.random.choice(["X", "Y", "Z"], 50),
            "组": np.random.choice(["G1", "G2"], 50),
        })
        self.engine = AdvancedChartEngine()
    
    def test_boxplot(self):
        """测试箱线图"""
        result = self.engine.generate(
            self.df, AdvancedChartType.BOXPLOT, ["A", "B", "C"], "测试箱线图"
        )
        self.assertFalse(result.startswith("[ERROR]"))
        self.assertTrue(len(result) > 100)
    
    def test_heatmap(self):
        """测试热力图"""
        result = self.engine.generate(
            self.df, AdvancedChartType.HEATMAP, ["A", "B", "C"], "测试热力图"
        )
        self.assertFalse(result.startswith("[ERROR]"))
    
    def test_scatter_matrix(self):
        """测试散点图矩阵"""
        result = self.engine.generate(
            self.df, AdvancedChartType.SCATTER_MATRIX, ["A", "B", "C"], "测试散点图矩阵"
        )
        self.assertFalse(result.startswith("[ERROR]"))
    
    def test_violin(self):
        """测试小提琴图"""
        result = self.engine.generate(
            self.df, AdvancedChartType.VIOLIN, ["A", "类别"], "测试小提琴图"
        )
        self.assertFalse(result.startswith("[ERROR]"))
    
    def test_recommend(self):
        """测试图表推荐"""
        column_types = {
            "A": "numeric", "B": "numeric", "C": "numeric",
            "类别": "categorical", "组": "categorical"
        }
        recs = self.engine.recommend_advanced(self.df, column_types, top_k=3)
        self.assertGreater(len(recs), 0)
        for rec in recs:
            self.assertIn("chart_type", rec)
            self.assertIn("columns", rec)
            self.assertIn("title", rec)


class TestStoryteller(unittest.TestCase):
    """测试故事生成引擎"""
    
    def setUp(self):
        np.random.seed(42)
        self.df = pd.DataFrame({
            "日期": pd.date_range("2024-01-01", periods=100, freq="D"),
            "销售额": np.random.normal(5000, 2000, 100),
            "订单数": np.random.poisson(50, 100),
            "地区": np.random.choice(["华东", "华南", "华北"], 100),
        })
        self.column_types = {
            "日期": "datetime", "销售额": "numeric",
            "订单数": "numeric", "地区": "categorical"
        }
        
        # 生成洞察
        insight_engine = InsightEngine(self.df, self.column_types)
        self.insights = insight_engine.generate_all()
    
    def test_generate_story(self):
        """测试故事生成"""
        engine = StorytellerEngine()
        
        # 模拟 profile 对象
        class MockProfile:
            source_name = "test.csv"
            row_count = 100
            col_count = 4
        
        profile = MockProfile()
        stats = {"basic": {"row_count": 100, "column_count": 4}}
        sections = engine.generate_story(profile, self.insights, None, stats)
        self.assertGreater(len(sections), 0)
        for section in sections:
            self.assertTrue(len(section.title) > 0)
            self.assertTrue(len(section.content) > 0)
    
    def test_to_markdown(self):
        """测试 Markdown 输出"""
        engine = StorytellerEngine()
        
        class MockProfile:
            source_name = "test.csv"
            row_count = 100
            col_count = 4
        
        stats = {"basic": {"row_count": 100, "column_count": 4}}
        
        sections = engine.generate_story(MockProfile(), self.insights, None, stats)
        markdown = engine.to_markdown(sections)
        
        self.assertIn("数据故事", markdown)
        self.assertIn("数据概览", markdown)


class TestPublishingAdapters(unittest.TestCase):
    """测试平台发布适配器"""
    
    def setUp(self):
        self.insights = [
            DataInsight(
                category=InsightCategory.TREND,
                severity=InsightSeverity.HIGH,
                title="销售额呈现上升趋势",
                description="销售额在观察期内显著上升",
                recommendation="关注增长驱动因素"
            ),
            DataInsight(
                category=InsightCategory.COMPARISON,
                severity=InsightSeverity.MEDIUM,
                title="华东地区占主导地位",
                description="华东地区贡献了60%的销售额",
                recommendation="保持华东优势"
            )
        ]
        
        self.charts = [
            {"type": "trend", "title": "销售趋势", "data": "base64data123"},
            {"type": "bar", "title": "地区对比", "data": "base64data456"}
        ]
    
    def test_xiaohongshu_adapter(self):
        """测试小红书适配器"""
        adapter = XiaohongshuAdapter()
        content = adapter.adapt("测试报告", [], self.insights, self.charts)
        
        self.assertEqual(content.platform, Platform.XIAOHONGSHU)
        self.assertTrue(len(content.title) > 0)
        self.assertTrue(len(content.content) > 0)
        self.assertTrue(len(content.hashtags) > 0)
        self.assertLessEqual(content.word_count, 1000)
    
    def test_wechat_adapter(self):
        """测试微信公众号适配器"""
        adapter = WechatMPAdapter()
        content = adapter.adapt("测试报告", [], self.insights, self.charts)
        
        self.assertEqual(content.platform, Platform.WECHAT_MP)
        self.assertTrue(len(content.title) > 0)
        self.assertTrue(len(content.content) > 0)
        self.assertTrue(len(content.summary) > 0)
    
    def test_publishing_orchestrator(self):
        """测试发布编排器"""
        orchestrator = PublishingOrchestrator()
        results = orchestrator.publish_to_all("测试报告", [], self.insights, self.charts)
        
        self.assertIn(Platform.XIAOHONGSHU, results)
        self.assertIn(Platform.WECHAT_MP, results)
        self.assertIn(Platform.MARKDOWN, results)


class TestPerformanceOptimizer(unittest.TestCase):
    """测试性能优化模块"""
    
    def setUp(self):
        self.df = pd.DataFrame({
            "A": np.random.randint(0, 100, 1000),
            "B": np.random.randint(0, 1000, 1000),
            "C": np.random.choice(["X", "Y", "Z"], 1000),
            "D": np.random.random(1000),
        })
    
    def test_memory_optimizer(self):
        """测试内存优化"""
        optimizer = MemoryOptimizer()
        optimized = optimizer.optimize_dataframe(self.df)
        
        # 检查类型是否优化
        self.assertTrue(optimized.memory_usage(deep=True).sum() <= self.df.memory_usage(deep=True).sum())
    
    def test_sampling_analyzer(self):
        """测试采样分析器"""
        sampler = SamplingAnalyzer(sample_size=100)
        
        def analyze(df):
            return {"mean_A": df["A"].mean(), "count": len(df)}
        
        result = sampler.sample_and_analyze(self.df, analyze)
        
        self.assertIn("mean_A", result)
        self.assertIn("sampling_info", result)
        self.assertTrue(result["sampling_info"]["sampled"])
    
    def test_cache(self):
        """测试缓存"""
        import tempfile
        cache_dir = Path(tempfile.mkdtemp())
        cache = AnalysisCache(cache_dir)
        
        # 创建一个测试文件
        test_file = cache_dir / "test.csv"
        test_file.write_text("a,b\n1,2\n")
        
        # 测试设置和获取
        cache.set(str(test_file), "test_analysis", {"result": 123})
        result = cache.get(str(test_file), "test_analysis")
        
        self.assertEqual(result["result"], 123)
        
        # 清理
        cache.clear()


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestAdvancedCharts))
    suite.addTests(loader.loadTestsFromTestCase(TestStoryteller))
    suite.addTests(loader.loadTestsFromTestCase(TestPublishingAdapters))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceOptimizer))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
