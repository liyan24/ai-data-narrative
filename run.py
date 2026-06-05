"""
AI数据叙事系统 v6.0 — 快捷运行入口

使用方式:
    python run.py data/sales_data.csv
    python run.py data/customer_data.csv --user-input "我是电商运营，想分析销售趋势"
    python run.py data/employee_data.xlsx --output ./my_reports --max-charts 3
    python run.py sqlite:///data/orders.db --user-input "分析订单数据"

环境变量 (.env):
    LLM_BASE_URL    大模型 API 地址 (默认: https://api.moonshot.cn/v1)
    LLM_API_KEY     大模型 API Key
    LLM_MODEL       模型名称 (默认: kimi-latest)
    LLM_TEMPERATURE 采样温度 (默认: 0.3)
    LLM_MAX_TOKENS  最大输出长度 (默认: 4096)
    SKILL_MAX_WORKERS 并行执行线程数 (默认: 4)
    SKILL_PARALLEL    启用并行执行 (默认: true)
    VIZ_FONT          图表字体 (默认: SimHei)
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
    
    parser = argparse.ArgumentParser(
        description="AI数据叙事系统 v6.0 — 大模型驱动的全自动数据叙事流水线"
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help="数据源路径 (CSV/Excel/JSON/JSON Lines/Parquet/SQLite/URL/数据库连接字符串)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出目录 (默认: output/)"
    )
    parser.add_argument(
        "--user-input", "-u",
        default=None,
        help="用户需求描述 (如: 我是电商运营，想分析销售趋势)"
    )
    parser.add_argument(
        "--max-charts", "-c",
        type=int,
        default=5,
        help="最大图表数量 (默认: 5)"
    )
    parser.add_argument(
        "--no-user-intent",
        action="store_true",
        help="禁用用户意图理解 (跳过 Phase 0，使用默认画像)"
    )
    parser.add_argument(
        "--no-skill-director",
        action="store_true",
        help="禁用技能导演 (跳过 Phase 2，使用默认执行计划)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="禁用并行执行 (串行执行所有技能)"
    )
    parser.add_argument(
        "--no-llm-cache",
        action="store_true",
        help="禁用 LLM 缓存 (每次调用都请求 API)"
    )
    parser.add_argument(
        "--auto-clean",
        action="store_true",
        help="启用数据自动清洗"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出执行日志"
    )
    parser.add_argument(
        "--generate-skill",
        default=None,
        help="触发动态技能生成 (如: geo-heatmap, text-analysis)"
    )
    
    args = parser.parse_args()
    
    # 检查数据源
    if not args.source:
        print("[ERROR] 需要提供数据源路径")
        print("\n用法示例:")
        print("  python run.py data/sales_data.csv")
        print("  python run.py data/orders.db --user-input '分析订单数据'")
        print("  python run.py https://api.example.com/data.csv --user-input '分析用户行为'")
        print("  python run.py mysql://user:pass@host/db --user-input '分析销售数据'")
        print("\n支持的数据源:")
        print("  本地文件: CSV, Excel (.xlsx), JSON, JSON Lines (.jsonl), Parquet")
        print("  SQLite: .db, .sqlite, .sqlite3")
        print("  数据库连接: mysql://, postgresql://, mongodb://")
        print("  REST API: https://...")
        sys.exit(1)
    
    # 检查文件是否存在（本地文件）
    source_path = Path(args.source)
    is_local_file = (
        not args.source.startswith(("http://", "https://", "mysql://", "postgresql://", "mongodb://", "sqlite://"))
        and not args.source.startswith("mongodb://")
    )
    if is_local_file and not source_path.exists():
        print(f"[ERROR] 文件不存在: {source_path}")
        print("\n提示: 先运行示例数据生成")
        print("   python examples/generate_sample_data.py")
        sys.exit(1)
    
    # 初始化流水线
    pipeline = DataNarrativePipeline(
        max_charts=args.max_charts,
        output_dir=args.output,
        auto_clean=args.auto_clean,
        enable_user_intent=not args.no_user_intent,
        enable_skill_director=not args.no_skill_director,
        verbose=args.verbose,
    )
    
    # 执行分析
    print("=" * 60)
    print(f"[SOURCE] 数据源: {args.source}")
    if args.user_input:
        print(f"[USER]   用户需求: {args.user_input}")
    print("=" * 60)
    
    result = pipeline.run(
        str(args.source),
        user_input=args.user_input
    )
    
    # 输出结果摘要
    print("\n" + "=" * 60)
    print("[DONE] 处理完成!")
    print("=" * 60)
    
    phases = result.get("phases", {})
    
    # Phase 0: 用户意图
    if "user_intent" in phases and phases["user_intent"]:
        ui = phases["user_intent"]
        if isinstance(ui, dict):
            up = ui.get("user_profile", {})
            if isinstance(up, dict):
                print(f"[USER]   角色: {up.get('role', 'N/A')}")
                print(f"[USER]   行业: {up.get('industry', 'N/A')}")
                print(f"[USER]   目标: {up.get('goal', 'N/A')}")
    
    # Phase 1: 数据加载
    if "data_load" in phases and phases["data_load"]:
        dl = phases["data_load"]
        if isinstance(dl, dict):
            print(f"[DATA]   文件: {dl.get('file', 'N/A')}")
            print(f"[DATA]   维度: {dl.get('rows', 'N/A')} 行 x {dl.get('columns', 'N/A')} 列")
    
    # Phase 3: 技能执行
    if "skill_execution" in phases:
        se = phases["skill_execution"]
        if isinstance(se, dict):
            success = sum(1 for sr in se.values() if sr.get("status") == "success")
            failed = sum(1 for sr in se.values() if sr.get("status") == "error")
            skipped = sum(1 for sr in se.values() if sr.get("status") == "skipped")
            print(f"[SKILLS] 执行: {success} 成功, {failed} 失败, {skipped} 跳过")
            if args.verbose:
                for name, sr in se.items():
                    st = sr.get("status", "N/A")
                    meta = sr.get("metadata", {})
                    extra = ""
                    if "elapsed_seconds" in meta:
                        extra = f" ({meta['elapsed_seconds']}s)"
                    print(f"  [{st.upper()}] {name}{extra}")
    
    # 报告路径
    report_path = result.get("report_path")
    if not report_path:
        # Try to get from skill_execution -> report-builder
        rb = phases.get("skill_execution", {}).get("report-builder", {})
        if isinstance(rb, dict) and rb.get("data"):
            report_path = rb["data"].get("report_path")
    
    if report_path:
        print(f"[REPORT] 报告路径: {report_path}")
    
    # 性能
    perf = result.get("performance")
    if perf and isinstance(perf, dict):
        print(f"[PERF]   总耗时: {perf.get('total_elapsed_seconds', 'N/A')}s")
    
    # 输出目录
    output_dir = result.get("output_dir")
    if output_dir:
        print(f"[OUTPUT] 所有输出保存在: {output_dir}")
    
    print("=" * 60)
    
    # 动态技能生成测试（如果指定）
    if args.generate_skill:
        from src.skills.generator import SkillGenerator
        from src.skills.models import SkillContext
        from src.data_schema.models import DataProfile
        import pandas as pd
        
        print(f"\n[GENERATE] 触发动态技能生成: {args.generate_skill}")
        registry = pipeline.skill_registry
        generator = SkillGenerator(registry)
        
        # 创建测试上下文
        df = pd.DataFrame({"a": [1, 2, 3]})
        ctx = SkillContext(data_profile=DataProfile(df=df, source_name="test.csv"))
        
        generated = generator.generate(args.generate_skill, ctx, verbose=True)
        if generated:
            print(f"[GENERATE] 技能生成成功: {generated.name}")
            print(f"[GENERATE] 目录: {generated.skill_dir}")
            print(f"[GENERATE] 安全通过: {generated.security_passed}")
        else:
            print(f"[GENERATE] 技能生成失败或不需要生成")


if __name__ == "__main__":
    main()
