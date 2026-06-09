"""Orchestrates the AI data narrative workflow."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ai_data_narrative.agents import (
    CodeReviewAgent,
    ContextAnalysisAgent,
    DataAnalysisAgent,
    DataInsightAgent,
    StoryIdeationAgent,
    StorytellingAgent,
    VisualizationDesignAgent,
)
from ai_data_narrative.config import OUTPUT_DIR
from ai_data_narrative.evaluation import (
    ComprehensibilityEvaluator,
    EvaluationReportBuilder,
    FactualAccuracyEvaluator,
    InformationCompletenessEvaluator,
    MultiLLMJudge,
    NarrativeCoherenceEvaluator,
    StructuralFidelityEvaluator,
)
from ai_data_narrative.execution import Sandbox
from ai_data_narrative.interfaces import BaseLLMProvider
from ai_data_narrative.models import (
    AgentInput,
    AgentOutput,
    EvaluationReport,
    Task,
    TaskStatus,
    WorkflowResult,
)
from ai_data_narrative.skills import DataAnalysisSkill, DataStorytellingSkill, DataVisualizationSkill
from ai_data_narrative.workflow.todo_manager import TodoManager


StepCallback = Callable[[str, str, Any], None]

STEPS = [
    ("context_analysis", "背景分析"),
    ("data_analysis", "数据分析"),
    ("data_insight", "数据洞察"),
    ("story_ideation", "故事构思"),
    ("visualization", "可视化设计"),
    ("storytelling", "故事讲述"),
    ("evaluation", "质量评估"),
]


class WorkflowEngine:
    """Runs the AI data narrative pipeline with data insight extraction."""

    def __init__(
        self,
        llm: BaseLLMProvider,
        output_dir: Optional[str] = None,
        sandbox: Optional[Sandbox] = None,
        judge_providers: Optional[List[BaseLLMProvider]] = None,
        step_callback: Optional[StepCallback] = None,
    ):
        self.llm = llm
        self.output_dir = output_dir or str(OUTPUT_DIR)
        self.sandbox = sandbox or Sandbox()
        self.todo = TodoManager()
        self._outputs: Dict[str, AgentOutput] = {}
        self.step_callback = step_callback

        # Skills
        self.analysis_skill = DataAnalysisSkill(llm=llm, sandbox=self.sandbox, output_dir=self.output_dir)
        self.viz_skill = DataVisualizationSkill(llm=llm, sandbox=self.sandbox, output_dir=self.output_dir)
        self.story_skill = DataStorytellingSkill(llm=llm, sandbox=self.sandbox, output_dir=self.output_dir)

        # Agents
        self.context_agent = ContextAnalysisAgent(llm=llm)
        self.data_agent = DataAnalysisAgent(llm=llm, skills=[self.analysis_skill])
        self.insight_agent = DataInsightAgent(llm=llm, skills=[self.analysis_skill])
        self.story_ideation_agent = StoryIdeationAgent(llm=llm)
        self.viz_agent = VisualizationDesignAgent(llm=llm, skills=[self.viz_skill])
        self.story_agent = StorytellingAgent(llm=llm, skills=[self.story_skill])
        self.review_agent = CodeReviewAgent(llm=llm)

        # Evaluators
        self.evaluators = {
            "IC": InformationCompletenessEvaluator(),
            "FA": FactualAccuracyEvaluator(),
            "NC": NarrativeCoherenceEvaluator(),
            "CP": ComprehensibilityEvaluator(),
            "SF": StructuralFidelityEvaluator(),
        }
        self.judge_providers = judge_providers or [llm]
        self.report_builder = EvaluationReportBuilder()

    def _emit(self, step: str, event: str, data: Any = None) -> None:
        if self.step_callback:
            self.step_callback(step, event, data)

    def _init_todo(self) -> None:
        self.todo = TodoManager()
        agent_map = {
            "context_analysis": self.context_agent,
            "data_analysis": self.data_agent,
            "data_insight": self.insight_agent,
            "story_ideation": self.story_ideation_agent,
            "visualization": self.viz_agent,
            "storytelling": self.story_agent,
        }
        deps_map = {
            "context_analysis": [],
            "data_analysis": ["context_analysis"],
            "data_insight": ["data_analysis"],
            "story_ideation": ["data_insight"],
            "visualization": ["data_insight"],
            "storytelling": ["story_ideation", "visualization"],
        }
        for task_id, deps in deps_map.items():
            agent = agent_map[task_id]
            self.todo.add_task(
                task_id=task_id,
                name=agent.name.replace("_", " ").title(),
                agent=agent.name,
                dependencies=deps,
            )

    def run(self, agent_input: AgentInput) -> WorkflowResult:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(self.output_dir, f"run_{run_id}")
        os.makedirs(run_dir, exist_ok=True)

        self._init_todo()
        outputs: Dict[str, AgentOutput] = {}

        for step_id, _label in STEPS:
            if step_id == "evaluation":
                break
            out = self.run_step(step_id, agent_input, outputs, run_dir)
            outputs[step_id] = out

        final_report = outputs.get("storytelling", AgentOutput(agent_name="storytelling")).artifacts.get("report", "")

        # Evaluation
        self._emit("evaluation", "start")
        evaluation = self._evaluate(final_report, agent_input.data)
        self._emit("evaluation", "complete", evaluation.model_dump(mode="json"))

        self._persist_outputs(agent_input, outputs, evaluation, final_report, run_dir)
        self._outputs = outputs
        return WorkflowResult(
            input=agent_input,
            tasks=self.todo.list_tasks(),
            evaluation=evaluation,
            final_report=final_report,
            output_dir=run_dir,
        )

    def run_step(
        self,
        step_id: str,
        agent_input: AgentInput,
        outputs: Dict[str, AgentOutput],
        run_dir: str,
    ) -> AgentOutput:
        """Run a single workflow step and return its output."""
        if not self.todo.get_task(step_id):
            self.restore_tasks(outputs)

        context = self._build_context(step_id, agent_input, outputs)
        self._emit(step_id, "start")
        out = self._run_agent(step_id, context, run_dir)
        self._emit(step_id, "complete", out.artifacts)
        return out

    def evaluate_only(
        self,
        agent_input: AgentInput,
        outputs: Dict[str, AgentOutput],
    ) -> EvaluationReport:
        """Run evaluation given completed outputs."""
        final_report = outputs.get("storytelling", AgentOutput(agent_name="storytelling")).artifacts.get("report", "")
        self._emit("evaluation", "start")
        evaluation = self._evaluate(final_report, agent_input.data)
        self._emit("evaluation", "complete", evaluation.model_dump(mode="json"))
        return evaluation

    def _build_context(
        self,
        step_id: str,
        agent_input: AgentInput,
        outputs: Dict[str, AgentOutput],
    ) -> Dict[str, Any]:
        if step_id == "context_analysis":
            return {"input": agent_input.model_dump()}
        if step_id == "data_analysis":
            return {
                "input": agent_input.model_dump(),
                "data": agent_input.data,
                "data_description": agent_input.data_description,
                "previous_output": outputs.get("context_analysis", AgentOutput(agent_name="context_analysis")).artifacts,
            }
        if step_id == "data_insight":
            data_out = outputs.get("data_analysis", AgentOutput(agent_name="data_analysis"))
            return {
                "previous_output": data_out.artifacts,
                "data": agent_input.data,
                "data_description": agent_input.data_description,
            }
        if step_id == "story_ideation":
            insight_out = outputs.get("data_insight", AgentOutput(agent_name="data_insight"))
            analysis_out = outputs.get("data_analysis", AgentOutput(agent_name="data_analysis"))
            return {
                "previous_output": {
                    "analysis_plan": analysis_out.artifacts.get("analysis_plan", {}),
                    "insights": insight_out.artifacts.get("insights", []),
                    "findings": analysis_out.artifacts.get("findings", []),
                },
                "data_description": agent_input.data_description,
            }
        if step_id == "visualization":
            insight_out = outputs.get("data_insight", AgentOutput(agent_name="data_insight"))
            analysis_out = outputs.get("data_analysis", AgentOutput(agent_name="data_analysis"))
            return {
                "data": agent_input.data,
                "data_description": agent_input.data_description,
                "previous_output": {
                    "findings": analysis_out.artifacts.get("findings", []),
                    "insights": insight_out.artifacts.get("insights", []),
                },
            }
        if step_id == "storytelling":
            ideation_out = outputs.get("story_ideation", AgentOutput(agent_name="story_ideation"))
            viz_out = outputs.get("visualization", AgentOutput(agent_name="visualization"))
            return {
                "input": agent_input.model_dump(),
                "story_ideation_output": ideation_out.artifacts,
                "visualization_output": viz_out.artifacts,
            }
        raise ValueError(f"Unknown step_id: {step_id}")

    def _run_agent(self, task_id: str, context: Dict[str, Any], run_dir: str) -> AgentOutput:
        self.todo.start_task(task_id)
        agent = self._agent_for(task_id)
        try:
            plan = agent.plan(context)
            output = agent.execute(plan, context)
            review = agent.review(output)
            output.artifacts["review"] = review.model_dump()
            # Copy generated files into the run directory for easy access
            copied = self._copy_files_to_run_dir(output, run_dir, task_id)
            if copied:
                output.artifacts["files"] = copied
            self._outputs[task_id] = output
            self.todo.complete_task(task_id, artifacts=output.artifacts)
            return output
        except Exception as exc:
            self.todo.fail_task(task_id, error=str(exc))
            self._emit(task_id, "fail", {"error": str(exc)})
            return AgentOutput(
                agent_name=task_id,
                status=TaskStatus.FAILED,
                error=str(exc),
            )

    def _agent_for(self, task_id: str):
        return {
            "context_analysis": self.context_agent,
            "data_analysis": self.data_agent,
            "data_insight": self.insight_agent,
            "story_ideation": self.story_ideation_agent,
            "visualization": self.viz_agent,
            "storytelling": self.story_agent,
        }[task_id]

    def _copy_files_to_run_dir(self, output: AgentOutput, run_dir: str, task_id: str) -> List[str]:
        files = output.artifacts.get("files", []) or []
        if not files:
            return []
        task_dir = Path(run_dir) / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        copied: List[str] = []
        for src in files:
            src_path = Path(src)
            if not src_path.exists():
                continue
            dst = task_dir / src_path.name
            try:
                shutil.copy2(str(src_path), str(dst))
                copied.append(str(dst))
            except Exception:
                continue
        return copied

    def _evaluate(self, report: str, data: Any) -> Any:
        judge = MultiLLMJudge(self.judge_providers)
        metric_scores = {}
        all_strengths: List[str] = []
        all_weaknesses: List[str] = []
        all_improvements: List[str] = []
        for metric, evaluator in self.evaluators.items():
            raw = evaluator.evaluate(report, data)
            prompt = (
                f"评估任务。请为以下报告的 {metric} 指标打分。\n\n"
                f"报告:\n{report[:3000]}\n\n"
                f"自动评估备注: {raw.get('reasoning', '')}\n"
                "请以 JSON 格式回复: {{\"score\": float 0-1, \"reasoning\": string}}"
            )
            agg = judge.score_metric(metric, report, prompt)
            metric_scores[metric] = agg
            if raw.get("suggestions"):
                all_improvements.extend(raw["suggestions"])
            if agg.weighted >= 0.8:
                all_strengths.append(f"{metric}: {agg.weighted:.2f}")
            elif agg.weighted < 0.6:
                all_weaknesses.append(f"{metric}: {agg.weighted:.2f}")

        return self.report_builder.build(
            metric_scores,
            strengths=all_strengths,
            weaknesses=all_weaknesses,
            improvements=all_improvements,
        )

    def _persist_outputs(
        self,
        agent_input: AgentInput,
        outputs: Dict[str, AgentOutput],
        evaluation: Any,
        final_report: str,
        run_dir: str,
    ) -> None:
        report_path = os.path.join(run_dir, "report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(final_report or "# 未生成报告")

        eval_path = os.path.join(run_dir, "evaluation.json")
        with open(eval_path, "w", encoding="utf-8") as f:
            f.write(self.report_builder.to_json(evaluation))

        eval_md_path = os.path.join(run_dir, "evaluation.md")
        with open(eval_md_path, "w", encoding="utf-8") as f:
            f.write(self.report_builder.to_markdown(evaluation))

        summary_path = os.path.join(run_dir, "workflow_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "input": agent_input.model_dump(),
                    "tasks": [t.model_dump(mode="json") for t in self.todo.list_tasks()],
                    "final_report_path": report_path,
                    "evaluation_path": eval_path,
                },
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    def restore_tasks(self, outputs: Dict[str, AgentOutput]) -> List[Task]:
        """Rebuild TodoManager task list from existing outputs (used in step-by-step UI)."""
        self._init_todo()
        for step_id, _label in STEPS:
            if step_id == "evaluation":
                continue
            out = outputs.get(step_id)
            if out is None:
                continue
            try:
                self.todo.start_task(step_id)
            except ValueError:
                pass
            if out.status == TaskStatus.FAILED:
                self.todo.fail_task(step_id, error=out.error or "")
            else:
                self.todo.complete_task(step_id, artifacts=out.artifacts)
        return self.todo.list_tasks()
