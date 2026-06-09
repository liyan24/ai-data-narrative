"""Streamlit frontend for the AI Data Narrative system."""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="AI Data Narrative", layout="wide")

# Make src available
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_data_narrative.config import DEFAULT_PASS_THRESHOLD  # noqa: E402
from ai_data_narrative.llm import (  # noqa: E402
    AnthropicProvider,
    MockProvider,
    OllamaProvider,
    OpenAIProvider,
)
from ai_data_narrative.models import AgentInput, AgentOutput, TaskStatus, WorkflowResult  # noqa: E402
from ai_data_narrative.workflow.workflow_engine import STEPS, WorkflowEngine  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "data" / "samples"

# -----------------------------------------------------------------------------
# Session state initialization
# -----------------------------------------------------------------------------
def _init_session() -> None:
    defaults = {
        "workflow_outputs": {},
        "run_dir": None,
        "eval_report": None,
        "result": None,
        "progress_lines": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_session()

# -----------------------------------------------------------------------------
# Provider & helpers
# -----------------------------------------------------------------------------
def provider_selector() -> Any:
    provider_name = st.sidebar.selectbox(
        "LLM Provider",
        ["Mock (离线)", "OpenAI / Deepseek", "Anthropic", "Ollama"],
        index=0,
    )
    if provider_name == "OpenAI / Deepseek":
        key = st.sidebar.text_input("API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        base_url = st.sidebar.text_input("Base URL (可选)", value=os.getenv("OPENAI_BASE_URL", ""), placeholder="https://api.openai.com/v1")
        model = st.sidebar.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        return OpenAIProvider(api_key=key or None, model=model, base_url=base_url or None)
    if provider_name == "Anthropic":
        key = st.sidebar.text_input("Anthropic API Key", type="password", value=os.getenv("ANTHROPIC_API_KEY", ""))
        model = st.sidebar.selectbox("Model", ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"], index=0)
        return AnthropicProvider(api_key=key or None, model=model)
    if provider_name == "Ollama":
        base = st.sidebar.text_input("Ollama Base URL", value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        model = st.sidebar.text_input("Model", value="llama3")
        return OllamaProvider(base_url=base, model=model)
    return MockProvider()


def download_button(data: str, filename: str, label: str) -> None:
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:file/plain;base64,{b64}" download="{filename}">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Dataset selector
# -----------------------------------------------------------------------------
def load_sample_index() -> list[dict]:
    idx_path = SAMPLES_DIR / "index.json"
    if not idx_path.exists():
        return []
    with open(idx_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_dataset(entry: dict) -> tuple[Any, Dict[str, Any]]:
    dpath = Path(entry["path"])
    data_type = entry["data_type"]
    meta_path = dpath / "meta.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    data: Any = None
    if data_type == "timeseries":
        data = pd.read_csv(dpath / "data.csv")
    elif data_type == "table":
        data = pd.read_csv(dpath / "data.csv")
    elif data_type == "json":
        with open(dpath / "data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    elif data_type == "network":
        with open(dpath / "nodes.json", "r", encoding="utf-8") as f:
            nodes = json.load(f)
        with open(dpath / "edges.json", "r", encoding="utf-8") as f:
            edges = json.load(f)
        data = {"nodes": nodes, "edges": edges}
    return data, meta


def _render_json_keys(keys: dict, level: int = 0) -> None:
    indent = "  " * level
    for k, v in keys.items():
        if isinstance(v, dict):
            t = v.get("type", "")
            desc = v.get("description", "")
            if t == "object":
                st.write(f"{indent}- **{k}** ({t}): {desc}")
                _render_json_keys(v.get("keys", {}), level + 1)
            elif t == "array":
                st.write(f"{indent}- **{k}** ({t}): {desc}")
                item = v.get("item_schema", {})
                if isinstance(item, dict) and item.get("type") == "object":
                    _render_json_keys(item.get("keys", {}), level + 1)
                elif isinstance(item, dict):
                    st.write(f"{indent}  - item ({item.get('type', '')})")
                else:
                    st.write(f"{indent}  - item ({item})")
            else:
                vals = v.get("values", [])
                vals_str = f" [{', '.join(map(str, vals))}]" if vals else ""
                st.write(f"{indent}- **{k}** ({t}{vals_str}): {desc}")


def render_meta_preview(meta: dict) -> None:
    data_type = meta.get("data_type", "")
    schema = meta.get("schema", {})

    if data_type == "timeseries":
        tf = schema.get("time_field", {})
        st.write(f"**时间字段**: {tf.get('name', '-')} ({tf.get('period', '-')}粒度, {tf.get('format', '-')})")
        for vf in schema.get("value_fields", []):
            unit = f" {vf.get('unit', '')}".strip()
            st.write(f"- **{vf['name']}** ({vf.get('type', '')}{unit}): {vf.get('description', '')}")
        dims = schema.get("dimension_fields", [])
        if dims:
            st.write("**维度字段**:")
            for df in dims:
                vals = df.get("values", [])
                st.write(f"- **{df['name']}**: {df.get('description', '')} ({', '.join(vals)})")
    elif data_type == "table":
        st.write(f"**每行含义**: {schema.get('row_meaning', '-')}")
        st.write(f"**每列含义**: {schema.get('column_meaning', '-')}")
        for col in schema.get("columns", []):
            unit = f" {col.get('unit', '')}".strip()
            role = f" [{col.get('role', '')}]" if col.get("role") else ""
            st.write(f"- **{col['name']}** ({col.get('type', '')}{unit}{role}): {col.get('description', '')}")
    elif data_type == "json":
        root = schema.get("root_type", "object")
        st.write(f"**根类型**: {root}")
        if root == "array":
            st.write(f"**每项含义**: {schema.get('item_meaning', '-')}")
        _render_json_keys(schema.get("keys", {}), level=0)
    elif data_type == "network":
        st.write("**节点类型**:")
        for nt, nt_def in schema.get("node_types", {}).items():
            st.write(f"- **{nt}**: {nt_def.get('description', '')}")
            for attr, adef in nt_def.get("attributes", {}).items():
                st.write(f"  - {attr} ({adef.get('type', '')}): {adef.get('description', '')}")
        st.write("**边类型**:")
        for et, et_def in schema.get("edge_types", {}).items():
            directed = "有向" if et_def.get("directed") else "无向"
            st.write(f"- **{et}** ({directed}): {et_def.get('description', '')}")
            for prop, pdef in et_def.get("properties", {}).items():
                st.write(f"  - {prop} ({pdef.get('type', '')}): {pdef.get('description', '')}")


def dataset_selector() -> tuple[Any, Dict[str, Any]] | tuple[None, dict]:
    entries = load_sample_index()
    if not entries:
        st.error("未找到样本数据集，请检查 data/samples/index.json")
        return None, {}

    groups: Dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(e["data_type"], []).append(e)

    type_labels = {"timeseries": "📈 时序数据", "table": "📊 多维表格", "json": "🗂️ JSON", "network": "🕸️ 网络数据"}
    selected_type = st.selectbox("选择数据类型", list(groups.keys()), format_func=lambda x: type_labels.get(x, x))

    type_entries = groups.get(selected_type, [])
    selected_entry = st.selectbox(
        "选择数据集",
        type_entries,
        format_func=lambda x: f"{x.get('title', x['slug'])} — {x.get('description', '')[:40]}...",
    )

    data, meta = load_dataset(selected_entry)

    st.divider()
    st.subheader("📋 数据预览")
    if isinstance(data, pd.DataFrame):
        st.dataframe(data.head(5), use_container_width=True)
        st.caption(f"形状: {data.shape}")
    elif isinstance(data, dict) and "nodes" in data and "edges" in data:
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**节点数**: {len(data['nodes'])}")
            st.json(data["nodes"][:2], expanded=False)
        with c2:
            st.write(f"**边数**: {len(data['edges'])}")
            st.json(data["edges"][:2], expanded=False)
    elif isinstance(data, list):
        st.write(f"**记录数**: {len(data)}")
        st.json(data[:2], expanded=False)
    else:
        st.json(data, expanded=False)

    st.divider()
    st.subheader("📖 数据元数据 (Schema)")
    render_meta_preview(meta)

    return data, meta


# -----------------------------------------------------------------------------
# Workflow UI
# -----------------------------------------------------------------------------
def _step_icon(status: str) -> str:
    return {"COMPLETED": "✅", "FAILED": "❌", "IN_PROGRESS": "🔄", "PENDING": "⏳"}.get(status, "⏳")


def render_step_output(step_id: str, out: AgentOutput) -> None:
    """Render the output artifacts of a single workflow step."""
    artifacts = out.artifacts

    if step_id == "context_analysis":
        if artifacts.get("context_brief"):
            st.json(artifacts["context_brief"])

    elif step_id == "data_analysis":
        analysis_plan = artifacts.get("analysis_plan", {})
        if analysis_plan:
            st.write(f"**检测到的数据类型**: {analysis_plan.get('data_type_detected', '-')}")
            st.write(f"**判断理由**: {analysis_plan.get('rationale', '')}")
            methods = analysis_plan.get("methods", [])
            if methods:
                st.write("**计划执行的分析方法**:")
                for m in methods:
                    st.write(f"- **{m.get('method', '')}**: {m.get('purpose', '')} → {m.get('expected_output', '')}")

        findings = artifacts.get("findings", [])
        st.divider()
        if findings:
            st.write(f"**实际发现数**: {len(findings)}")
            for f in findings[:10]:
                metric = f.get("metric", "")
                value = f.get("value", "")
                desc = f.get("description", "")
                st.write(f"- **{metric}**: {value} ({desc})")
        else:
            st.info("未发现结构化 findings")
        if artifacts.get("code"):
            with st.expander("执行代码"):
                st.code(artifacts["code"], language="python")
        skill_exec = artifacts.get("skill_execution")
        if skill_exec:
            st.caption(f"代码执行: {'成功' if skill_exec.get('success') else '失败'} | stdout: {skill_exec.get('stdout', '')[:100]}")

    elif step_id == "data_insight":
        insights = artifacts.get("insights", [])
        if insights:
            st.write(f"**洞察数量**: {len(insights)}")
            for idx, ins in enumerate(insights):
                priority = ins.get("priority", "medium")
                emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                with st.expander(f"{emoji} 洞察 {idx+1}: {ins.get('title', '')}", expanded=(idx == 0)):
                    st.write(f"**描述**: {ins.get('description', '')}")
                    st.write(f"**类型**: {ins.get('insight_type', '')}")
                    st.write(f"**优先级**: {priority}")
                    st.write(f"**推荐图表**: {ins.get('recommended_chart', '')}")
                    sd = ins.get("supporting_data", {})
                    if sd:
                        st.write(f"**支撑数据类型**: {sd.get('viz_type', '')}")
                        if sd.get("series"):
                            st.write(f"**系列数**: {len(sd['series'])}")
                        if sd.get("categories"):
                            st.write(f"**类别数**: {len(sd['categories'])}")
                        if sd.get("nodes"):
                            st.write(f"**节点数**: {len(sd['nodes'])}, **边数**: {len(sd.get('edges', []))}")
        else:
            st.info("未提取到洞察")

    elif step_id == "story_ideation":
        if artifacts.get("big_idea"):
            st.markdown(f"**💡 核心观点**: {artifacts['big_idea']}")
        if artifacts.get("elevator_pitch"):
            st.markdown(f"**🎤 三分钟故事**: {artifacts['elevator_pitch']}")
        storyboard = artifacts.get("storyboard", [])
        if storyboard:
            st.write("**📋 故事板**:")
            for page in storyboard:
                st.write(f"- 第 {page.get('page', '?')} 页: **{page.get('title', '')}** — {page.get('content', '')}")
        insights_used = artifacts.get("insights_used", [])
        st.caption(f"基于 {len(insights_used)} 个数据洞察构建")

    elif step_id == "visualization":
        if artifacts.get("chart_type"):
            st.write(f"**图表类型**: {artifacts['chart_type']}")
        if artifacts.get("title"):
            st.write(f"**标题**: {artifacts['title']}")
        if artifacts.get("rationale"):
            st.write(f"**设计理由**: {artifacts['rationale']}")
        if artifacts.get("accessibility_notes"):
            st.write(f"**无障碍备注**: {artifacts['accessibility_notes']}")
        files = artifacts.get("files", [])
        if files:
            for fp in files:
                if Path(fp).exists():
                    st.image(fp, use_container_width=True)
        else:
            st.info("未生成图表文件")
        if artifacts.get("code"):
            with st.expander("图表代码"):
                st.code(artifacts["code"], language="python")
        skill_exec = artifacts.get("skill_execution")
        if skill_exec:
            st.caption(f"代码执行: {'成功' if skill_exec.get('success') else '失败'}")
            if skill_exec.get("stderr"):
                st.caption(f"stderr: {skill_exec['stderr'][:200]}")

    elif step_id == "storytelling":
        if artifacts.get("big_idea"):
            st.markdown(f"**💡 核心观点**: {artifacts['big_idea']}")
        if artifacts.get("elevator_pitch"):
            st.markdown(f"**🎤 三分钟故事**: {artifacts['elevator_pitch']}")
        report = artifacts.get("report", "")
        if report:
            st.markdown(report[:800] + ("..." if len(report) > 800 else ""))
        else:
            st.info("未生成报告")
        takeaways = artifacts.get("key_takeaways", [])
        if takeaways:
            st.write("**关键要点**:")
            for t in takeaways:
                st.write(f"- {t}")
        embedded = artifacts.get("embedded_files", [])
        if embedded:
            st.write(f"**嵌入图表数**: {len(embedded)}")

    else:
        st.json(artifacts)


def _run_step(step_id: str, engine: WorkflowEngine, agent_input: AgentInput, progress_placeholder: Any) -> None:
    outputs = st.session_state["workflow_outputs"]
    run_dir = st.session_state["run_dir"]
    if not run_dir:
        run_dir = str(Path(engine.output_dir) / f"run_step_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")
        Path(run_dir).mkdir(parents=True, exist_ok=True)
        st.session_state["run_dir"] = run_dir

    def cb(s: str, e: str, d: Any = None):
        lines = st.session_state["progress_lines"]
        name = dict(STEPS).get(s, s)
        if e == "start":
            lines.append(f"🔄 {name} 开始...")
        elif e == "complete":
            for i in range(len(lines)):
                if lines[i].endswith(f"{name} 开始..."):
                    lines[i] = f"✅ {name} 完成"
                    break
        elif e == "fail":
            for i in range(len(lines)):
                if lines[i].endswith(f"{name} 开始..."):
                    lines[i] = f"❌ {name} 失败"
                    break
        st.session_state["progress_lines"] = lines
        progress_placeholder.markdown("\n".join(lines))

    engine.step_callback = cb
    out = engine.run_step(step_id, agent_input, outputs, run_dir)
    outputs[step_id] = out
    st.session_state["workflow_outputs"] = outputs

    # If storytelling just completed, persist report to session result for convenience
    if step_id == "storytelling":
        tasks = engine.restore_tasks(outputs)
        st.session_state["result"] = WorkflowResult(
            input=agent_input,
            tasks=tasks,
            evaluation=st.session_state.get("eval_report"),
            final_report=out.artifacts.get("report", ""),
            output_dir=run_dir,
        )


def _run_evaluation(engine: WorkflowEngine, agent_input: AgentInput) -> None:
    outputs = st.session_state["workflow_outputs"]
    if "storytelling" not in outputs:
        st.warning("请先完成故事构建步骤。")
        return
    ev = engine.evaluate_only(agent_input, outputs)
    st.session_state["eval_report"] = ev
    result = st.session_state.get("result")
    if result:
        result.evaluation = ev
    else:
        tasks = engine.restore_tasks(outputs)
        st.session_state["result"] = WorkflowResult(
            input=agent_input,
            tasks=tasks,
            evaluation=ev,
            final_report=outputs["storytelling"].artifacts.get("report", ""),
            output_dir=st.session_state["run_dir"] or "",
        )


def _run_all_steps(engine: WorkflowEngine, agent_input: AgentInput, progress_placeholder: Any) -> None:
    outputs: Dict[str, AgentOutput] = {}

    def cb(s: str, e: str, d: Any = None):
        lines = st.session_state["progress_lines"]
        name = dict(STEPS).get(s, s)
        if e == "start":
            lines.append(f"🔄 {name} 开始...")
        elif e == "complete":
            for i in range(len(lines)):
                if lines[i].endswith(f"{name} 开始..."):
                    lines[i] = f"✅ {name} 完成"
                    break
        elif e == "fail":
            for i in range(len(lines)):
                if lines[i].endswith(f"{name} 开始..."):
                    lines[i] = f"❌ {name} 失败"
                    break
        st.session_state["progress_lines"] = lines
        progress_placeholder.markdown("\n".join(lines))

    engine.step_callback = cb
    result = engine.run(agent_input)
    st.session_state["result"] = result
    st.session_state["run_dir"] = result.output_dir
    # Rebuild outputs dict from tasks
    outputs_map: Dict[str, AgentOutput] = {}
    for t in result.tasks:
        outputs_map[t.id] = AgentOutput(
            agent_name=t.agent,
            status=t.status,
            artifacts=t.artifacts or {},
        )
    st.session_state["workflow_outputs"] = outputs_map
    st.session_state["eval_report"] = result.evaluation


def _is_step_enabled(step_id: str, outputs: Dict[str, AgentOutput]) -> bool:
    """Check if a step can be run based on DAG dependencies."""
    deps_map = {
        "context_analysis": [],
        "data_analysis": ["context_analysis"],
        "data_insight": ["data_analysis"],
        "story_ideation": ["data_insight"],
        "visualization": ["data_insight"],
        "storytelling": ["story_ideation", "visualization"],
    }
    deps = deps_map.get(step_id, [])
    for dep in deps:
        dep_out = outputs.get(dep)
        if not dep_out or dep_out.status != TaskStatus.COMPLETED:
            return False
    return True


def render_step_controls(engine: WorkflowEngine, agent_input: AgentInput, progress_placeholder: Any) -> None:
    outputs = st.session_state["workflow_outputs"]

    st.subheader("🔧 分步执行")
    st.caption("故事构思和可视化设计可以并行执行；前置步骤未完成时后续按钮不可用。")

    step_keys = [s[0] for s in STEPS if s[0] != "evaluation"]
    labels = [dict(STEPS)[k] for k in step_keys]

    # Row 1: context_analysis + data_analysis
    cols1 = st.columns(2)
    for idx, step_id in enumerate(["context_analysis", "data_analysis"]):
        with cols1[idx]:
            out = outputs.get(step_id)
            status = out.status.value if out else "PENDING"
            icon = _step_icon(status)
            disabled = not _is_step_enabled(step_id, outputs)
            if status == "COMPLETED":
                st.success(f"{icon} {labels[step_keys.index(step_id)]}")
            elif status == "FAILED":
                st.error(f"{icon} {labels[step_keys.index(step_id)]}")
            else:
                if st.button(f"{icon} 运行{labels[step_keys.index(step_id)]}", key=f"btn_{step_id}", disabled=disabled):
                    _run_step(step_id, engine, agent_input, progress_placeholder)
                    st.rerun()

    # Row 2: data_insight
    cols2 = st.columns(1)
    with cols2[0]:
        step_id = "data_insight"
        out = outputs.get(step_id)
        status = out.status.value if out else "PENDING"
        icon = _step_icon(status)
        disabled = not _is_step_enabled(step_id, outputs)
        if status == "COMPLETED":
            st.success(f"{icon} {labels[step_keys.index(step_id)]}")
        elif status == "FAILED":
            st.error(f"{icon} {labels[step_keys.index(step_id)]}")
        else:
            if st.button(f"{icon} 运行{labels[step_keys.index(step_id)]}", key=f"btn_{step_id}", disabled=disabled):
                _run_step(step_id, engine, agent_input, progress_placeholder)
                st.rerun()

    # Row 3: story_ideation + visualization (parallel)
    cols3 = st.columns(2)
    for idx, step_id in enumerate(["story_ideation", "visualization"]):
        with cols3[idx]:
            out = outputs.get(step_id)
            status = out.status.value if out else "PENDING"
            icon = _step_icon(status)
            disabled = not _is_step_enabled(step_id, outputs)
            if status == "COMPLETED":
                st.success(f"{icon} {labels[step_keys.index(step_id)]}")
            elif status == "FAILED":
                st.error(f"{icon} {labels[step_keys.index(step_id)]}")
            else:
                if st.button(f"{icon} 运行{labels[step_keys.index(step_id)]}", key=f"btn_{step_id}", disabled=disabled):
                    _run_step(step_id, engine, agent_input, progress_placeholder)
                    st.rerun()

    # Row 4: storytelling
    cols4 = st.columns(1)
    with cols4[0]:
        step_id = "storytelling"
        out = outputs.get(step_id)
        status = out.status.value if out else "PENDING"
        icon = _step_icon(status)
        disabled = not _is_step_enabled(step_id, outputs)
        if status == "COMPLETED":
            st.success(f"{icon} {labels[step_keys.index(step_id)]}")
        elif status == "FAILED":
            st.error(f"{icon} {labels[step_keys.index(step_id)]}")
        else:
            if st.button(f"{icon} 运行{labels[step_keys.index(step_id)]}", key=f"btn_{step_id}", disabled=disabled):
                _run_step(step_id, engine, agent_input, progress_placeholder)
                st.rerun()

    st.divider()

    # Show outputs for completed steps
    for step_id, label in STEPS:
        if step_id == "evaluation":
            continue
        out = outputs.get(step_id)
        if out and out.status == TaskStatus.COMPLETED:
            with st.expander(f"📄 {label} 结果", expanded=False):
                render_step_output(step_id, out)
        elif out and out.status == TaskStatus.FAILED:
            with st.expander(f"❌ {label} 失败详情", expanded=False):
                st.error(out.error or "未知错误")
                if out.artifacts:
                    st.json(out.artifacts)

    st.divider()
    st.subheader("🚀 一键完成")
    if st.button("一键运行全部步骤 + 评估", key="btn_run_all"):
        with st.spinner("正在执行完整工作流..."):
            _run_all_steps(engine, agent_input, progress_placeholder)
        st.rerun()

    if "storytelling" in outputs and outputs["storytelling"].status == TaskStatus.COMPLETED:
        if st.button("运行质量评估", key="btn_eval"):
            with st.spinner("正在评估..."):
                _run_evaluation(engine, agent_input)
            st.rerun()


# -----------------------------------------------------------------------------
# Tabs renderers
# -----------------------------------------------------------------------------
def render_task_board() -> None:
    st.subheader("任务看板")
    result = st.session_state.get("result")
    if not result:
        st.info("尚未运行任何步骤。")
        return
    tasks = result.tasks
    if not tasks:
        st.info("暂无任务。")
        return
    cols = st.columns(len(tasks))
    icon_map = {
        "PENDING": "⏳",
        "IN_PROGRESS": "🔄",
        "COMPLETED": "✅",
        "FAILED": "❌",
        "SKIPPED": "⏭️",
    }
    for col, task in zip(cols, tasks):
        with col:
            st.metric(
                label=f"{icon_map.get(task.status.value, '❓')} {task.name}",
                value=task.status.value,
            )
            if task.error:
                st.error(task.error)


def collect_chart_files() -> list[str]:
    """Collect all chart files generated during workflow."""
    files: list[str] = []
    outputs = st.session_state.get("workflow_outputs", {})
    for out in outputs.values():
        if isinstance(out, AgentOutput):
            files.extend(out.artifacts.get("files", []) or [])
    # Also include copied files in run_dir
    run_dir = st.session_state.get("run_dir")
    if run_dir and Path(run_dir).exists():
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.html"):
            files.extend(str(p) for p in Path(run_dir).rglob(ext))
    # Deduplicate while preserving order
    seen = set()
    deduped: list[str] = []
    for f in files:
        rp = str(Path(f).resolve())
        if rp not in seen and Path(f).exists():
            seen.add(rp)
            deduped.append(f)
    return deduped


def render_visualizations() -> None:
    st.subheader("生成的可视化图表")
    chart_files = collect_chart_files()
    if not chart_files:
        st.info("未生成可视化文件。")
        return
    cols = st.columns(min(len(chart_files), 3))
    for idx, (col, path) in enumerate(zip(cols, chart_files)):
        with col:
            st.image(path, use_container_width=True)
            with open(path, "rb") as f:
                st.download_button("下载", f.read(), file_name=Path(path).name, key=f"dl_{idx}_{Path(path).name}")


def render_report() -> None:
    st.subheader("最终叙事报告")
    result = st.session_state.get("result")
    if not result:
        st.info("尚未生成报告。")
        return

    report = result.final_report or ""
    outputs = st.session_state.get("workflow_outputs", {})
    story_out = outputs.get("storytelling")

    # Show big idea and elevator pitch prominently
    if story_out:
        big_idea = story_out.artifacts.get("big_idea", "")
        elevator_pitch = story_out.artifacts.get("elevator_pitch", "")
        if big_idea:
            st.markdown(f"## 💡 核心观点\n\n> {big_idea}")
        if elevator_pitch:
            st.markdown(f"## 🎤 三分钟故事\n\n{elevator_pitch}")
        st.divider()

    if report:
        # Parse markdown image tags and render images inline
        _render_markdown_with_images(report)
    else:
        st.info("报告内容为空。")

    st.divider()
    download_button(report, "report.md", "📥 下载报告 (.md)")

    # Also show all charts below the report for convenience
    chart_files = collect_chart_files()
    if chart_files:
        st.subheader("报告中的可视化图表")
        cols = st.columns(min(len(chart_files), 3))
        for idx, (col, path) in enumerate(zip(cols, chart_files)):
            with col:
                st.image(path, use_container_width=True)


def _render_markdown_with_images(report: str) -> None:
    """Split markdown by image tags and render images using Streamlit."""
    pattern = r"!\[(.*?)\]\((.+?)\)"
    last_end = 0
    for match in re.finditer(pattern, report):
        start, end = match.span()
        text_before = report[last_end:start]
        if text_before.strip():
            st.markdown(text_before)
        alt, src = match.groups()
        src = src.strip()
        # Try to resolve path
        path_candidates = [Path(src)]
        run_dir = st.session_state.get("run_dir")
        if run_dir:
            path_candidates.append(Path(run_dir) / src)
            path_candidates.extend(Path(run_dir).rglob(Path(src).name))
        found = None
        for p in path_candidates:
            if p.exists():
                found = p
                break
        if found:
            st.image(str(found), caption=alt or None, use_container_width=True)
        else:
            st.markdown(f"![{alt}]({src})")
        last_end = end
    text_after = report[last_end:]
    if text_after.strip():
        st.markdown(text_after)


def render_evaluation() -> None:
    st.subheader("质量评估")
    result = st.session_state.get("result")
    ev = result.evaluation if result else None
    if not ev:
        st.info("评估结果不可用。")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("综合得分", f"{ev.overall_score:.2f}")
    col2.metric("等级", ev.grade)
    col3.metric("是否通过", "通过" if ev.passed else "未通过")

    metrics = list(ev.metrics.keys())
    values = [ev.metrics[m].weighted for m in metrics]
    fig = go.Figure(
        data=go.Scatterpolar(
            r=values + [values[0]],
            theta=metrics + [metrics[0]],
            fill="toself",
            name="Scores",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False,
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("指标详情"):
        for metric, agg in ev.metrics.items():
            st.write(f"**{metric}**: {agg.weighted:.2f} (标准差 {agg.std:.2f}, 一致性 {agg.consensus})")
            for js in agg.judge_scores:
                st.write(f"- {js.provider} (权重 {js.weight}): {js.score:.2f}")

    with st.expander("优势"):
        for s in ev.strengths or ["暂无"]:
            st.write(f"- {s}")
    with st.expander("劣势"):
        for w in ev.weaknesses or ["暂无"]:
            st.write(f"- {w}")
    with st.expander("改进建议"):
        for i in ev.improvements or ["暂无"]:
            st.write(f"- {i}")

    json_data = json.dumps(ev.model_dump(mode="json"), ensure_ascii=False, indent=2)
    download_button(json_data, "evaluation.json", "📥 下载评估 (.json)")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    st.title("🎙️ AI 数据叙事")
    st.caption("将数据自动转化为引人入胜的数据叙事。")

    st.sidebar.header("LLM Provider 配置")
    llm = provider_selector()
    pass_threshold = st.sidebar.slider("通过阈值", 0.0, 1.0, DEFAULT_PASS_THRESHOLD, 0.05)

    tab_config, tab_workflow, tab_viz, tab_report, tab_eval = st.tabs(
        ["⚙️ 配置", "🔄 工作流", "📊 可视化", "📝 报告", "✅ 评估"]
    )

    with tab_config:
        st.subheader("选择数据集")
        data, data_description = dataset_selector()

        st.divider()
        st.subheader("叙事请求")
        user_request = st.text_area("用户请求", value="分析该数据集并讲述关键驱动因素的故事。")
        background = st.text_area("背景 / 上下文", value="")
        audience = st.text_input("目标受众", value="业务高管")

        if data is not None:
            agent_input = AgentInput(
                user_request=user_request,
                background=background,
                audience=audience,
                data=data,
                data_description=data_description,
                pass_threshold=pass_threshold,
            )
            st.divider()
            progress_placeholder = st.empty()
            progress_placeholder.markdown("\n".join(st.session_state.get("progress_lines", [])))
            render_step_controls(WorkflowEngine(llm=llm, judge_providers=[llm]), agent_input, progress_placeholder)
        else:
            st.info("请先选择一个数据集。")

    with tab_workflow:
        render_task_board()

    with tab_viz:
        render_visualizations()

    with tab_report:
        render_report()

    with tab_eval:
        render_evaluation()


if __name__ == "__main__":
    main()
