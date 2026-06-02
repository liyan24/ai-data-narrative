"""
报告组装层 — 将分析结果、图表组装为完整报告
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import base64

from src.config import REPORT_CONFIG, OUTPUT_DIR


class ReportBuilder:
    """报告构建器"""
    
    def __init__(self, title: str = None, author: str = None):
        self.title = title or REPORT_CONFIG["title"]
        self.author = author or REPORT_CONFIG["author"]
        self.sections: List[Dict[str, Any]] = []
        self.charts: List[Dict] = []
    
    def add_section(self, heading: str, content: str, level: int = 2):
        """添加文本章节"""
        self.sections.append({
            "type": "text",
            "heading": heading,
            "level": level,
            "content": content
        })
    
    def add_chart(self, chart_base64: str, title: str, description: str = ""):
        """添加图表"""
        self.charts.append({
            "type": "chart",
            "data": chart_base64,
            "title": title,
            "description": description
        })
        
        self.sections.append({
            "type": "chart",
            "heading": title,
            "level": 3,
            "content": description,
            "chart_data": chart_base64
        })
    
    def add_table(self, data: Dict[str, List], title: str = "数据表格"):
        """添加表格"""
        self.sections.append({
            "type": "table",
            "heading": title,
            "level": 3,
            "data": data
        })
    
    def add_insight(self, insight_text: str, severity: str = "info"):
        """添加洞察点"""
        self.sections.append({
            "type": "insight",
            "heading": "数据洞察",
            "level": 3,
            "content": insight_text,
            "severity": severity
        })
    
    def to_html(self) -> str:
        """生成 HTML 报告"""
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang=\"zh-CN\">",
            "<head>",
            "    <meta charset=\"UTF-8\">",
            "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            f"    <title>{self.title}</title>",
            "    <style>",
            "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; background: #f5f5f5; }",
            "        .report-container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }",
            "        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }",
            "        h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 15px; }",
            "        h3 { color: #555; margin-top: 20px; }",
            "        .meta { color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px; }",
            "        .chart-container { text-align: center; margin: 20px 0; padding: 15px; background: #fafafa; border-radius: 6px; }",
            "        .chart-container img { max-width: 100%; height: auto; border-radius: 4px; }",
            "        .chart-title { font-weight: bold; color: #2c3e50; margin-bottom: 8px; }",
            "        .chart-desc { color: #666; font-size: 0.9em; }",
            "        .insight-box { background: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; border-radius: 4px; }",
            "        .insight-box.warning { background: #fff3e0; border-left-color: #ff9800; }",
            "        .insight-box.critical { background: #ffebee; border-left-color: #f44336; }",
            "        table { width: 100%; border-collapse: collapse; margin: 15px 0; }",
            "        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }",
            "        th { background: #f8f9fa; font-weight: bold; }",
            "        tr:nth-child(even) { background: #f8f9fa; }",
            "        .footer { text-align: center; color: #999; font-size: 0.8em; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <div class=\"report-container\">",
            f"        <h1>{self.title}</h1>",
            f"        <div class=\"meta\">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 生成工具: {self.author}</div>",
        ]
        
        for section in self.sections:
            if section["type"] == "text":
                tag = f"h{section['level']}"
                html_parts.append(f"        <{tag}>{section['heading']}</{tag}>")
                html_parts.append(f"        <p>{section['content']}</p>")
            
            elif section["type"] == "chart":
                html_parts.append("        <div class=\"chart-container\">")
                html_parts.append(f"            <div class=\"chart-title\">{section['heading']}</div>")
                if section.get("content"):
                    html_parts.append(f"            <div class=\"chart-desc\">{section['content']}</div>")
                html_parts.append(f"            <img src=\"data:image/png;base64,{section['chart_data']}\" alt=\"{section['heading']}\">")
                html_parts.append("        </div>")
            
            elif section["type"] == "insight":
                severity = section.get("severity", "info")
                html_parts.append(f"        <div class=\"insight-box {severity}\">")
                html_parts.append(f"            <strong>💡 {section['heading']}</strong><br>")
                html_parts.append(f"            {section['content']}")
                html_parts.append("        </div>")
            
            elif section["type"] == "table":
                html_parts.append(f"        <h3>{section['heading']}</h3>")
                html_parts.append("        <table>")
                
                data = section["data"]
                headers = list(data.keys())
                html_parts.append("            <tr>" + "".join([f"<th>{h}</th>" for h in headers]) + "</tr>")
                
                row_count = len(data[headers[0]]) if headers else 0
                for i in range(min(row_count, 20)):  # 最多20行
                    html_parts.append("            <tr>" + "".join([f"<td>{data[h][i]}</td>" for h in headers]) + "</tr>")
                
                html_parts.append("        </table>")
        
        html_parts.extend([
            "        <div class=\"footer\">",
            "            由 AI数据叙事系统 自动生成",
            "        </div>",
            "    </div>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_parts)
    
    def to_markdown(self) -> str:
        """生成 Markdown 报告"""
        lines = [
            f"# {self.title}",
            "",
            f"_生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
            "",
            "---",
            "",
        ]
        
        for section in self.sections:
            heading_prefix = "#" * section["level"]
            lines.append(f"{heading_prefix} {section['heading']}")
            lines.append("")
            
            if section["type"] == "text":
                lines.append(section["content"])
            elif section["type"] == "chart":
                lines.append(f"![{section['heading']}](data:image/png;base64,{section['chart_data']})")
                if section.get("content"):
                    lines.append(f"*{section['content']}*")
            elif section["type"] == "insight":
                lines.append(f"> 💡 **{section['heading']}**: {section['content']}")
            elif section["type"] == "table":
                lines.append("[表格数据见HTML版本]")
            
            lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("*由 AI数据叙事系统 自动生成*")
        
        return "\n".join(lines)
    
    def save(self, output_path: Optional[str] = None, format: str = "html") -> Path:
        """保存报告到文件"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"report_{timestamp}.{format}"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "html":
            content = self.to_html()
        elif format == "markdown":
            content = self.to_markdown()
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_path
