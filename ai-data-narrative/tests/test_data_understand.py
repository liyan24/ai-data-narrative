"""
数据理解层测试 — 验证统计特征提取

运行方式:
    python -m pytest tests/test_data_understand.py -v
    或: python tests/test_data_understand.py
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_understand.statistics import StatisticExtractor


class TestStatisticExtractor(unittest.TestCase):
    """测试统计特征提取器"""
    
    def setUp(self):
        """创建测试数据"""
        np.random.seed(42)
        self.df = pd.DataFrame({
            "数值A": np.random.normal(100, 15, 100),
            "数值B": np.random.normal(50, 10, 100),
            "类别": np.random.choice(["X", "Y", "Z"], 100),
            "日期": pd.date_range("2024-01-01", periods=100, freq="D"),
        })
    
    def test_extract_basic(self):
        """测试基础统计"""
        basic = StatisticExtractor.extract_basic(self.df)
        
        self.assertEqual(basic["row_count"], 100)
        self.assertEqual(basic["column_count"], 4)
        self.assertIn("memory_usage_mb", basic)
        self.assertIn("density", basic)
    
    def test_extract_numeric(self):
        """测试数值统计"""
        stats = StatisticExtractor.extract_numeric(self.df)
        
        self.assertIn("数值A", stats)
        self.assertIn("数值B", stats)
        
        for col in ["数值A", "数值B"]:
            self.assertIn("mean", stats[col])
            self.assertIn("std", stats[col])
            self.assertIn("min", stats[col])
            self.assertIn("max", stats[col])
            self.assertIn("skewness", stats[col])
    
    def test_extract_categorical(self):
        """测试类别统计"""
        stats = StatisticExtractor.extract_categorical(self.df)
        
        self.assertIn("类别", stats)
        self.assertIn("unique_count", stats["类别"])
        self.assertIn("most_frequent", stats["类别"])
        self.assertIn("top_values", stats["类别"])
    
    def test_extract_datetime(self):
        """测试日期统计"""
        stats = StatisticExtractor.extract_datetime(self.df)
        
        self.assertIn("日期", stats)
        self.assertIn("earliest", stats["日期"])
        self.assertIn("latest", stats["日期"])
        self.assertIn("span_days", stats["日期"])
    
    def test_extract_correlations(self):
        """测试相关性提取"""
        stats = StatisticExtractor.extract_correlations(self.df)
        
        self.assertTrue(stats["available"])
        self.assertIn("matrix", stats)
        self.assertIn("strong_pairs", stats)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestStatisticExtractor))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
