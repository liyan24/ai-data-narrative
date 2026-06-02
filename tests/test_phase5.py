"""
第五阶段测试 — Web界面增强、数据源扩展、ML分析、插件系统、多语言
"""

import unittest
import sys
import tempfile
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.web.enhanced_app import create_enhanced_app
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    create_enhanced_app = None
from src.data_input.connectors import DatabaseConnector, APIConnector, DataSourceManager, ConnectionConfig
from src.analysis.ml_engine import MLEngine, AdvancedAnalyzer, AnomalyResult, PredictionResult, ClusterResult
from src.plugins.manager import PluginManager, PluginBase, SamplePlugin, CustomInsightPlugin
from src.i18n.translator import Translator, _


class TestDataSourceConnectors(unittest.TestCase):
    """测试数据源连接器"""
    
    def test_sqlite_connector(self):
        """测试 SQLite 连接"""
        import sqlite3
        import gc
        import time
        db_path = f"test_sqlite_{time.time()}.db"
        
        try:
            # 创建测试数据
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER, name TEXT, value REAL)")
            conn.execute("DELETE FROM test")
            conn.execute("INSERT INTO test VALUES (1, 'A', 10.5)")
            conn.execute("INSERT INTO test VALUES (2, 'B', 20.3)")
            conn.commit()
            conn.close()
            
            connector = DatabaseConnector(f"sqlite:///{db_path}")
            with connector.connect():
                tables = connector.get_tables()
                self.assertIn("test", tables)
                
                df = connector.query("SELECT * FROM test")
                self.assertEqual(len(df), 2)
                self.assertEqual(df.columns.tolist(), ["id", "name", "value"])
            
            del connector
            gc.collect()
        finally:
            try:
                Path(db_path).unlink()
            except PermissionError:
                pass
    
    def test_api_connector(self):
        """测试 API 连接器（模拟）"""
        # 由于无法访问真实 API，测试解析逻辑
        connector = APIConnector("https://api.example.com")
        self.assertEqual(connector.base_url, "https://api.example.com")
        self.assertEqual(connector.headers, {})
    
    def test_data_source_manager(self):
        """测试数据源管理器"""
        import sqlite3
        import gc
        import time
        db_path = f"test_manager_{time.time()}.db"
        
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
            conn.execute("DELETE FROM test")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.commit()
            conn.close()
            
            manager = DataSourceManager()
            self.assertEqual(len(manager.list_sources()), 0)
            
            # 添加 SQLite 源
            manager.add_database("test_db", f"sqlite:///{db_path}")
            self.assertEqual(len(manager.list_sources()), 1)
            
            status = manager.test_connection("test_db")
            self.assertEqual(status["status"], "ok")
            
            del manager
            gc.collect()
        finally:
            try:
                Path(db_path).unlink()
            except PermissionError:
                pass


class TestMLEngine(unittest.TestCase):
    """测试 ML 分析引擎"""
    
    def setUp(self):
        np.random.seed(42)
        self.df = pd.DataFrame({
            'sales': np.random.normal(100, 20, 100),
            'orders': np.random.normal(50, 10, 100),
            'region': np.random.choice(['A', 'B', 'C'], 100),
            'date': pd.date_range('2024-01-01', periods=100)
        })
        # 添加一些异常值
        self.df.loc[10, 'sales'] = 500
        self.df.loc[20, 'sales'] = 600
        self.ml = MLEngine(self.df)
    
    def test_anomaly_detection(self):
        """测试异常检测"""
        results = self.ml.detect_anomalies(columns=['sales'], method='zscore')
        self.assertTrue(len(results) > 0)
        
        anomaly = results[0]
        self.assertEqual(anomaly.column, 'sales')
        self.assertTrue(len(anomaly.indices) > 0)
        self.assertIn(10, anomaly.indices)  # 我们插入的异常值
        self.assertIn(20, anomaly.indices)
    
    def test_prediction(self):
        """测试预测"""
        result = self.ml.predict('sales', horizon=7, method='linear')
        self.assertIsInstance(result, PredictionResult)
        self.assertEqual(result.column, 'sales')
        self.assertEqual(result.horizon, 7)
        self.assertEqual(len(result.predictions), 7)
        self.assertIsNotNone(result.confidence_interval)
    
    def test_cluster(self):
        """测试聚类"""
        result = self.ml.cluster(columns=['sales', 'orders'], n_clusters=3)
        if result:  # sklearn 可能未安装
            self.assertIsInstance(result, ClusterResult)
            self.assertEqual(result.n_clusters, 3)
            self.assertEqual(len(result.cluster_sizes), 3)
            self.assertEqual(len(result.labels), 100)
    
    def test_feature_importance(self):
        """测试特征重要性"""
        importance = self.ml.feature_importance('sales', ['orders'])
        self.assertIsInstance(importance, dict)
        if importance:  # sklearn 可能未安装
            self.assertIn('orders', importance)
    
    def test_advanced_analyzer(self):
        """测试高级分析器"""
        analyzer = AdvancedAnalyzer(self.df)
        results = analyzer.analyze_all(
            target_column='sales',
            segment_column='region'
        )
        
        self.assertIsInstance(results, dict)
        # 至少包含异常检测
        self.assertIn('anomalies', results)


class TestPluginSystem(unittest.TestCase):
    """测试插件系统"""
    
    def test_plugin_manager(self):
        """测试插件管理器"""
        manager = PluginManager()
        self.assertEqual(len(manager.plugins), 0)
        
        # 添加内置插件
        plugin = SamplePlugin()
        manager.plugins[plugin.name] = plugin
        manager.hooks["on_report"].append(plugin.on_report)
        
        self.assertEqual(len(manager.plugins), 1)
        self.assertEqual(len(manager.hooks["on_report"]), 1)
        
        # 列出插件
        plugins = manager.list_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]["name"], "watermark")
    
    def test_custom_plugin(self):
        """测试自定义插件"""
        plugin = CustomInsightPlugin()
        
        # 添加自定义规则
        def check_insights(insights):
            return len(insights) > 0
        
        plugin.add_rule("has_insights", check_insights)
        
        # 测试执行
        insights = [{'title': 'test'}]
        result = plugin.on_insight(insights)
        self.assertEqual(result, insights)
    
    def test_plugin_hooks(self):
        """测试钩子执行"""
        manager = PluginManager()
        
        # 添加插件
        plugin = SamplePlugin()
        manager.plugins[plugin.name] = plugin
        manager.hooks["on_report"].append(plugin.on_report)
        
        # 创建测试报告文件
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write("<html><body></body></html>")
            report_path = tmp.name
        
        try:
            # 运行钩子
            result = manager.run_hook("on_report", Path(report_path))
            self.assertEqual(result, Path(report_path))  # 插件返回相同路径
        finally:
            Path(report_path).unlink(missing_ok=True)


class TestI18n(unittest.TestCase):
    """测试国际化"""
    
    def test_chinese(self):
        """测试中文翻译"""
        t = Translator("zh")
        self.assertEqual(t("hello"), "你好")
        self.assertEqual(t("data_overview"), "数据概览")
        self.assertEqual(t("nonexistent_key"), "nonexistent_key")
    
    def test_english(self):
        """测试英文翻译"""
        t = Translator("en")
        self.assertEqual(t("hello"), "Hello")
        self.assertEqual(t("data_overview"), "Data Overview")
    
    def test_switch_locale(self):
        """测试切换语言"""
        t = Translator("zh")
        self.assertEqual(t("hello"), "你好")
        
        t.set_locale("en")
        self.assertEqual(t("hello"), "Hello")
    
    def test_available_locales(self):
        """测试可用语言列表"""
        t = Translator()
        locales = t.available_locales()
        self.assertIn("zh", locales)
        self.assertIn("en", locales)
    
    def test_shortcut(self):
        """测试快捷函数"""
        self.assertEqual(_("hello", "zh"), "你好")
        self.assertEqual(_("hello", "en"), "Hello")
    
    def test_translate_dict(self):
        """测试字典翻译"""
        t = Translator("zh")
        data = {"hello": "hello", "other": "other"}
        result = t.translate_dict(data, keys=["hello"])
        self.assertEqual(result["hello"], "你好")
        self.assertEqual(result["other"], "other")  # 未翻译


class TestWebEnhanced(unittest.TestCase):
    """测试增强 Web 界面"""
    
    @unittest.skipUnless(GRADIO_AVAILABLE, "gradio not installed")
    def test_app_creation(self):
        """测试应用创建"""
        app = create_enhanced_app()
        self.assertIsNotNone(app)
    
    def test_health_check(self):
        """测试健康检查"""
        from src.monitoring.logger import HealthChecker
        checker = HealthChecker()
        report = checker.check_all()
        self.assertIn("status", report)
        self.assertIn("checks", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
