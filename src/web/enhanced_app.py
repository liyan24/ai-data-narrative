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


def create_enhanced_app():
    """创建增强版 Gradio 应用"""
    
    # 健康检查
    health = HealthChecker().check_all()
    
    # 存储会话状态
    session_state = {}
    
    def process_data(file, narrative_hint, auto_clean, advanced_charts, 
                     storytelling, publish, llm_enhance):
        """处理上传的文件"""
        if file is None:
            return "请先上传数据文件", None, None, None, None
        
        try:
            pipeline = DataNarrativePipeline(
                max_charts=4,
                auto_clean=auto_clean,
                enable_advanced_charts=advanced_charts,
                enable_storytelling=storytelling,
                enable_publishing=publish,
                enable_llm_enhance=llm_enhance,
                enable_monitoring=True
            )
            
            result = pipeline.run(file.name, narrative_hint=narrative_hint or None)
            session_state["last_result"] = result
            
            # 读取生成的报告
            report_path = Path(result['report_path'])
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    report_html = f.read()
            else:
                report_html = "<p>报告生成失败</p>"
            
            # 构建数据预览
            try:
                df = pd.read_csv(file.name) if file.name.endswith('.csv') else pd.read_excel(file.name)
                preview = df.head(10).to_html(classes="data-table", index=False)
            except:
                preview = "<p>无法预览数据</p>"
            
            # 构建性能指标
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
            
            summary = f"""
## 处理结果

- **状态**: 成功
- **叙事策略**: {result['strategy']['title'] or '通用分析'}
- **策略得分**: {result['strategy'].get('score', 0):.2f}
- **生成图表**: {result['charts_count']} 张
- **数据洞察**: {result['insights_count']} 条
- **多维分析**: {result['analysis_count']} 项
- **故事章节**: {result.get('story_sections', 0)} 个
- **平台适配**: {', '.join(result.get('platforms', []))}

### 数据概览
- 行数: {result['data_profile']['rows']:,}
- 列数: {result['data_profile']['columns']}
- 类型分布: {result['data_profile']['type_distribution']}

### 质量评分
- 等级: {result['quality']['grade']}
- 得分: {result['quality']['overall_score']:.1%}
- 发现问题: {result['quality']['summary']['issue_count']} 个

{perf_text}
"""
            return summary, report_html, preview, str(report_path), json.dumps(result, indent=2, default=str)
            
        except Exception as e:
            return f"❌ 处理失败: {str(e)}", None, None, None, None
    
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
    
    # Gradio 界面
    with gr.Blocks(title="AI数据叙事系统 v4.0", css="""
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { color: white; margin: 0; }
        .step-box { border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin: 10px 0; background: #fafafa; }
        .data-table { font-size: 0.85em; border-collapse: collapse; width: 100%; }
        .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .data-table th { background-color: #667eea; color: white; }
        .data-table tr:nth-child(even) { background-color: #f9f9f9; }
    """) as app:
        
        gr.HTML("""
        <div class="header">
            <h1>🎨 AI数据叙事系统 v4.0</h1>
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
        
        with gr.Tabs():
            # 主分析 Tab
            with gr.TabItem("📊 数据分析"):
                with gr.Row():
                    # 左侧控制面板
                    with gr.Column(scale=1):
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
                        auto_clean = gr.Checkbox(label="自动清洗数据", value=False)
                        advanced_charts = gr.Checkbox(label="生成高级图表", value=True)
                        storytelling = gr.Checkbox(label="生成数据故事", value=True)
                        publish = gr.Checkbox(label="生成平台适配", value=True)
                        llm_enhance = gr.Checkbox(label="LLM 增强 (需API Key)", value=False)
                        
                        process_btn = gr.Button("🚀 开始分析", variant="primary")
                        
                        gr.Markdown("### 📋 处理摘要")
                        summary_output = gr.Markdown()
                        
                        report_path_output = gr.Textbox(
                            label="报告文件路径",
                            interactive=False
                        )
                    
                    # 右侧结果展示
                    with gr.Column(scale=2):
                        with gr.Tabs():
                            with gr.TabItem("📄 报告"):
                                report_output = gr.HTML()
                            with gr.TabItem("🔍 数据预览"):
                                preview_output = gr.HTML()
                            with gr.TabItem("📋 原始结果"):
                                raw_output = gr.Code(language="json")
            
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
                gr.Markdown("""
## 使用指南

### 1. 数据上传
支持 CSV、Excel、JSON 格式。文件大小建议不超过 100MB。

### 2. 分析选项
- **自动清洗**: 自动处理缺失值、异常值和重复值
- **高级图表**: 生成箱线图、热力图、散点图矩阵等高级图表
- **数据故事**: 自动生成叙事化的数据故事章节
- **平台适配**: 生成小红书、微信公众号适配的内容格式
- **LLM 增强**: 使用大模型增强洞察和故事（需要配置 API Key）

### 3. 查看结果
- **报告**: HTML 格式的完整分析报告
- **数据预览**: 前 10 行数据预览
- **洞察详情**: 所有数据洞察的详细列表
- **平台发布**: 查看各平台适配的内容

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
            outputs=[summary_output, report_output, preview_output, report_path_output, raw_output]
        )
        
        gr.Markdown("""
        ---
        <div style="text-align: center; color: #999; font-size: 0.8em;">
            AI数据叙事系统 v4.0 | 全自动化数据可视化与报告生成
        </div>
        """)
    
    return app


if __name__ == "__main__":
    app = create_enhanced_app()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
