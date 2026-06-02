"""
AI数据叙事系统 — 快捷运行入口

使用方式:
    python run.py data/sales_data.csv
    python run.py data/customer_data.csv --max-charts 3
    python run.py data/employee_data.xlsx --output ./my_reports

环境变量:
    LLM_API_KEY     大模型 API Key
    LLM_BASE_URL    大模型 API 地址 (默认: https://api.moonshot.cn/v1)
    LLM_MODEL       模型名称 (默认: kimi-latest)
"""

import sys
from pathlib import Path
import io

# 修复 Windows 控制台编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.pipeline import DataNarrativePipeline


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AI数据叙事系统")
    parser.add_argument("file", help="数据文件路径 (CSV/Excel/JSON)")
    parser.add_argument("--output", "-o", default=None, help="输出目录")
    parser.add_argument("--max-charts", "-c", type=int, default=5, help="最大图表数量")
    parser.add_argument("--hint", "-t", default=None, help="叙事意图提示")
    
    parser.add_argument("--auto-clean", action="store_true", help="启用自动清洗")
    parser.add_argument("--aggressive", action="store_true", help="激进清洗模式")
    
    # 第三阶段参数
    parser.add_argument("--no-advanced", action="store_true", help="禁用高级图表")
    parser.add_argument("--no-story", action="store_true", help="禁用数据故事")
    parser.add_argument("--no-publish", action="store_true", help="禁用平台发布适配")
    parser.add_argument("--sample", type=int, default=None, help="大数据采样分析（指定采样行数）")
    
    # 第四阶段参数
    parser.add_argument("--llm-enhance", action="store_true", help="启用 LLM 洞察增强（需要 API Key）")
    parser.add_argument("--no-monitor", action="store_true", help="禁用性能监控")
    parser.add_argument("--auto-publish", action="store_true", help="自动发布到已配置平台（需先配置）")
    parser.add_argument("--health-check", action="store_true", help="运行健康检查并退出")
    
    # 第五阶段参数
    parser.add_argument("--no-ml", action="store_true", help="禁用 ML 分析")
    parser.add_argument("--plugin-dir", default=None, help="插件目录")
    parser.add_argument("--locale", default="zh", choices=["zh", "en"], help="界面语言")
    parser.add_argument("--web", action="store_true", help="启动增强 Web 界面")
    parser.add_argument("--db", default=None, help="数据库连接字符串（如 sqlite:///data.db）")
    
    args = parser.parse_args()
    
    # 启动 Web 界面
    if args.web:
        from src.web.enhanced_app import create_enhanced_app
        app = create_enhanced_app()
        app.launch(server_name="0.0.0.0", server_port=7860, share=False)
        return
    
    # 检查文件是否存在
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[ERROR] 文件不存在: {file_path}")
        print("\n提示: 先运行示例数据生成")
        print("   python examples/generate_sample_data.py")
        sys.exit(1)
    
    # 处理健康检查
    if args.health_check:
        from src.monitoring.logger import HealthChecker
        checker = HealthChecker()
        report = checker.check_all()
        print("\n[HEALTH CHECK] 系统健康检查")
        print(f"整体状态: {report['status']}")
        print(f"检查项: {report['summary']['ok']} 正常, {report['summary']['warning']} 警告, {report['summary']['error']} 错误")
        for name, check in report['checks'].items():
            status = check['status']
            icon = 'OK' if status == 'ok' else 'WARN' if status == 'warning' else 'ERR'
            print(f"  [{icon}] {name}: {check.get('message', '')}")
        sys.exit(0)
    
    pipeline = DataNarrativePipeline(
        max_charts=args.max_charts,
        output_dir=args.output,
        auto_clean=args.auto_clean,
        aggressive_clean=args.aggressive,
        enable_advanced_charts=not args.no_advanced,
        enable_storytelling=not args.no_story,
        enable_publishing=not args.no_publish,
        sample_size=args.sample,
        enable_llm_enhance=args.llm_enhance,
        enable_monitoring=not args.no_monitor,
        enable_auto_publish=args.auto_publish,
        enable_ml_analysis=not args.no_ml,
        plugin_dir=args.plugin_dir,
        locale=args.locale
    )
    
    result = pipeline.run(str(file_path), narrative_hint=args.hint)
    
    print("\n" + "=" * 60)
    print("[DONE] 处理完成!")
    print(f"[REPORT] 报告路径: {result['report_path']}")
    print(f"[CHARTS] 生成图表: {result['charts_count']} 张")
    print(f"[INSIGHTS] 数据洞察: {result['insights_count']} 条")
    print(f"[ANALYSIS] 多维分析: {result['analysis_count']} 项")
    print(f"[STORY] 故事章节: {result.get('story_sections', 0)} 个")
    print(f"[PLATFORMS] 平台适配: {', '.join(result.get('platforms', []))}")
    print(f"[STRATEGY] 叙事策略: {result['strategy']['title']}")
    
    # 第四阶段输出
    if result.get('report_summary'):
        print(f"[SUMMARY] 报告摘要: {result['report_summary'][:100]}...")
    if result.get('performance') and result['performance'].get('status') == 'success':
        perf = result['performance']
        mem = perf.get('memory', {})
        print(f"[PERF] 内存峰值: {mem.get('peak_mb', 0):.1f} MB, 耗时: {perf.get('elapsed_seconds', 0):.1f}s")
    if args.llm_enhance:
        print("[LLM] LLM 增强已启用")
    
    # 第五阶段输出
    if result.get('ml_analysis'):
        ml = result['ml_analysis']
        ml_outputs = []
        if ml.get('anomalies'):
            ml_outputs.append(f"异常检测: {len(ml['anomalies'])} 列")
        if ml.get('clusters'):
            ml_outputs.append(f"聚类: {ml['clusters']['n_clusters']} 类")
        if ml.get('prediction'):
            ml_outputs.append(f"预测: {ml['prediction']['horizon']} 步")
        if ml.get('feature_importance'):
            ml_outputs.append(f"特征重要性: {len(ml['feature_importance'])} 个")
        if ml_outputs:
            print(f"[ML] {' | '.join(ml_outputs)}")
    
    print("=" * 60)
    print(f"[OUTPUT] 所有输出保存在: {Path(result['report_path']).parent}")
    print(f"[LOGS] 查看 logs/ 目录获取详细日志和性能报告")


if __name__ == "__main__":
    main()
