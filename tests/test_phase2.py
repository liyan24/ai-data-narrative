"""
第二阶段测试 — 数据洞察引擎、数据清洗引擎、多维度分析引擎

运行方式:
    python tests/test_phase2.py
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.insights.engine import InsightEngine, DataInsight, InsightCategory, InsightSeverity
from src.cleaning.engine import DataCleaner, CleanAction
from src.analysis.engine import MultiDimensionAnalyzer, AnalysisResult, AnalysisType


class TestInsightEngine(unittest.TestCase):
    """测试数据洞察引擎"""
    
    def setUp(self):
        np.random.seed(42)
        self.df = pd.DataFrame({
            "日期": pd.date_range("2024-01-01", periods=100, freq="D"),
            "销售额": np.random.normal(5000, 2000, 100).clip(1000, 15000),
            "订单数": np.random.poisson(50, 100),
            "地区": np.random.choice(["华东", "华南", "华北", "西南"], 100),
            "产品": np.random.choice(["A", "B", "C"], 100),
        })
        self.column_types = {
            "日期": "datetime",
            "销售额": "numeric",
            "订单数": "numeric",
            "地区": "categorical",
            "产品": "categorical",
        }
    
    def test_generate_insights(self):
        """测试洞察生成"""
        engine = InsightEngine(self.df, self.column_types)
        insights = engine.generate_all()
        
        self.assertGreater(len(insights), 0)
        for insight in insights:
            self.assertIsInstance(insight, DataInsight)
            self.assertIn(insight.category, InsightCategory)
            self.assertIn(insight.severity, InsightSeverity)
            self.assertTrue(len(insight.title) > 0)
            self.assertTrue(len(insight.description) > 0)
    
    def test_trend_detection(self):
        """测试趋势检测"""
        # 创建有趋势的数据
        df = self.df.copy()
        df["销售额"] = np.arange(100) * 100 + np.random.normal(0, 500, 100)
        
        engine = InsightEngine(df, self.column_types)
        insights = engine.generate_all()
        
        trend_insights = [i for i in insights if i.category == InsightCategory.TREND]
        self.assertGreater(len(trend_insights), 0)
    
    def test_comparison_insight(self):
        """测试对比洞察"""
        engine = InsightEngine(self.df, self.column_types)
        insights = engine.generate_all()
        
        comparison_insights = [i for i in insights if i.category == InsightCategory.COMPARISON]
        # 可能生成也可能不生成，取决于数据分布
        for ci in comparison_insights:
            self.assertIn("Top", ci.title)
    
    def test_to_markdown(self):
        """测试 Markdown 输出"""
        engine = InsightEngine(self.df, self.column_types)
        insights = engine.generate_all()
        markdown = engine.to_markdown(top_n=5)
        
        self.assertIn("数据洞察", markdown)
        self.assertIn(insights[0].title, markdown)


class TestDataCleaner(unittest.TestCase):
    """测试数据清洗引擎"""
    
    def setUp(self):
        # 创建有问题的数据
        self.df = pd.DataFrame({
            "A": [1, 2, None, 4, 5, 2, 7, 8, 9, 1000],  # 有缺失值和异常值
            "B": ["x", "y", "z", "x", "y", "z", "x", "y", "z", "x"],
            "C": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        })
    
    def test_auto_clean(self):
        """测试自动清洗"""
        cleaner = DataCleaner(self.df)
        cleaned = cleaner.auto_clean()
        
        # 不应该有缺失值
        self.assertEqual(cleaned.isnull().sum().sum(), 0)
        # 重复行应该被处理
        # 异常值应该被处理
    
    def test_cleaning_report(self):
        """测试清洗报告"""
        cleaner = DataCleaner(self.df)
        cleaner.auto_clean()
        report = cleaner.get_cleaning_report()
        
        self.assertIn("original_shape", report)
        self.assertIn("cleaned_shape", report)
        self.assertIn("suggestions", report)
    
    def test_aggressive_clean(self):
        """测试激进清洗"""
        # 创建高缺失率列
        df = pd.DataFrame({
            "A": [1, None, None, None, None, None, None, None, None, None],
            "B": list(range(10)),
        })
        cleaner = DataCleaner(df)
        cleaned = cleaner.auto_clean(aggressive=True)
        
        # A列应该被删除（缺失率90% > 50%）
        self.assertNotIn("A", cleaned.columns)


class TestMultiDimensionAnalyzer(unittest.TestCase):
    """测试多维度分析引擎"""
    
    def setUp(self):
        np.random.seed(42)
        self.df = pd.DataFrame({
            "日期": pd.date_range("2024-01-01", periods=100, freq="D"),
            "销售额": np.random.normal(5000, 2000, 100).clip(1000, 15000),
            "订单数": np.random.poisson(50, 100),
            "地区": np.random.choice(["华东", "华南", "华北", "西南"], 100),
            "产品": np.random.choice(["A", "B", "C"], 100),
        })
        self.column_types = {
            "日期": "datetime",
            "销售额": "numeric",
            "订单数": "numeric",
            "地区": "categorical",
            "产品": "categorical",
        }
    
    def test_cross_analysis(self):
        """测试交叉分析"""
        analyzer = MultiDimensionAnalyzer(self.df, self.column_types)
        results = analyzer.analyze(AnalysisType.CROSS)
        
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertEqual(r.analysis_type, AnalysisType.CROSS)
            self.assertIn("total", r.metrics)
    
    def test_rank_analysis(self):
        """测试排名分析"""
        analyzer = MultiDimensionAnalyzer(self.df, self.column_types)
        results = analyzer.analyze(AnalysisType.RANK)
        
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertEqual(r.analysis_type, AnalysisType.RANK)
            self.assertIn("top1_share", r.metrics)
    
    def test_compare_analysis(self):
        """测试对比分析"""
        analyzer = MultiDimensionAnalyzer(self.df, self.column_types)
        results = analyzer.analyze(AnalysisType.COMPARE)
        
        if len(results) > 0:
            self.assertEqual(results[0].analysis_type, AnalysisType.COMPARE)
    
    def test_all_analysis(self):
        """测试全部分析"""
        analyzer = MultiDimensionAnalyzer(self.df, self.column_types)
        results = analyzer.analyze()
        
        self.assertGreater(len(results), 0)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestInsightEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestDataCleaner))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiDimensionAnalyzer))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
