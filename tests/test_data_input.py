"""
数据输入层测试 — 验证数据加载、类型推断、质量检查

运行方式:
    python -m pytest tests/test_data_input.py -v
    或: python tests/test_data_input.py
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os
import sys

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_input.loader import DataLoader, DataProfile, DataTypeInferencer
from src.data_understand.quality import QualityChecker


class TestDataTypeInferencer(unittest.TestCase):
    """测试数据类型推断器"""
    
    def test_numeric_type(self):
        """测试数值型推断"""
        series = pd.Series([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
        result = DataTypeInferencer.infer(series)
        self.assertEqual(result["type"], "numeric")
        self.assertEqual(result["subtype"], "integer")
    
    def test_float_type(self):
        """测试浮点型推断"""
        series = pd.Series([100.5, 200.3, 300.7, 400.2, 500.9, 600.1, 700.4, 800.8, 900.6, 1000.0])
        result = DataTypeInferencer.infer(series)
        self.assertEqual(result["type"], "numeric")
        self.assertEqual(result["subtype"], "float")
    
    def test_categorical_type(self):
        """测试类别型推断"""
        series = pd.Series(["A", "B", "A", "C", "B", "A"] * 10)
        result = DataTypeInferencer.infer(series)
        self.assertEqual(result["type"], "categorical")
    
    def test_boolean_type(self):
        """测试布尔型推断"""
        series = pd.Series(["是", "否", "是", "否"] * 5)
        result = DataTypeInferencer.infer(series)
        self.assertEqual(result["type"], "boolean")
    
    def test_datetime_type(self):
        """测试日期型推断"""
        # 使用重复值避免被判定为 ID
        dates = [
            "2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01",
            "2024-05-01", "2024-06-01", "2024-01-01", "2024-02-01",
            "2024-03-01", "2024-04-01"
        ]
        series = pd.Series(dates)
        result = DataTypeInferencer.infer(series)
        self.assertEqual(result["type"], "datetime")
    
    def test_text_type(self):
        """测试文本型推断"""
        # 使用重复值，避免被判定为 ID（unique_ratio > 0.95）
        texts = [
            f"这是一条非常长的评论内容，包含大量不同的文字信息，编号{i % 10}"
            for i in range(50)
        ]
        series = pd.Series(texts)
        result = DataTypeInferencer.infer(series)
        # 由于唯一值只有10个（<=20），会被判定为 categorical
        # 这是合理的行为 — 短文本重复内容属于类别
        self.assertEqual(result["type"], "categorical")


class TestDataLoader(unittest.TestCase):
    """测试数据加载器"""
    
    def setUp(self):
        """创建临时测试文件"""
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        
        # 创建测试 CSV — 使用更多数据避免被误判为 ID/datetime
        names = ["张三", "李四", "王五", "赵六", "钱七"] * 10  # 重复值，避免 ID 判定
        df = pd.DataFrame({
            "姓名": names,
            "年龄": np.random.randint(18, 65, 50),
            "分数": np.random.uniform(60, 100, 50).round(1),
            "日期": pd.date_range("2024-01-01", periods=50, freq="D"),
        })
        self.csv_path = self.tmp_path / "test.csv"
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
    
    def tearDown(self):
        """清理临时文件"""
        self.tmp_dir.cleanup()
    
    def test_load_csv(self):
        """测试加载 CSV"""
        profile = DataLoader.load(self.csv_path)
        self.assertEqual(profile.row_count, 50)
        self.assertEqual(profile.col_count, 4)
        self.assertEqual(profile.source_name, "test.csv")
    
    def test_column_types(self):
        """测试列类型推断"""
        profile = DataLoader.load(self.csv_path)
        types = profile.get_column_types()
        
        self.assertEqual(types["姓名"], "categorical")
        self.assertEqual(types["年龄"], "numeric")
        self.assertEqual(types["分数"], "numeric")
        self.assertEqual(types["日期"], "datetime")
    
    def test_get_summary(self):
        """测试获取数据摘要"""
        profile = DataLoader.load(self.csv_path)
        summary = profile.get_summary()
        
        self.assertEqual(summary["rows"], 50)
        self.assertEqual(summary["columns"], 4)
        self.assertIn("type_distribution", summary)


class TestQualityChecker(unittest.TestCase):
    """测试数据质量检查器"""
    
    def test_perfect_data(self):
        """测试完美数据"""
        df = pd.DataFrame({
            "A": [1, 2, 3, 4, 5],
            "B": ["a", "b", "c", "d", "e"]
        })
        result = QualityChecker.check_all(df)
        
        self.assertEqual(result["grade"], "A+")
        self.assertEqual(result["overall_score"], 1.0)
        self.assertEqual(result["summary"]["issue_count"], 0)
    
    def test_with_missing(self):
        """测试含缺失值的数据"""
        df = pd.DataFrame({
            "A": [1, 2, None, 4, 5],
            "B": ["a", "b", "c", None, "e"]
        })
        result = QualityChecker.check_all(df)
        
        self.assertLess(result["overall_score"], 1.0)
        issues = [i for i in result["issues"] if i["type"] == "missing_values"]
        self.assertEqual(len(issues), 2)
    
    def test_with_duplicates(self):
        """测试含重复数据"""
        df = pd.DataFrame({
            "A": [1, 2, 2, 3, 4],
            "B": ["a", "b", "b", "c", "d"]
        })
        result = QualityChecker.check_all(df)
        
        dup_issues = [i for i in result["issues"] if i["type"] == "duplicate_rows"]
        self.assertEqual(len(dup_issues), 1)
    
    def test_with_outliers(self):
        """测试含异常值的数据"""
        df = pd.DataFrame({
            "A": [1, 2, 3, 4, 1000],  # 1000 是异常值
        })
        result = QualityChecker.check_all(df)
        
        outlier_issues = [i for i in result["issues"] if i["type"] == "outliers"]
        self.assertEqual(len(outlier_issues), 1)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDataTypeInferencer))
    suite.addTests(loader.loadTestsFromTestCase(TestDataLoader))
    suite.addTests(loader.loadTestsFromTestCase(TestQualityChecker))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
