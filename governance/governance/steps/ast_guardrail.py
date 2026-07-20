"""Step 1 — AST Guardrail: structural analysis of Python source."""

from __future__ import annotations

import ast
from pathlib import Path

from governance.models import Finding, Severity, StepResult

STEP_ID = "ast_guardrail"
STEP_NAME = "AST Guardrail (Code Structure Analysis)"

FORBIDDEN_CALLS = {
    "eval": "eval() is forbidden — arbitrary code execution risk",
    "exec": "exec() is forbidden — arbitrary code execution risk",
    "compile": "compile() with dynamic source is forbidden",
    "__import__": "Dynamic __import__ is forbidden — use explicit imports",
}

MAX_NESTED_LOOPS = 2


class _StructureVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.findings: list[Finding] = []
        self._loop_depth = 0

    def visit_For(self, node: ast.For) -> None:
        self._enter_loop(node)
        self.generic_visit(node)
        self._exit_loop()

    def visit_While(self, node: ast.While) -> None:
        self._enter_loop(node)
        self.generic_visit(node)
        self._exit_loop()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._enter_loop(node)
        self.generic_visit(node)
        self._exit_loop()

    def _enter_loop(self, node: ast.AST) -> None:
        self._loop_depth += 1
        if self._loop_depth > MAX_NESTED_LOOPS:
            self.findings.append(
                Finding(
                    step=STEP_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"Nested loop depth {self._loop_depth} exceeds limit "
                        f"({MAX_NESTED_LOOPS}). Prefer a hashmap / set join "
                        f"to avoid O(N^{self._loop_depth}) scaling."
                    ),
                    file=self.file_path,
                    line=getattr(node, "lineno", None),
                    rule_id="AST001_NESTED_LOOPS",
                    suggestion="Replace nested scans with dict/set lookups (O(N)).",
                )
            )

    def _exit_loop(self) -> None:
        self._loop_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        # Only bare names (eval/exec/compile/__import__), not attrs like re.compile
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            name = node.func.id
            self.findings.append(
                Finding(
                    step=STEP_ID,
                    severity=Severity.CRITICAL,
                    message=FORBIDDEN_CALLS[name],
                    file=self.file_path,
                    line=node.lineno,
                    rule_id="AST002_FORBIDDEN_CALL",
                    evidence=name,
                    suggestion="Remove the call or replace with a safe alternative.",
                )
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function_complexity(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function_complexity(node)
        self.generic_visit(node)

    def _check_function_complexity(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        branches = sum(
            1
            for n in ast.walk(node)
            if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With))
        )
        if branches > 15:
            self.findings.append(
                Finding(
                    step=STEP_ID,
                    severity=Severity.WARNING,
                    message=(
                        f"Function `{node.name}` has high structural complexity "
                        f"(~{branches} branch points). Consider splitting."
                    ),
                    file=self.file_path,
                    line=node.lineno,
                    rule_id="AST003_COMPLEXITY",
                )
            )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return None


def analyze_file(path: Path) -> list[Finding]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [
            Finding(
                step=STEP_ID,
                severity=Severity.ERROR,
                message=f"SyntaxError: {exc.msg}",
                file=str(path),
                line=exc.lineno,
                rule_id="AST000_SYNTAX",
            )
        ]
    visitor = _StructureVisitor(str(path))
    visitor.visit(tree)
    return visitor.findings


def run(paths: list[Path]) -> StepResult:
    """Analyze Python files for structural anti-patterns."""
    py_files = [p for p in paths if p.suffix == ".py" and p.is_file()]
    findings: list[Finding] = []
    for path in py_files:
        findings.extend(analyze_file(path))

    blocking = [f for f in findings if f.severity in (Severity.ERROR, Severity.CRITICAL)]
    return StepResult(
        step=STEP_ID,
        name=STEP_NAME,
        passed=len(blocking) == 0,
        findings=findings,
        metrics={
            "files_scanned": len(py_files),
            "findings": len(findings),
            "blocking": len(blocking),
        },
    )
