"""CodeReviewAgent: QA for generated code and outputs."""
from __future__ import annotations

import json
from typing import Any, Dict

from ai_data_narrative.agents.base import Agent
from ai_data_narrative.llm.prompts import CODE_REVIEW_SYSTEM
from ai_data_narrative.models import AgentOutput, AgentPlan, ReviewResult


class CodeReviewAgent(Agent):
    name = "code_review"
    role = "quality assurance engineer"
    system_prompt = CODE_REVIEW_SYSTEM

    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        return AgentPlan(
            agent_name=self.name,
            goal="Review generated code for syntax, security, style",
            steps=["syntax check", "security scan", "style review"],
            expected_output={"passed": "boolean", "score": "number", "issues": "array"},
        )

    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        code = context.get("code", "")
        from ai_data_narrative.execution import check_syntax, scan_code

        syntax = check_syntax(code)
        security = scan_code(code)
        auto_issues = []
        if not syntax.valid:
            auto_issues.extend([f"Syntax: {e['message']} at line {e['line']}" for e in syntax.errors])
        for issue in security.issues:
            auto_issues.append(f"Security ({issue.severity}): {issue.message} at line {issue.line}")

        prompt = f"""Review the following Python code:
```python
{code}
```

Auto-detected issues:
{json.dumps(auto_issues, ensure_ascii=False, indent=2)}

Provide structured JSON review as described.
"""
        result = self._ask_json(prompt)
        issues = result.get("issues", [])
        passed = result.get("passed", len(issues) == 0 and len(auto_issues) == 0)
        score = result.get("score", 1.0 if passed else 0.5)

        return AgentOutput(
            agent_name=self.name,
            artifacts={
                "passed": passed,
                "score": score,
                "issues": issues + [{"message": m, "severity": "auto"} for m in auto_issues],
                "feedback": result.get("feedback", ""),
            },
            reasoning="Reviewed code with static checks + LLM.",
        )

    def review(self, output: AgentOutput) -> ReviewResult:
        passed = output.artifacts.get("passed", False)
        return ReviewResult(
            passed=passed,
            score=float(output.artifacts.get("score", 0.0)),
            feedback=output.artifacts.get("feedback", ""),
            suggestions=[i.get("message", str(i)) for i in output.artifacts.get("issues", [])],
        )
