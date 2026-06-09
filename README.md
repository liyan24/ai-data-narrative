# AI Data Narrative

AI 驱动的数据叙事工作流系统。将原始数据自动转化为引人注目的数据叙事，遵循 Cole Nussbaumer Knaflic《Storytelling with Data》的六步方法论：

1. **理解背景**（Context）
2. **数据分析**（Data Analysis）
3. **选择可视化并消除杂乱**（Visualization / Declutter）
4. **聚焦注意力**（Focus Attention）
5. **像设计师一样思考**（Design Polish）
6. **讲述故事**（Storytelling）

同时提供基于 DeepEval 启发的五维质量评估框架，支持多 LLM 评审。

---

## 特性

- 🤖 **6 个 AI 智能体（Agent）**：Context / Data / Visualization (×3) / Storytelling / CodeReview
- 🧩 **技能插件化（Skill）**：DataAnalysis / DataVisualization / DataStorytelling，均基于统一接口
- 🔒 **安全代码执行引擎**：AST 语法检查、静态安全扫描、受限命名空间沙箱、超时保护、重试机制
- 📋 **待办管理器**：任务生命周期、依赖 DAG、进度追踪、故事板导出
- 📊 **五维质量评估**：信息完整性（IC）、事实准确性（FA）、叙事连贯性（NC）、可理解性（CP）、结构保真度（SF）
- 🌐 **多 LLM 支持**：OpenAI、Anthropic Claude、Ollama（本地），以及 Mock 模式（无需密钥，离线测试）
- 🚀 **Streamlit 前端**：上传数据、配置参数、运行工作流、查看可视化、下载报告与评估

---

## 快速开始

### 1. 克隆与安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\python -m pip install -r requirements.txt
# macOS/Linux
.venv/bin/python -m pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

**使用 Deepseek 等兼容 OpenAI 的 API**：
```bash
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

如果暂时没有 API Key，可以使用 **Mock Provider** 运行完整工作流和测试。

### 3. 运行测试

```bash
# Windows
.venv\Scripts\python -m pytest tests/ -v
```

### 4. 启动 Streamlit 前端

```bash
# Windows
.venv\Scripts\python -m streamlit run app/streamlit_app.py
```

浏览器打开 http://localhost:8502 即可使用。

---

## 项目结构

```
.
├── app/
│   └── streamlit_app.py          # Streamlit 前端
├── src/ai_data_narrative/
│   ├── agents/                   # 6 个 Agent 实现
│   ├── evaluation/               # 5 指标评估 + 多 LLM 评审
│   ├── execution/                # 代码执行引擎（语法/安全/沙箱/重试）
│   ├── llm/                      # LLM Provider 与路由
│   ├── models.py                 # Pydantic 数据模型
│   ├── interfaces.py             # 抽象接口
│   ├── skills/                   # Skill 插件
│   ├── utils/                    # 工具函数
│   └── workflow/                 # WorkflowEngine + TodoManager
├── tests/                        # pytest 测试套件
├── data/                         # 示例数据
├── requirements.txt
└── pyproject.toml
```

---

## 使用示例（Python API）

```python
import pandas as pd
from ai_data_narrative.llm import MockProvider
from ai_data_narrative.models import AgentInput
from ai_data_narrative.workflow.workflow_engine import WorkflowEngine

llm = MockProvider()
engine = WorkflowEngine(llm=llm)

df = pd.read_csv("data/sales_data.csv")
inp = AgentInput(
    user_request="分析销售数据并生成数据叙事报告",
    background="2024年Q3销售报告",
    audience="销售总监",
    data=df,
    data_description={"shape": df.shape, "columns": list(df.columns)},
)

result = engine.run(inp)
print(result.final_report)
print(result.evaluation.grade)
```

---

## 接口设计

### Agent 接口

```python
class BaseAgent(ABC):
    def plan(self, context: dict) -> AgentPlan: ...
    def execute(self, plan: AgentPlan, context: dict) -> AgentOutput: ...
    def review(self, output: AgentOutput) -> ReviewResult: ...
    def report(self, output: AgentOutput) -> ReportFragment: ...
```

### Skill 接口

```python
class BaseSkill(ABC):
    def plan(self, context: dict) -> SkillPlan: ...
    def validate_plan(self, plan: SkillPlan) -> ValidationResult: ...
    def execute(self, plan: SkillPlan, context: dict) -> SkillOutput: ...
```

### LLM Provider 接口

```python
class BaseLLMProvider(ABC):
    def complete(self, messages, json_mode=False, ...) -> str | dict: ...
```

新增 LLM 后端只需实现 `BaseLLMProvider` 并在配置中注册即可。

---

## 安全说明

生成的 Python 代码在沙箱中执行：

- 运行前通过 AST 做语法检查
- 静态扫描禁止 `os.system/subprocess/eval/exec/socket/urllib/pickle/ctypes/importlib/compile`
- 执行时仅暴露白名单 builtins（`len/range/sum/print` 等）
- 默认超时 120 秒
- 失败时支持 LLM 驱动的自动修复与指数退避重试

---

## 许可

MIT（或根据项目实际情况调整）
