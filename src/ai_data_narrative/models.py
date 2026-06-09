"""Pydantic data models for the AI data narrative system."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Task(BaseModel):
    id: str = Field(..., description="Unique task identifier")
    name: str
    description: str = ""
    agent: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.HIGH
    dependencies: List[str] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Progress(BaseModel):
    total: int
    completed: int
    failed: int
    skipped: int
    in_progress: int
    pending: int
    percent: float


class AgentInput(BaseModel):
    user_request: str
    background: str = ""
    audience: str = ""
    data: Any = None
    data_description: Dict[str, Any] = Field(default_factory=dict)
    pass_threshold: float = 0.60


class AgentPlan(BaseModel):
    agent_name: str
    goal: str
    steps: List[str] = Field(default_factory=list)
    expected_output: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    agent_name: str
    status: TaskStatus = TaskStatus.COMPLETED
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""
    error: Optional[str] = None


class SkillPlan(BaseModel):
    skill_name: str
    intent: str
    code: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    valid: bool
    issues: List[str] = Field(default_factory=list)


class SkillOutput(BaseModel):
    skill_name: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    files: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class ReviewResult(BaseModel):
    passed: bool
    score: float = 0.0
    feedback: str = ""
    suggestions: List[str] = Field(default_factory=list)


class ReportFragment(BaseModel):
    title: str
    content: str
    kind: str = "markdown"  # markdown, json, html


class ScoreDetails(BaseModel):
    metric: str
    score: float = Field(..., ge=0.0, le=1.0)
    dimensions: Dict[str, float] = Field(default_factory=dict)
    reasoning: str = ""
    suggestions: List[str] = Field(default_factory=list)


class JudgeScore(BaseModel):
    provider: str
    weight: float
    score: float
    reasoning: str = ""


class AggregatedScore(BaseModel):
    metric: str
    mean: float
    median: float
    weighted: float
    std: float
    consensus: str  # high / medium / low
    judge_scores: List[JudgeScore] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    overall_score: float
    grade: str
    passed: bool
    pass_threshold: float
    metrics: Dict[str, AggregatedScore] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowResult(BaseModel):
    input: AgentInput
    tasks: List[Task] = Field(default_factory=list)
    evaluation: Optional[EvaluationReport] = None
    final_report: str = ""
    output_dir: str = ""
