"""
Web界面增强 — 实时分析、交互式图表、多步骤工作流

使用方式:
    python src/web/enhanced_app.py
"""

import gradio as gr
import pandas as pd
from pathlib import Path
import json
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.pipeline import DataNarrativePipeline
from src.monitoring.logger import HealthChecker
from src.config import LLM_CONFIG


def create_enhanced_app():
    """创建增强版 Gradio 应用"""
    
    # 健康检查
    health = HealthChecker().check_all()
    
    # 存储会话状态
    session_state = {}
    
    # 检查 LLM 配置状态
    llm_api_key = LLM_CONFIG.get("api_key", "")
    llm_configured = bool(llm_api_key and llm_api_key != "your-api-key-here")
    
    def process_data(file, narrative_hint, auto_clean, advanced_charts, 
                     storytelling, publish, llm_enhance, progress=gr.Progress()):
        """处理上传的文件，带进度反馈"""
        if file is None:
            return (
                "⚠️ 请先上传数据文件", 
                "", 
                "<p>无数据</p>", 
                "", 
                "",
                "未开始"
            )
        
        logs = []
        
        def log(msg):
            logs.append(msg)
            print(f"[WEB] {msg}")
        
        try:
            # 步骤 1: 初始化
            progress(0.05, desc="📦 初始化流水线...")
            log("开始初始化数据叙事流水线")
            
            # 检查 LLM 状态
            llm_status_text = ""
            if llm_enhance:
                if llm_configured:
                    llm_status_text = "✅ LLM 增强已启用 | API 已配置"
                    log("LLM 增强已启用，API 已配置")
                else:
                    llm_status_text = "⚠️ LLM 增强已启用 | 但 API 未配置，将降级为模板生成"
                    log("LLM 增强已启用，但 API 未配置，将降级为模板生成")
            else:
                llm_status_text = "❌ LLM 增强未启用"
                log("LLM 增强未启用")
            
            # 步骤 2: 构建流水线
            progress(0.15, desc="🔧 构建分析流水线...")
            log(f"构建流水线: 自动清洗={auto_clean}, 高级图表={advanced_charts}, 故事={storytelling}, 发布={publish}")
            
            pipeline = DataNarrativePipeline(
                max_charts=4,
                auto_clean=auto_clean,
                enable_advanced_charts=advanced_charts,
                enable_storytelling=storytelling,
                enable_publishing=publish,
                enable_llm_enhance=llm_enhance,
                enable_monitoring=True
            )
            
            # 步骤 3: 运行分析
            progress(0.30, desc="📊 正在分析数据（这可能需要一些时间）...")
            log(f"开始分析文件: {file.name}")
            
            result = pipeline.run(file.name, narrative_hint=narrative_hint or None)
            session_state["last_result"] = result
            
            # 步骤 4: 读取报告
            progress(0.75, desc="📄 生成报告...")
            log("分析完成，正在读取报告")
            
            report_path = Path(result['report_path'])
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    report_html = f.read()
            else:
                report_html = "<p>报告生成失败</p>"
            
            # 步骤 5: 构建数据预览
            progress(0.85, desc="🔍 构建数据预览...")
            try:
                df = pd.read_csv(file.name) if file.name.endswith('.csv') else pd.read_excel(file.name)
                preview = df.head(10).to_html(classes="data-table", index=False)
            except:
                preview = "<p>无法预览数据</p>"
            
            # 步骤 6: 构建性能指标
            progress(0.90, desc="📈 汇总结果...")
            
            perf = result.get('performance', {})
            if perf and perf.get('status') == 'success':
                mem = perf.get('memory', {})
                perf_text = f"""
**性能指标**
- 内存峰值: {mem.get('peak_mb', 0):.1f} MB
- 内存平均: {mem.get('avg_mb', 0):.1f} MB
- 总耗时: {perf.get('elapsed_seconds', 0):.1f} 秒
"""
            else:
                perf_text = "**性能指标**: 未启用监控"
            
            # 构建 LLM 详细状态
            llm_detail = ""
            if llm_enhance and result.get('report_summary'):
                llm_detail = f"\n- **LLM 报告摘要**: {result['report_summary'][:80]}..."
            
            # ML 分析结果
            ml_text = ""
            if result.get('ml_analysis'):
                ml = result['ml_analysis']
                ml_parts = []
                if ml.get('anomalies'):
                    ml_parts.append(f"异常检测: {len(ml['anomalies'])} 列")
                if ml.get('clusters'):
                    ml_parts.append(f"聚类: {ml['clusters']['n_clusters']} 类")
                if ml.get('prediction'):
                    ml_parts.append(f"预测: {ml['prediction']['horizon']} 步")
                if ml.get('feature_importance'):
                    ml_parts.append(f"特征重要性: {len(ml['feature_importance'])} 个")
                if ml_parts:
                    ml_text = f"\n- **ML 分析**: {' | '.join(ml_parts)}"
            
            summary = f"""
## ✅ 处理完成

### 配置状态
- {llm_status_text}

### 分析结果
- **叙事策略**: {result['strategy']['title'] or '通用分析'}
- **策略得分**: {result['strategy'].get('score', 0):.2f}
- **生成图表**: {result['charts_count']} 张
- **数据洞察**: {result['insights_count']} 条
- **多维分析**: {result['analysis_count']} 项
- **故事章节**: {result.get('story_sections', 0)} 个
- **平台适配**: {', '.join(result.get('platforms', []))}{ml_text}

### 数据概览
- 行数: {result['data_profile']['rows']:,}
- 列数: {result['data_profile']['columns']}
- 类型分布: {result['data_profile']['type_distribution']}

### 质量评分
- 等级: {result['quality']['grade']}
- 得分: {result['quality']['overall_score']:.1%}
- 发现问题: {result['quality']['summary']['issue_count']} 个

{perf_text}
{llm_detail}
"""
            
            # 运行日志
            log_text = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(logs)])
            
            progress(1.0, desc="✅ 完成!")
            return summary, report_html, preview, str(report_path), json.dumps(result, indent=2, default=str), log_text
            
        except Exception as e:
            error_msg = f"❌ 处理失败: {str(e)}"
            log(f"错误: {str(e)}")
            log_text = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(logs)])
            return error_msg, None, None, None, None, log_text
    
    def get_insights_detail():
        """获取洞察详情"""
        result = session_state.get("last_result", {})
        insights = result.get('insights', [])
        if not insights:
            return "暂无洞察数据，请先运行分析"
        return "\n\n".join([f"{i+1}. {insight}" for i, insight in enumerate(insights)])
    
    def get_platform_content(platform):
        """获取平台适配内容"""
        result = session_state.get("last_result", {})
        report_path = result.get('report_path', '')
        if not report_path:
            return "请先运行分析"
        
        output_dir = Path(report_path).parent
        platform_file = output_dir / f"{platform}_*.md"
        files = list(output_dir.glob(f"{platform}_*.md"))
        if files:
            with open(files[0], "r", encoding="utf-8") as f:
                return f.read()
        return f"未找到 {platform} 的适配内容"
    
    # CSS 样式 — 确保界面不会变窄
    css = """
        .gradio-container { max-width: 95% !important; margin: 0 auto; }
        .header { text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { color: white; margin: 0; }
        .data-table { font-size: 0.85em; border-collapse: collapse; width: 100%; }
        .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .data-table th { background-color: #667eea; color: white; }
        .data-table tr:nth-child(even) { background-color: #f9f9f9; }
        .log-box { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; padding: 10px; font-family: monospace; font-size: 0.85em; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
    """
    
    # Gradio 界面 — 使用 fill_width=True 防止变窄
    with gr.Blocks(
        title="AI数据叙事系统 v5.0", 
        css=css,
        fill_width=True,
        theme=gr.themes.Soft()
    ) as app:
        
        gr.HTML("""
        <div class="header">
            <h1>🎨 AI数据叙事系统 v5.0</h1>
            <p>从数据到故事 — 全自动化数据叙事流水线</p>
        </div>
        """)
        
        # 系统状态栏
        with gr.Row():
            status_items = []
            for name, check in health.get('checks', {}).items():
                status = check['status']
                icon = '✅' if status == 'ok' else '⚠️' if status == 'warning' else '❌'
                status_items.append(f"{icon} {name}")
            gr.Markdown(f"**系统状态**: {' | '.join(status_items[:6])}")
        
        # LLM 配置提示
        if not llm_configured:
            gr.HTML("""
            <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 12px; margin: 10px 0;">
                <strong>⚠️ 提示：</strong>LLM API Key 未配置。如需使用 LLM 增强功能，请在项目根目录的 <code>.env</code> 文件中设置 <code>LLM_API_KEY</code>。
                当前 LLM 增强将降级为模板生成。
            </div>
            """)
        
        with gr.Tabs():
            # 主分析 Tab
            with gr.TabItem("📊 数据分析"):
                with gr.Row():
                    # 左侧控制面板
                    with gr.Column(scale=1, min_width=320):
                        gr.Markdown("### 📥 数据上传")
                        file_input = gr.File(
                            label="上传数据文件",
                            file_types=[".csv", ".xlsx", ".xls", ".json"]
                        )
                        hint_input = gr.Textbox(
                            label="叙事意图 (可选)",
                            placeholder="例如：分析销售趋势、对比各区域表现...",
                            lines=2
                        )
                        
                        gr.Markdown("### ⚙️ 分析选项")
                        with gr.Group():
                            auto_clean = gr.Checkbox(label="自动清洗数据", value=False)
                            advanced_charts = gr.Checkbox(label="生成高级图表", value=True)
                            storytelling = gr.Checkbox(label="生成数据故事", value=True)
                            publish = gr.Checkbox(label="生成平台适配", value=True)
                            llm_enhance = gr.Checkbox(
                                label="LLM 增强 (需API Key)", 
                                value=False,
                                info="当前配置状态: " + ("✅ 已配置" if llm_configured else "⚠️ 未配置")
                            )
                        
                        process_btn = gr.Button("🚀 开始分析", variant="primary", size="lg")
                        
                        gr.Markdown("### 📋 处理摘要")
                        summary_output = gr.Markdown()
                        
                        report_path_output = gr.Textbox(
                            label="报告文件路径",
                            interactive=False
                        )
                    
                    # 右侧结果展示
                    with gr.Column(scale=3, min_width=500):
                        with gr.Tabs():
                            with gr.TabItem("📄 报告"):
                                report_output = gr.HTML()
                            with gr.TabItem("🔍 数据预览"):
                                preview_output = gr.HTML()
                            with gr.TabItem("📋 原始结果"):
                                raw_output = gr.Code(language="json")
                            with gr.TabItem("📝 运行日志"):
                                log_output = gr.Textbox(
                                    label="",
                                    interactive=False,
                                    lines=15,
                                    max_lines=30
                                )
            
            # 洞察 Tab
            with gr.TabItem("💡 洞察详情"):
                insights_btn = gr.Button("📋 加载洞察")
                insights_output = gr.Markdown()
                insights_btn.click(fn=get_insights_detail, outputs=insights_output)
            
            # 平台发布 Tab
            with gr.TabItem("📱 平台发布"):
                with gr.Row():
                    platform_select = gr.Dropdown(
                        choices=["xiaohongshu", "wechat_mp", "markdown"],
                        label="选择平台",
                        value="xiaohongshu"
                    )
                    load_btn = gr.Button("加载内容")
                platform_output = gr.Markdown()
                load_btn.click(fn=get_platform_content, inputs=platform_select, outputs=platform_output)
            
            # 帮助 Tab
            with gr.TabItem("❓ 帮助"):
                gr.Markdown(f"""
## 使用指南

### 1. LLM 配置状态
{'✅ **LLM 已配置** — 可以正常使用 LLM 增强功能' if llm_configured else '⚠️ **LLM 未配置** — 请在 `.env` 文件中设置 `LLM_API_KEY`'}

### 2. 数据上传
支持 CSV、Excel、JSON 格式。文件大小建议不超过 100MB。

### 3. 分析选项
- **自动清洗**: 自动处理缺失值、异常值和重复值
- **高级图表**: 生成箱线图、热力图、散点图矩阵等高级图表
- **数据故事**: 自动生成叙事化的数据故事章节
- **平台适配**: 生成小红书、微信公众号适配的内容格式
- **LLM 增强**: 使用大模型增强洞察和故事（需要配置 API Key）

### 4. CLI 使用
```bash
python run.py data.csv --auto-clean --llm-enhance
```

### 5. 健康检查
```bash
python run.py --health-check
```
                """)
        
        process_btn.click(
            fn=process_data,
            inputs=[file_input, hint_input, auto_clean, advanced_charts, 
                    storytelling, publish, llm_enhance],
            outputs=[summary_output, report_output, preview_output, report_path_output, raw_output, log_output]
        )
        
        gr.Markdown("""
        ---
        <div style="text-align: center; color: #999; font-size: 0.8em;">
            AI数据叙事系统 v5.0 | 全自动化数据可视化与报告生成
        </div>
        """)
    
    return app


if __name__ == "__main__":
    app = create_enhanced_app()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
