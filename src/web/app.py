"""
Web界面 — Gradio 数据叙事应用
"""

import gradio as gr
import pandas as pd
from pathlib import Path

from src.pipeline import DataNarrativePipeline


def create_app():
    """创建 Gradio 应用"""
    
    pipeline = DataNarrativePipeline(max_charts=4)
    
    def process_data(file, narrative_hint):
        """处理上传的文件"""
        if file is None:
            return "请先上传数据文件", None, None
        
        try:
            result = pipeline.run(file.name, narrative_hint=narrative_hint or None)
            
            # 读取生成的报告
            report_path = Path(result['report_path'])
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    report_html = f.read()
            else:
                report_html = "报告生成失败"
            
            summary = f"""
## 处理结果

- **状态**: ✅ 成功
- **叙事策略**: {result['strategy']['title'] or '通用分析'}
- **策略置信度**: {result['strategy']['confidence']:.0%}
- **生成图表**: {result['charts_count']} 张
- **报告路径**: {result['report_path']}

### 数据概览
- 行数: {result['data_profile']['rows']:,}
- 列数: {result['data_profile']['columns']}
- 类型分布: {result['data_profile']['type_distribution']}

### 质量评分
- 等级: {result['quality']['grade']}
- 得分: {result['quality']['overall_score']:.1%}
- 发现问题: {result['quality']['summary']['issue_count']} 个
"""
            return summary, report_html, str(report_path)
            
        except Exception as e:
            return f"❌ 处理失败: {str(e)}", None, None
    
    # Gradio 界面
    with gr.Blocks(title="AI数据叙事系统", css="""
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; padding: 20px; }
        .header h1 { color: #2c3e50; }
    """) as app:
        
        gr.HTML("""
        <div class="header">
            <h1>🎨 AI数据叙事系统</h1>
            <p>上传数据，自动生成可视化报告与数据洞察</p>
        </div>
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📥 数据上传")
                file_input = gr.File(
                    label="上传数据文件 (CSV/Excel/JSON)",
                    file_types=[".csv", ".xlsx", ".xls", ".json"]
                )
                hint_input = gr.Textbox(
                    label="叙事意图 (可选)",
                    placeholder="例如：分析销售趋势、对比各区域表现...",
                    lines=2
                )
                process_btn = gr.Button("🚀 生成报告", variant="primary")
                
                gr.Markdown("### 📋 处理摘要")
                summary_output = gr.Markdown()
                
                report_path_output = gr.Textbox(
                    label="报告文件路径",
                    interactive=False
                )
            
            with gr.Column(scale=2):
                gr.Markdown("### 📄 生成报告")
                report_output = gr.HTML()
        
        process_btn.click(
            fn=process_data,
            inputs=[file_input, hint_input],
            outputs=[summary_output, report_output, report_path_output]
        )
        
        gr.Markdown("""
        ---
        <div style="text-align: center; color: #999; font-size: 0.8em;">
            AI数据叙事系统 | 自动数据可视化与报告生成
        </div>
        """)
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
