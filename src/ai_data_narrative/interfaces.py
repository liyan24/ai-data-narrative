"""Abstract interfaces for agents, skills, evaluators, and LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ai_data_narrative.models import (
    AgentInput,
    AgentOutput,
    AgentPlan,
    EvaluationReport,
    ReportFragment,
    ReviewResult,
    SkillOutput,
    SkillPlan,
    ValidationResult,
    WorkflowResult,
)


class BaseLLMProvider(ABC):
    """Abstract LLM provider. Implementations must be thread-safe."""

    name: str = "base"
    weight: float = 1.0

    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> str | Dict[str, Any]:
        """Return either raw text or parsed JSON dict."""
        ...


class BaseSkill(ABC):
    """Abstract skill following plan -> validate -> execute lifecycle."""

    name: str = "base_skill"

    @abstractmethod
    def plan(self, context: Dict[str, Any]) -> SkillPlan:
        """Produce an execution plan from context."""
        ...

    @abstractmethod
    def validate_plan(self, plan: SkillPlan) -> ValidationResult:
        """Validate plan before execution."""
        ...

    @abstractmethod
    def execute(self, plan: SkillPlan, context: Dict[str, Any]) -> SkillOutput:
        """Execute the skill and return outputs + file paths."""
        ...


class BaseAgent(ABC):
    """Abstract agent with a standardized lifecycle."""

    name: str = "base_agent"
    role: str = ""
    system_prompt: str = ""

    def __init__(self, llm: BaseLLMProvider, skills: List[BaseSkill] | None = None):
        self.llm = llm
        self.skills: List[BaseSkill] = skills or []
        self._skill_registry: Dict[str, BaseSkill] = {s.name: s for s in self.skills}

    def get_skill(self, name: str) -> BaseSkill | None:
        return self._skill_registry.get(name)

    @abstractmethod
    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        ...

    @abstractmethod
    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        ...

    @abstractmethod
    def review(self, output: AgentOutput) -> ReviewResult:
        ...

    @abstractmethod
    def report(self, output: AgentOutput) -> ReportFragment:
        ...

    def run(self, context: Dict[str, Any]) -> AgentOutput:
        plan = self.plan(context)
        output = self.execute(plan, context)
        review = self.review(output)
        if not review.passed and review.suggestions:
            output.artifacts["review"] = review.model_dump()
        return output


class BaseEvaluator(ABC):
    """Abstract evaluator for a single quality metric."""

    metric: str = "base"

    @abstractmethod
    def evaluate(
        self,
        narrative_report: str,
        data: Any,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Return a dict compatible with ScoreDetails."""
        ...


class BaseWorkflowEngine(ABC):
    """Abstract workflow engine that orchestrates agents."""

    @abstractmethod
    def run(self, agent_input: AgentInput) -> WorkflowResult:
        ...
