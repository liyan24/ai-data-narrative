#!/usr/bin/env python3
"""
微信公众号一键发布脚本

使用方法:
    python publish_wechat.py --file output/day2_wechat_published.md --title "Day 2 总结"
    
    或直接从流水线发布:
    python publish_wechat.py --pipeline --data data/sales_data.csv
"""

import sys
from pathlib import Path

# 设置项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.api_publish.wechat_real import WechatPublisher, WechatPublishOrchestrator
from src.pipeline import DataNarrativePipeline
import argparse


def main():
    parser = argparse.ArgumentParser(description='发布内容到微信公众号')
    parser.add_argument('--file', '-f', type=str, help='Markdown/HTML文件路径')
    parser.add_argument('--title', '-t', type=str, help='文章标题')
    parser.add_argument('--author', '-a', type=str, default='AI数据叙事', help='作者名')
    parser.add_argument('--digest', '-d', type=str, help='文章摘要')
    parser.add_argument('--pipeline', '-p', action='store_true', help='从流水线结果发布')
    parser.add_argument('--data', type=str, help='数据文件路径（配合--pipeline使用）')
    parser.add_argument('--test', action='store_true', help='测试连接')
    
    args = parser.parse_args()
    
    # 初始化发布器
    publisher = WechatPublisher()
    
    # 测试模式
    if args.test:
        print("🔍 测试微信公众号连接...")
        success, msg = publisher.test_connection()
        if success:
            print(f"✅ 连接成功！{msg}")
        else:
            print(f"❌ 连接失败：{msg}")
            print("📖 请按 docs/WECHAT_API_SETUP.md 配置")
        return
    
    # 从文件发布
    if args.file:
        if not Path(args.file).exists():
            print(f"❌ 文件不存在：{args.file}")
            return
        
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        title = args.title or Path(args.file).stem
        
        # 简单HTML转换
        html = f"<div style='font-size:16px;line-height:1.8'>"
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('# '):
                html += f"<h1>{line[2:]}</h1>"
            elif line.startswith('## '):
                html += f"<h2>{line[3:]}</h2>"
            elif line.startswith('### '):
                html += f"<h3>{line[4:]}</h3>"
            elif line.startswith('- '):
                html += f"<li>{line[2:]}</li>"
            elif line.startswith('|') and '---' not in line:
                # 表格行跳过
                pass
            elif line:
                html += f"<p>{line}</p>"
        html += "</div>"
        
        print(f"📤 正在发布文章：{title}")
        result = publisher.publish_article(
            title=title,
            content=html,
            author=args.author,
            digest=args.digest or ""
        )
    
    # 从流水线发布
    elif args.pipeline:
        if not args.data:
            print("❌ 请指定数据文件路径：--data data/sales_data.csv")
            return
        
        print(f"📊 正在运行流水线：{args.data}")
        pipeline = DataNarrativePipeline()
        pipeline_result = pipeline.run(data_path=args.data)
        
        orchestrator = WechatPublishOrchestrator(publisher)
        orchestrator.load_pipeline_result(pipeline_result)
        
        title = args.title or "AI数据分析报告"
        print(f"📤 正在发布文章：{title}")
        result = orchestrator.publish_wechat(title=title, author=args.author)
    
    else:
        print("❌ 请指定发布方式：")
        print("  --file FILE.md    从文件发布")
        print("  --pipeline --data FILE.csv  从流水线发布")
        print("  --test            测试连接")
        return
    
    # 输出结果
    if result.success:
        print(f"✅ 发布成功！")
        print(f"   发布ID：{result.publish_id}")
        print(f"   📱 请访问公众号主页查看文章")
    else:
        print(f"❌ 发布失败：{result.message}")
        print(f"   原始响应：{result.raw_response}")


if __name__ == '__main__':
    main()
