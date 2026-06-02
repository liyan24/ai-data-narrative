# AI 数据叙事系统

> **Data Storyteller** — 让数据自己会讲故事

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 简介

AI 数据叙事系统是一个**全自动化的数据到故事流水线**。你只需上传一份数据文件，系统就能自动完成数据分析、洞察提取、图表生成、故事撰写、多平台内容适配的全过程。

本项目面向**技术小白**设计，所有复杂的统计分析、机器学习、自然语言处理都由系统自动完成，最终输出通俗易懂的数据故事。

## 核心能力

| 能力 | 说明 | 状态 |
|------|------|------|
| 📥 **智能数据输入** | 支持 CSV、Excel、JSON、SQLite、MySQL、PostgreSQL、MongoDB、REST API | ✅ |
| 🧹 **自动数据清洗** | 缺失值填充、异常值处理、重复值删除、类型标准化 | ✅ |
| 🔍 **数据质量检查** | A-F 质量评分、完整性、唯一性、有效性、一致性、及时性 | ✅ |
| 📊 **统计特征提取** | 数值统计、类别分布、相关性、时间序列特征 | ✅ |
| 💡 **自动洞察生成** | 趋势检测、分布分析、对比分析、异常检测、关联发现 | ✅ |
| 🤖 **ML 高级分析** | 异常检测、时间序列预测、K-Means 聚类、特征重要性 | ✅ |
| 📈 **图表自动生成** | 趋势图、柱状图、热力图、箱线图、小提琴图、散点图矩阵等 | ✅ |
| 📖 **数据故事生成** | 引言→发现→趋势→对比→总结，多章节完整故事 | ✅ |
| 🎨 **叙事策略匹配** | 自动匹配最佳叙事策略（趋势/对比/分布/构成/关系） | ✅ |
| 📱 **多平台发布** | 小红书（短图文）、微信公众号（长图文）、Markdown | ✅ |
| 🔌 **插件扩展** | 5 个生命周期钩子，支持自定义洞察、水印等插件 | ✅ |
| 🌐 **多语言支持** | 中文/英文界面和输出 | ✅ |
| ⚡ **性能优化** | 大数据分块加载、内存优化、采样分析、缓存机制 | ✅ |
| 🐳 **容器化部署** | Dockerfile + docker-compose 一键部署 | ✅ |
| 🖥️ **Web 界面** | Gradio 交互式界面，实时分析、图表预览、平台内容预览 | ✅ |
| 🤖 **LLM 增强** | 大模型驱动洞察增强、故事润色、报告摘要（可选） | ✅ |
| ⏰ **定时调度** | 每日/间隔任务调度、数据监控、批量处理 | ✅ |
| 📊 **监控日志** | 结构化日志、性能监控、健康检查、指标收集 | ✅ |

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

核心依赖：`pandas`, `numpy`, `matplotlib`, `scipy`, `openai`（可选，用于 LLM 增强）

可选依赖：`gradio`（Web 界面）、`pymongo`（MongoDB）、`psycopg2`（PostgreSQL）

### 基本使用

```bash
# 分析 CSV 文件并生成完整报告
python run.py data/sales_data.csv

# 启用自动数据清洗
python run.py data/sales_data.csv --auto-clean

# 限制生成图表数量
python run.py data/sales_data.csv --max-charts 3

# 启动 Web 界面
python run.py --web

# 从数据库读取数据
python run.py sqlite:///data.db --db "SELECT * FROM sales"
```

### 输出示例

运行后会生成：

- `output/report_*.html` — 交互式 HTML 报告（含图表）
- `output/xiaohongshu_*.md` — 小红书适配内容
- `output/wechat_mp_*.md` — 微信公众号适配内容
- `output/markdown_*.md` — Markdown 通用导出
- `logs/*.log` — 详细日志
- `logs/performance_*.json` — 性能指标

## 项目架构

```
ai-data-narrative/
├── src/
│   ├── data_input/          # 数据输入层 — 多格式加载、数据库连接、API
│   ├── data_understand/     # 数据理解层 — 质量检查、统计特征
│   ├── insights/            # 数据洞察层 — 基于统计规则的自动洞察
│   ├── cleaning/            # 数据清洗层 — 自动清洗、缺失值处理
│   ├── analysis/            # 多维度分析层 — 交叉分析、排名、对比、ML
│   ├── narrative/           # 叙事策略层 — 策略匹配、故事线生成
│   ├── visualization/       # 可视化层 — 图表推荐、图表生成
│   ├── report/              # 报告组装层 — HTML/Markdown 报告
│   ├── publishing/          # 平台发布层 — 小红书/微信公众号适配
│   ├── performance/         # 性能优化层 — 内存/采样/缓存/分块
│   ├── llm_integration/     # LLM 增强层 — 洞察/故事/摘要增强
│   ├── automation/          # 自动化层 — 定时任务/监控/批量处理
│   ├── monitoring/          # 监控层 — 日志/性能/健康检查
│   ├── api_publish/         # 发布 API — 平台发布接口
│   ├── plugins/             # 插件系统 — 可扩展插件框架
│   ├── i18n/                # 国际化层 — 多语言翻译
│   ├── web/                 # Web界面 — Gradio 应用
│   ├── pipeline.py          # 主流水线编排
│   ├── llm_client.py        # 大模型调用封装
│   └── config.py            # 全局配置
├── tests/                   # 测试文件（6个文件，76个用例）
├── data/                    # 示例数据
├── examples/                # 示例脚本
├── Dockerfile               # Docker 镜像
├── docker-compose.yml       # Docker Compose 配置
└── run.py                   # CLI 入口
```

## 技术栈

- **Python 3.10+**
- **pandas** — 数据处理
- **numpy** — 数值计算
- **matplotlib** — 图表生成
- **scipy** — 统计分析
- **scikit-learn** — 机器学习（异常检测、聚类、预测、特征重要性）
- **openai** — 大模型调用（兼容 OpenAI API，可选）
- **gradio** — Web 界面（可选）

## 测试

```bash
# 运行全部测试
python tests/test_data_input.py
python tests/test_data_understand.py
python tests/test_phase2.py
python tests/test_phase3.py
python tests/test_phase4.py
python tests/test_phase5.py

# 或使用 pytest
python -m pytest tests/ -v
```

## 更新日志

### v5.0（第五阶段）
- 增强 Web 界面（多标签页、系统状态栏、平台内容预览）
- 数据源扩展（SQLite、MySQL、PostgreSQL、MongoDB、REST API）
- 高级 ML 分析（异常检测、时间序列预测、K-Means 聚类、特征重要性）
- 插件系统（基类、加载器、5 个生命周期钩子、内置水印/自定义洞察插件）
- 多语言支持（中文/英文翻译、字典翻译、快捷函数）

### v4.0（第四阶段）
- LLM 集成增强（洞察自然语言化、故事增强、报告摘要）
- 自动化调度（定时任务、数据监控、批量处理）
- 监控日志系统（结构化日志、性能监控、健康检查）
- 发布 API（小红书/微信公众号模拟发布）
- 容器化支持（Dockerfile + docker-compose）

### v3.0（第三阶段）
- 高级图表引擎（箱线图、热力图、散点图矩阵、小提琴图、配对图、桑基图）
- 故事生成引擎（多策略组合、自然语言故事章节）
- 平台发布适配器（小红书、微信公众号、Markdown）
- 性能优化模块（内存优化、采样分析、分块加载、缓存机制）

### v2.0（第二阶段）
- 数据洞察引擎（基于统计规则的自动洞察）
- 数据清洗引擎（自动处理缺失值、异常值、重复值）
- 多维度分析引擎（交叉分析、排名、对比、分段）
- 增强报告模板（洞察卡片、分析表格、清洗记录）

### v1.0（第一阶段）
- 数据输入层：多格式加载、智能类型推断
- 数据理解层：质量检查、统计特征提取
- 可视化层：图表推荐、图表生成
- 报告层：HTML 报告生成
- 叙事策略层：策略匹配、故事线

## 开发计划

| 阶段 | 周期 | 内容 |
|------|------|------|
| 第一阶段 | Day 1-7 | 数据输入、理解、可视化、报告、Web 界面 |
| 第二阶段 | Day 8-14 | 洞察引擎、清洗引擎、多维度分析、增强报告 |
| 第三阶段 | Day 15-21 | 高级图表、叙事增强、平台发布、性能优化 |
| 第四阶段 | Day 22-28 | LLM 集成、自动发布、定时调度、监控日志、容器化 |
| 第五阶段 | Day 29-35 | Web 增强、数据源扩展、ML 分析、插件系统、多语言 |

## 许可证

MIT License
