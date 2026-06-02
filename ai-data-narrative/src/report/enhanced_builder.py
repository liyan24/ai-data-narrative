"""
增强报告模板系统 — 支持洞察、多维度分析、清洗记录

核心能力：
- 自动插入洞察卡片
- 多维度分析表格
- 清洗记录展示
- 交互式图表
- 导出 HTML / Markdown
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import base64

from src.config import REPORT_CONFIG, OUTPUT_DIR
from src.insights.engine import DataInsight, InsightSeverity
from src.analysis.engine import AnalysisResult, AnalysisType


class EnhancedReportBuilder:
    """增强报告构建器"""
    
    def __init__(self, title: str = None, author: str = None):
        self.title = title or REPORT_CONFIG["title"]
        self.author = author or REPORT_CONFIG["author"]
        self.sections: List[Dict[str, Any]] = []
        self.insights: List[DataInsight] = []
        self.analysis_results: List[AnalysisResult] = []
        self.cleaning_log: List[str] = []
    
    def add_insights(self, insights: List[DataInsight]):
        """添加数据洞察"""
        self.insights = insights
        for insight in insights:
            self.sections.append({
                "type": "insight",
                "heading": insight.title,
                "level": 3,
                "content": insight.description,
                "severity": insight.severity.value,
                "category": insight.category.value,
                "recommendation": insight.recommendation,
                "metric": insight.metric,
                "value": insight.value
            })
    
    def add_analysis(self, results: List[AnalysisResult]):
        """添加多维度分析结果"""
        self.analysis_results = results
        for result in results:
            self.sections.append({
                "type": "analysis",
                "heading": result.title,
                "level": 3,
                "content": result.description,
                "analysis_type": result.analysis_type.value,
                "data": result.data,
                "metrics": result.metrics,
                "insights": result.insights
            })
    
    def add_cleaning_log(self, log: List[str]):
        """添加清洗记录"""
        self.cleaning_log = log
        if log:
            self.sections.append({
                "type": "cleaning",
                "heading": "数据清洗记录",
                "level": 3,
                "content": "\n".join(log)
            })
    
    def add_chart(self, chart_base64: str, title: str, description: str = ""):
        """添加图表"""
        self.sections.append({
            "type": "chart",
            "heading": title,
            "level": 3,
            "content": description,
            "chart_data": chart_base64
        })
    
    def add_text(self, heading: str, content: str, level: int = 2):
        """添加文本"""
        self.sections.append({
            "type": "text",
            "heading": heading,
            "level": level,
            "content": content
        })
    
    def to_html(self) -> str:
        """生成 HTML 报告"""
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='zh-CN'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            f"    <title>{self.title}</title>",
            "    <style>",
            self._get_css(),
            "    </style>",
            "</head>",
            "<body>",
            "    <div class='report-container'>",
            f"        <h1>{self.title}</h1>",
            f"        <div class='meta'>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 生成工具: {self.author}</div>",
        ]
        
        for section in self.sections:
            html_parts.append(self._render_section(section))
        
        html_parts.extend([
            "        <div class='footer'>由 AI数据叙事系统 自动生成</div>",
            "    </div>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_parts)
    
    def _get_css(self) -> str:
        """获取 CSS 样式"""
        return """
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; line-height: 1.6; max-width: 1000px; margin: 0 auto; padding: 20px; color: #333; background: #f5f5f5; }
        .report-container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 15px; }
        h3 { color: #555; margin-top: 20px; }
        .meta { color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px; }
        .chart-container { text-align: center; margin: 20px 0; padding: 15px; background: #fafafa; border-radius: 6px; }
        .chart-container img { max-width: 100%; height: auto; border-radius: 4px; }
        .chart-title { font-weight: bold; color: #2c3e50; margin-bottom: 8px; }
        .chart-desc { color: #666; font-size: 0.9em; }
        .insight-box { background: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; border-radius: 4px; }
        .insight-box.warning { background: #fff3e0; border-left-color: #ff9800; }
        .insight-box.critical { background: #ffebee; border-left-color: #f44336; }
        .insight-box.high { background: #fce4ec; border-left-color: #e91e63; }
        .insight-box.low { background: #f3e5f5; border-left-color: #9c27b0; }
        .insight-header { font-weight: bold; margin-bottom: 8px; }
        .insight-category { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 10px; }
        .insight-category.trend { background: #e3f2fd; color: #1976d2; }
        .insight-category.distribution { background: #f3e5f5; color: #7b1fa2; }
        .insight-category.comparison { background: #e8f5e9; color: #388e3c; }
        .insight-category.relationship { background: #fff3e0; color: #f57c00; }
        .insight-category.composition { background: #fce4ec; color: #c2185b; }
        .insight-category.anomaly { background: #ffebee; color: #d32f2f; }
        .insight-recommendation { margin-top: 10px; padding: 8px; background: rgba(255,255,255,0.7); border-radius: 4px; font-size: 0.9em; }
        .analysis-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        .analysis-table th, .analysis-table td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        .analysis-table th { background: #f8f9fa; font-weight: bold; }
        .analysis-table tr:nth-child(even) { background: #f8f9fa; }
        .analysis-metrics { display: flex; gap: 15px; margin: 10px 0; flex-wrap: wrap; }
        .metric-badge { background: #e3f2fd; padding: 5px 12px; border-radius: 15px; font-size: 0.85em; }
        .cleaning-log { background: #f5f5f5; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 0.9em; white-space: pre-wrap; }
        .footer { text-align: center; color: #999; font-size: 0.8em; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }
        """
    
    def _render_section(self, section: Dict) -> str:
        """渲染单个章节"""
        t = section["type"]
        
        if t == "text":
            tag = f"h{section['level']}"
            return f"        <{tag}>{section['heading']}</{tag}>\n        <p>{section['content']}</p>"
        
        elif t == "chart":
            return f"""        <div class='chart-container'>
            <div class='chart-title'>{section['heading']}</div>
            <div class='chart-desc'>{section.get('content', '')}</div>
            <img src="data:image/png;base64,{section['chart_data']}" alt="{section['heading']}">
        </div>"""
        
        elif t == "insight":
            severity = section.get("severity", "info")
            category = section.get("category", "general")
            recommendation = section.get("recommendation", "")
            metric = section.get("metric", "")
            value = section.get("value", "")
            
            rec_html = f"<div class='insight-recommendation'>💡 建议: {recommendation}</div>" if recommendation else ""
            metric_html = f"<div><strong>指标:</strong> {metric} = {value}</div>" if metric else ""
            
            return f"""        <div class='insight-box {severity}'>
            <div class='insight-header'>
                {section['heading']}
                <span class='insight-category {category}'>{category}</span>
            </div>
            <p>{section['content']}</p>
            {metric_html}
            {rec_html}
        </div>"""
        
        elif t == "analysis":
            data = section.get("data", {})
            metrics = section.get("metrics", {})
            insights = section.get("insights", [])
            
            # 渲染数据表格
            table_html = ""
            if isinstance(data, dict):
                table_html = self._dict_to_html_table(data)
            
            # 渲染指标
            metrics_html = ""
            if metrics:
                badges = [f"<span class='metric-badge'>{k}: {v}</span>" for k, v in metrics.items()]
                metrics_html = f"<div class='analysis-metrics'>{' '.join(badges)}</div>"
            
            # 渲染洞察
            insights_html = ""
            if insights:
                insights_html = "<ul>" + "".join([f"<li>{i}</li>" for i in insights]) + "</ul>"
            
            return f"""        <h3>{section['heading']}</h3>
        <p>{section['content']}</p>
        {metrics_html}
        {insights_html}
        {table_html}"""
        
        elif t == "cleaning":
            return f"""        <h3>{section['heading']}</h3>
        <div class='cleaning-log'>{section['content']}</div>"""
        
        return ""
    
    def _dict_to_html_table(self, data: Dict) -> str:
        """将字典转换为 HTML 表格"""
        if not data:
            return ""
        
        # 尝试找到二维结构
        first_key = list(data.keys())[0]
        first_val = data[first_key]
        
        if isinstance(first_val, dict):
            # 嵌套字典 → 二维表格
            headers = [""] + list(first_val.keys())
            rows = []
            for k, v in data.items():
                row = [str(k)] + [str(v.get(h, "")) for h in headers[1:]]
                rows.append(row)
            
            thead = "<tr>" + "".join([f"<th>{h}</th>" for h in headers]) + "</tr>"
            tbody = ""
            for row in rows[:10]:  # 最多10行
                tbody += "<tr>" + "".join([f"<td>{c}</td>" for c in row]) + "</tr>"
            
            return f"<table class='analysis-table'>{thead}{tbody}</table>"
        else:
            # 简单字典 → 键值对表格
            rows = ""
            for k, v in list(data.items())[:10]:
                rows += f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>"
            return f"<table class='analysis-table'>{rows}</table>"
    
    def save(self, output_path: Optional[str] = None, format: str = "html") -> Path:
        """保存报告"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"report_enhanced_{timestamp}.html"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.to_html()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_path
