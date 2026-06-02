# AI Data Narrative System

> **Data Storyteller** — Let Data Tell Its Own Story

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Introduction

AI Data Narrative System is a **fully automated data-to-story pipeline**. Simply upload a data file, and the system automatically completes data analysis, insight extraction, chart generation, story writing, and multi-platform content adaptation.

Designed for **non-technical users**, all complex statistical analysis, machine learning, and natural language processing are handled automatically by the system, producing easy-to-understand data stories.

## Core Capabilities

| Capability | Description | Status |
|------------|-------------|--------|
| 📥 **Smart Data Input** | Support CSV, Excel, JSON, SQLite, MySQL, PostgreSQL, MongoDB, REST API | ✅ |
| 🧹 **Auto Data Cleaning** | Missing value imputation, outlier handling, duplicate removal, type normalization | ✅ |
| 🔍 **Data Quality Check** | A-F quality scoring, completeness, uniqueness, validity, consistency, timeliness | ✅ |
| 📊 **Statistical Feature Extraction** | Numeric statistics, categorical distribution, correlation, time-series features | ✅ |
| 💡 **Auto Insight Generation** | Trend detection, distribution analysis, comparison, anomaly detection, relationship discovery | ✅ |
| 🤖 **Advanced ML Analysis** | Anomaly detection, time-series forecasting, K-Means clustering, feature importance | ✅ |
| 📈 **Auto Chart Generation** | Trend lines, bar charts, heatmaps, box plots, violin plots, scatter matrices, etc. | ✅ |
| 📖 **Data Story Generation** | Introduction → Discoveries → Trends → Comparisons → Conclusion, multi-chapter complete stories | ✅ |
| 🎨 **Narrative Strategy Matching** | Auto-match best narrative strategy (trend/comparison/distribution/composition/relationship) | ✅ |
| 📱 **Multi-Platform Publishing** | Xiaohongshu (short content), WeChat Official Account (long content), Markdown | ✅ |
| 🔌 **Plugin System** | 5 lifecycle hooks, support custom insights, watermarks, and more | ✅ |
| 🌐 **Multi-Language Support** | Chinese/English interface and output | ✅ |
| ⚡ **Performance Optimization** | Big data chunked loading, memory optimization, sampling analysis, caching | ✅ |
| 🐳 **Containerized Deployment** | Dockerfile + docker-compose one-click deployment | ✅ |
| 🖥️ **Web Interface** | Gradio interactive UI, real-time analysis, chart preview, platform content preview | ✅ |
| 🤖 **LLM Enhancement** | LLM-powered insight enhancement, story polishing, report summarization (optional) | ✅ |
| ⏰ **Scheduled Automation** | Daily/interval task scheduling, data monitoring, batch processing | ✅ |
| 📊 **Monitoring & Logging** | Structured logging, performance monitoring, health checks, metrics collection | ✅ |

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

Core dependencies: `pandas`, `numpy`, `matplotlib`, `scipy`, `openai` (optional, for LLM enhancement)

Optional dependencies: `gradio` (Web UI), `pymongo` (MongoDB), `psycopg2` (PostgreSQL)

### Basic Usage

```bash
# Analyze CSV file and generate full report
python run.py data/sales_data.csv

# Enable automatic data cleaning
python run.py data/sales_data.csv --auto-clean

# Limit number of generated charts
python run.py data/sales_data.csv --max-charts 3

# Launch Web interface
python run.py --web

# Read data from database
python run.py sqlite:///data.db --db "SELECT * FROM sales"
```

### Output Example

After running, the following files are generated:

- `output/report_*.html` — Interactive HTML report (with charts)
- `output/xiaohongshu_*.md` — Xiaohongshu adapted content
- `output/wechat_mp_*.md` — WeChat Official Account adapted content
- `output/markdown_*.md` — Markdown general export
- `logs/*.log` — Detailed logs
- `logs/performance_*.json` — Performance metrics

## Project Architecture

```
ai-data-narrative/
├── src/
│   ├── data_input/          # Data Input Layer — multi-format loading, DB connection, API
│   ├── data_understand/     # Data Understanding Layer — quality checks, statistical features
│   ├── insights/            # Insight Layer — rule-based automatic insights
│   ├── cleaning/            # Cleaning Layer — auto cleaning, missing value handling
│   ├── analysis/            # Multi-Dimensional Analysis — cross analysis, ranking, ML
│   ├── narrative/           # Narrative Strategy Layer — strategy matching, storyline
│   ├── visualization/       # Visualization Layer — chart recommendation, generation
│   ├── report/              # Report Assembly — HTML/Markdown reports
│   ├── publishing/          # Publishing Layer — Xiaohongshu/WeChat adaptation
│   ├── performance/         # Performance Optimization — memory/sampling/cache/chunking
│   ├── llm_integration/     # LLM Enhancement — insight/story/summary enhancement
│   ├── automation/          # Automation Layer — scheduling/monitoring/batch processing
│   ├── monitoring/          # Monitoring Layer — logging/performance/health checks
│   ├── api_publish/         # Publishing API — platform publishing interfaces
│   ├── plugins/             # Plugin System — extensible plugin framework
│   ├── i18n/                # Internationalization — multi-language translation
│   ├── web/                 # Web UI — Gradio application
│   ├── pipeline.py          # Main pipeline orchestration
│   ├── llm_client.py        # LLM client wrapper
│   └── config.py            # Global configuration
├── tests/                   # Test files (6 files, 76 test cases)
├── data/                    # Sample data
├── examples/                # Example scripts
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker Compose config
└── run.py                   # CLI entry point
```

## Tech Stack

- **Python 3.10+**
- **pandas** — Data processing
- **numpy** — Numerical computation
- **matplotlib** — Chart generation
- **scipy** — Statistical analysis
- **scikit-learn** — Machine learning (anomaly detection, clustering, forecasting, feature importance)
- **openai** — LLM calls (OpenAI API compatible, optional)
- **gradio** — Web interface (optional)

## Testing

```bash
# Run all tests
python tests/test_data_input.py
python tests/test_data_understand.py
python tests/test_phase2.py
python tests/test_phase3.py
python tests/test_phase4.py
python tests/test_phase5.py

# Or use pytest
python -m pytest tests/ -v
```

## Changelog

### v5.0 (Phase 5)
- Enhanced Web UI (multi-tab, system status bar, platform content preview)
- Data source extensions (SQLite, MySQL, PostgreSQL, MongoDB, REST API)
- Advanced ML analysis (anomaly detection, time-series forecasting, K-Means clustering, feature importance)
- Plugin system (base class, loader, 5 lifecycle hooks, built-in watermark/custom insight plugins)
- Multi-language support (Chinese/English translation, dictionary translation, shortcut functions)

### v4.0 (Phase 4)
- LLM integration enhancement (insight natural language, story enhancement, report summarization)
- Automation scheduling (timed tasks, data monitoring, batch processing)
- Monitoring & logging system (structured logging, performance monitoring, health checks)
- Publishing API (Xiaohongshu/WeChat Official Account simulated publishing)
- Containerization support (Dockerfile + docker-compose)

### v3.0 (Phase 3)
- Advanced chart engine (box plots, heatmaps, scatter matrices, violin plots, pair plots, Sankey diagrams)
- Story generation engine (multi-strategy combination, natural language story chapters)
- Platform publishing adapters (Xiaohongshu, WeChat Official Account, Markdown)
- Performance optimization module (memory optimization, sampling analysis, chunked loading, caching)

### v2.0 (Phase 2)
- Data insight engine (rule-based automatic insights)
- Data cleaning engine (automatic missing value, outlier, duplicate handling)
- Multi-dimensional analysis engine (cross analysis, ranking, comparison, segmentation)
- Enhanced report templates (insight cards, analysis tables, cleaning records)

### v1.0 (Phase 1)
- Data input layer: multi-format loading, intelligent type inference
- Data understanding layer: quality checks, statistical feature extraction
- Visualization layer: chart recommendation, chart generation
- Report layer: HTML report generation
- Narrative strategy layer: strategy matching, storyline

## Development Plan

| Phase | Period | Content |
|-------|--------|---------|
| Phase 1 | Day 1-7 | Data input, understanding, visualization, reporting, Web UI |
| Phase 2 | Day 8-14 | Insight engine, cleaning engine, multi-dimensional analysis, enhanced reporting |
| Phase 3 | Day 15-21 | Advanced charts, narrative enhancement, platform publishing, performance optimization |
| Phase 4 | Day 22-28 | LLM integration, auto-publishing, scheduling, monitoring, containerization |
| Phase 5 | Day 29-35 | Web enhancement, data source expansion, ML analysis, plugin system, multi-language |

## License

MIT License
