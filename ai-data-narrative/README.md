# AI数据叙事系统

> 从数据上传到报告生成的全自动化流水线
> 项目周期: 2026-06-01 ~ 2026-08-01

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置大模型（可选）

```bash
# Windows PowerShell
$env:LLM_API_KEY="your-api-key"
$env:LLM_BASE_URL="https://api.moonshot.cn/v1"

# 或 Linux/Mac
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://api.moonshot.cn/v1"
```

> 未配置 LLM 时，系统仍可进行数据加载、类型推断、质量检查、统计分析和图表生成，仅 AI 洞察部分会降级。

### 3. 生成示例数据

```bash
python examples/generate_sample_data.py
```

### 4. 运行数据叙事（第二阶段增强版）

```bash
# 基础模式
python run.py data/sales_data.csv

# 限制图表数量
python run.py data/customer_data.csv --max-charts 3

# 启用自动清洗
python run.py data/sales_data.csv --auto-clean

# 激进清洗 + 限制图表
python run.py data/sales_data.csv --auto-clean --aggressive --max-charts 2

# 指定输出目录
python run.py data/employee_data.xlsx --output ./my_reports

# 第三阶段 — 禁用高级图表/故事/发布（加快处理）
python run.py data/sales_data.csv --no-advanced --no-story --no-publish

# 大数据采样分析
python run.py data/large_file.csv --sample 10000

# 第四阶段 — 启用 LLM 增强（需要 API Key）
python run.py data/sales_data.csv --llm-enhance

# 第四阶段 — 自动发布到已配置平台
python run.py data/sales_data.csv --auto-publish

# 第四阶段 — 健康检查
python run.py --health-check

# 第五阶段 — 启动增强 Web 界面
python run.py --web

# 第五阶段 — 禁用 ML 分析（加快处理）
python run.py data/sales_data.csv --no-ml

# 第五阶段 — 指定插件目录
python run.py data/sales_data.csv --plugin-dir ./plugins

# 第五阶段 — 英文界面
python run.py --locale en --web
```

### 6. 启动 Web 界面

```bash
python src/web/app.py
```

然后打开浏览器访问 `http://localhost:7860`

---

## 项目架构

```
ai-data-narrative/
├── src/
│   ├── data_input/          # 数据输入层 — 多格式加载、类型推断、数据库连接
│   ├── data_understand/     # 数据理解层 — 质量检查、统计特征
│   ├── insights/            # 数据洞察层 — 基于统计规则的自动洞察
│   ├── cleaning/            # 数据清洗层 — 自动清洗、缺失值处理
│   ├── analysis/            # 多维度分析层 — 交叉分析、排名、对比、ML分析
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
│   ├── web/                 # Web界面 — Gradio 应用（增强版）
│   ├── pipeline.py          # 主流水线编排（第五阶段完整版）
│   ├── llm_client.py        # 大模型调用封装
│   └── config.py            # 全局配置
├── examples/                # 示例数据生成
├── tests/                   # 测试用例
├── data/                    # 数据目录（运行示例后生成）
├── output/                  # 输出目录（报告保存位置）
├── prompts/                 # Prompt 模板
├── templates/               # 报告/图表模板
├── requirements.txt         # 依赖
└── run.py                   # 快捷入口
```

---

## 第一阶段（Day 1-7）功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 数据输入 | CSV/Excel/JSON/Parquet 加载 | ✅ |
| 数据输入 | 编码自动探测（utf-8/gbk/gb2312） | ✅ |
| 数据输入 | 智能类型推断（7种类型） | ✅ |
| 数据理解 | 缺失值检测 | ✅ |
| 数据理解 | 异常值检测（IQR/Z-Score） | ✅ |
| 数据理解 | 重复值检测 | ✅ |
| 数据理解 | 统计特征提取（均值/分布/相关性） | ✅ |
| 数据理解 | 数据质量评分（A+~F） | ✅ |

## 第二阶段（Day 8-14）功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 数据洞察 | 趋势检测（上升/下降/波动） | ✅ |
| 数据洞察 | 分布分析（偏态/峰度/多峰） | ✅ |
| 数据洞察 | 对比分析（Top N / 极值 / 差异显著性） | ✅ |
| 数据洞察 | 关系分析（相关性/正/负） | ✅ |
| 数据洞察 | 构成分析（HHI集中度） | ✅ |
| 数据洞察 | 异常检测（Z-Score 统计异常） | ✅ |
| 数据清洗 | 自动缺失值填充（均值/中位数/众数） | ✅ |
| 数据清洗 | 异常值处理（截断/删除） | ✅ |
| 数据清洗 | 重复值删除 | ✅ |
| 数据清洗 | 类型标准化（日期自动转换） | ✅ |
| 多维度分析 | 交叉分析（类别 x 类别 → 数值） | ✅ |
| 多维度分析 | 排名分析（Top N / Bottom N） | ✅ |
| 多维度分析 | 对比分析（环比/月环比） | ✅ |
| 多维度分析 | 分段分析（等频分箱） | ✅ |
| 报告增强 | 洞察卡片式展示 | ✅ |
| 报告增强 | 多维度分析表格 | ✅ |
| 报告增强 | 清洗记录展示 | ✅ |
| 报告增强 | 交互式图表 | ✅ |

## 第四阶段（Day 22-28）功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 高级图表 | 箱线图（分布/异常值） | ✅ |
| 高级图表 | 热力图（相关性/交叉表） | ✅ |
| 高级图表 | 散点图矩阵（多变量探索） | ✅ |
| 高级图表 | 小提琴图（分布密度对比） | ✅ |
| 高级图表 | 配对图（回归线+密度） | ✅ |
| 高级图表 | 桑基图/流向图（构成流向） | ✅ |
| 叙事增强 | 多策略组合与评分 | ✅ |
| 叙事增强 | 策略冲突检测与解决 | ✅ |
| 叙事增强 | 自然语言故事生成 | ✅ |
| 叙事增强 | 故事章节（引言/发现/趋势/总结） | ✅ |
| 平台发布 | 小红书适配（短文本/emoji/话题） | ✅ |
| 平台发布 | 微信公众号适配（长图文/摘要） | ✅ |
| 平台发布 | Markdown 通用导出 | ✅ |
| 性能优化 | 大数据分块加载 | ✅ |
| 性能优化 | 内存优化（类型降采样） | ✅ |
| 性能优化 | 采样分析（随机/分层） | ✅ |
| 性能优化 | 分析缓存机制 | ✅ |
| 性能优化 | 进度跟踪 | ✅ |
| LLM 集成 | 洞察自然语言增强 | ✅ |
| LLM 集成 | 故事内容增强 | ✅ |
| LLM 集成 | 报告摘要/标题生成 | ✅ |
| LLM 集成 | 缓存降级机制 | ✅ |
| 自动调度 | 每日/间隔任务调度 | ✅ |
| 自动调度 | 数据文件监控 | ✅ |
| 自动调度 | 批量处理 | ✅ |
| 监控日志 | 结构化日志记录 | ✅ |
| 监控日志 | 性能监控（内存/CPU） | ✅ |
| 监控日志 | 健康检查 | ✅ |
| 监控日志 | 指标收集 | ✅ |
| 发布 API | 小红书/微信发布接口 | ✅ |
| 发布 API | 内容验证 | ✅ |
| 发布 API | 批量发布 | ✅ |
| 容器化 | Dockerfile | ✅ |
| 容器化 | docker-compose.yml | ✅ |

## 第五阶段（Day 29-35）功能

| 模块 | 功能 | 状态 |
|------|------|------|
| Web 增强 | 增强 Gradio 界面（多标签/状态栏） | ✅ |
| Web 增强 | 实时分析处理 | ✅ |
| Web 增强 | 平台内容预览 | ✅ |
| 数据源扩展 | SQLite 数据库连接 | ✅ |
| 数据源扩展 | MySQL/PostgreSQL 连接器 | ✅ |
| 数据源扩展 | MongoDB 连接器 | ✅ |
| 数据源扩展 | REST API 数据源 | ✅ |
| 数据源扩展 | 数据源管理器 | ✅ |
| 高级 ML | 异常检测（IsolationForest/DBSCAN/Z-Score） | ✅ |
| 高级 ML | 时间序列预测（线性/移动平均/指数平滑） | ✅ |
| 高级 ML | K-Means 聚类分析 | ✅ |
| 高级 ML | 随机森林特征重要性 | ✅ |
| 高级 ML | 分段统计分析 | ✅ |
| 插件系统 | 插件基类与加载器 | ✅ |
| 插件系统 | 钩子机制（5 个生命周期钩子） | ✅ |
| 插件系统 | 内置水印插件 | ✅ |
| 插件系统 | 自定义洞察规则插件 | ✅ |
| 多语言 | 中文/英文翻译 | ✅ |
| 多语言 | 字典键翻译 | ✅ |
| 多语言 | 快捷翻译函数 | ✅ |

---

## 测试

```bash
# 运行第一阶段测试
python tests/test_data_input.py
python tests/test_data_understand.py

# 运行第二阶段测试
python tests/test_phase2.py

# 运行第三阶段测试
python tests/test_phase3.py

# 运行第四阶段测试
python tests/test_phase4.py

# 运行第五阶段测试
python tests/test_phase5.py

# 使用 pytest
python -m pytest tests/ -v
```

---

## 技术栈

- **Python 3.10+**
- **pandas** — 数据处理
- **numpy** — 数值计算
- **matplotlib** — 图表生成
- **scipy** — 统计分析
- **openai** — 大模型调用（兼容 OpenAI API）
- **gradio** — Web 界面

---

## 更新日志

### v5.0（第五阶段）
- 增强 Web 界面（多标签页、系统状态栏、平台内容预览）
- 数据源扩展（SQLite、MySQL、PostgreSQL、MongoDB、REST API）
- 高级 ML 分析（异常检测、时间序列预测、K-Means 聚类、特征重要性）
- 插件系统（基类、加载器、5 个生命周期钩子、内置水印/自定义洞察插件）
- 多语言支持（中文/英文翻译、字典翻译、快捷函数）
- 流水线支持 `--no-ml`、`--plugin-dir`、`--locale`、`--web`、`--db` 参数
- 新增数据源连接器、ML 分析引擎、插件管理器、翻译器

### v4.0（第四阶段）
- 新增 LLM 集成增强（洞察自然语言化、故事内容增强、报告摘要）
- 新增自动化调度（定时任务、数据监控、批量处理）
- 新增监控日志系统（结构化日志、性能监控、健康检查）
- 新增发布 API（小红书/微信公众号模拟发布）
- 新增容器化支持（Dockerfile + docker-compose）
- 流水线支持 `--llm-enhance`、`--auto-publish`、`--health-check` 参数
- 增强性能报告和日志输出

### v3.0（第三阶段）
- 新增高级图表引擎（箱线图、热力图、散点图矩阵、小提琴图、配对图、桑基图）
- 新增故事生成引擎（多策略组合、自然语言故事章节）
- 新增策略评分器（按数据特征加权评分）和冲突检测器
- 新增平台发布适配器（小红书、微信公众号、Markdown）
- 新增性能优化模块（内存优化、采样分析、分块加载、缓存机制）
- 流水线支持 `--no-advanced`、`--no-story`、`--no-publish`、`--sample` 参数
- 增强报告支持故事章节和平台适配内容

### v2.0（第二阶段）
- 新增数据洞察引擎（基于统计规则的自动洞察）
- 新增数据清洗引擎（自动处理缺失值、异常值、重复值）
- 新增多维度分析引擎（交叉分析、排名、对比、分段）
- 增强报告模板（洞察卡片、分析表格、清洗记录）
- 流水线支持自动清洗和激进模式
- 新增 `--auto-clean` 和 `--aggressive` CLI 参数

### v1.0（第一阶段）
- 数据输入层：多格式加载、智能类型推断
- 数据理解层：质量检查、统计特征提取
- 可视化层：图表推荐、图表生成
- 报告层：HTML 报告生成
- 叙事策略层：策略匹配、故事线

---

*正在开发中... 第五阶段代码已完成，后续阶段陆续更新。*
