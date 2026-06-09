"""Static security scanner for generated Python code."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import List

from ai_data_narrative.config import FORBIDDEN_BUILTINS, FORBIDDEN_IMPORTS


@dataclass
class SecurityIssue:
    severity: str
    category: str
    message: str
    line: int


class SecurityScanResult:
    def __init__(self, safe: bool, issues: List[SecurityIssue]):
        self.safe = safe
        self.issues = issues


class SecurityScanner(ast.NodeVisitor):
    """Scan AST for forbidden imports and calls."""

    def __init__(self):
        self.issues: List[SecurityIssue] = []

    def scan(self, code: str) -> SecurityScanResult:
        self.issues = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return SecurityScanResult(safe=False, issues=[])
        self.visit(tree)
        return SecurityScanResult(safe=len(self.issues) == 0, issues=self.issues)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_import(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        self._check_import(module, node.lineno)
        for alias in node.names:
            self._check_import(f"{module}.{alias.name}", node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_BUILTINS:
                self.issues.append(
                    SecurityIssue(
                        severity="critical",
                        category="forbidden_call",
                        message=f"Forbidden builtin call: {node.func.id}",
                        line=node.lineno,
                    )
                )
        elif isinstance(node.func, ast.Attribute):
            attr_chain = self._attr_chain(node.func)
            if attr_chain and any(attr_chain.startswith(forbidden) for forbidden in FORBIDDEN_IMPORTS if "." in forbidden):
                self.issues.append(
                    SecurityIssue(
                        severity="critical",
                        category="forbidden_call",
                        message=f"Forbidden call: {attr_chain}",
                        line=node.lineno,
                    )
                )
        self.generic_visit(node)

    def _attr_chain(self, node: ast.Attribute) -> str:
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        else:
            return ""
        return ".".join(reversed(parts))

    def _check_import(self, name: str, lineno: int) -> None:
        for forbidden in FORBIDDEN_IMPORTS:
            if forbidden in name:
                self.issues.append(
                    SecurityIssue(
                        severity="critical",
                        category="forbidden_import",
                        message=f"Forbidden import: {name}",
                        line=lineno,
                    )
                )
                break


def scan_code(code: str) -> SecurityScanResult:
    return SecurityScanner().scan(code)
