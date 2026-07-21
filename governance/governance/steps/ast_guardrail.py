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

SYNC_HTTP_RULE_ID = "AST004_SYNC_HTTP_CLIENT_IN_APP"
CHAT_INTERCEPTOR_ORDER_RULE_ID = "AST005_CHAT_INTERCEPTOR_ORDER"

HTTPX_SYNC_CALLS = {"Client", "get", "post", "put", "patch", "delete", "request", "stream"}
REQUESTS_SYNC_CALLS = {
    "Session",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    "request",
}


class _StructureVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.findings: list[Finding] = []
        self._loop_depth = 0
        self._is_app_file = _is_app_path(file_path)
        self._httpx_modules = {"httpx"}
        self._requests_modules = {"requests"}
        self._imported_httpx_sync_calls: set[str] = set()
        self._imported_requests_sync_calls: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            if alias.name == "httpx":
                self._httpx_modules.add(local_name)
            if alias.name == "requests":
                self._requests_modules.add(local_name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "httpx":
            for alias in node.names:
                if alias.name in HTTPX_SYNC_CALLS:
                    self._imported_httpx_sync_calls.add(alias.asname or alias.name)
        if node.module == "requests":
            for alias in node.names:
                if alias.name in REQUESTS_SYNC_CALLS:
                    self._imported_requests_sync_calls.add(alias.asname or alias.name)
        self.generic_visit(node)

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
        self._check_sync_http_usage(node)
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

    def _check_sync_http_usage(self, node: ast.Call) -> None:
        if not self._is_app_file:
            return

        evidence: str | None = None
        parts = _call_name_parts(node.func)
        if parts is not None:
            module_name, attr = parts
            if module_name in self._httpx_modules and attr in HTTPX_SYNC_CALLS:
                evidence = f"{module_name}.{attr}"
            if module_name in self._requests_modules and attr in REQUESTS_SYNC_CALLS:
                evidence = f"{module_name}.{attr}"

        bare_name = _bare_call_name(node.func)
        if bare_name in self._imported_httpx_sync_calls:
            evidence = bare_name
        if bare_name in self._imported_requests_sync_calls:
            evidence = bare_name

        if evidence is None:
            return

        self.findings.append(
            Finding(
                step=STEP_ID,
                severity=Severity.ERROR,
                message=(
                    "Synchronous HTTP clients are forbidden in app/ gateway code; "
                    "use async provider clients instead."
                ),
                file=self.file_path,
                line=node.lineno,
                rule_id=SYNC_HTTP_RULE_ID,
                evidence=evidence,
                suggestion="Use httpx.AsyncClient or the existing async provider interface.",
            )
        )


def _is_app_path(file_path: str) -> bool:
    return "app" in Path(file_path).parts


def _is_chat_route_path(file_path: str) -> bool:
    parts = Path(file_path).parts
    return len(parts) >= 4 and parts[-4:] == ("app", "api", "v1", "chat.py")


def _call_name_parts(node: ast.AST) -> tuple[str, str] | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr
    return None


def _bare_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return None


def _first_call_line(function: ast.AST, names: set[str], attrs: set[str]) -> int | None:
    lines: list[int] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in names:
            lines.append(node.lineno)
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in attrs:
            lines.append(node.lineno)
    return min(lines) if lines else None


def _check_chat_route_interceptor_order(tree: ast.AST, file_path: str) -> list[Finding]:
    if not _is_chat_route_path(file_path):
        return []

    route_fn = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "chat_completions"
        ),
        None,
    )
    if route_fn is None:
        return []

    interceptor_line = _first_call_line(route_fn, {"intercept_outbound_request"}, set())
    provider_line = _first_call_line(
        route_fn,
        {"_resolve_provider", "_get_provider_adapter"},
        {"chat_completion", "chat_completion_stream"},
    )

    if interceptor_line is None:
        return [
            Finding(
                step=STEP_ID,
                severity=Severity.ERROR,
                message=(
                    "chat_completions must call intercept_outbound_request before "
                    "provider resolution or provider calls."
                ),
                file=file_path,
                line=getattr(route_fn, "lineno", None),
                rule_id=CHAT_INTERCEPTOR_ORDER_RULE_ID,
                suggestion="Call intercept_outbound_request before resolving or invoking providers.",
            )
        ]
    if provider_line is not None and provider_line < interceptor_line:
        return [
            Finding(
                step=STEP_ID,
                severity=Severity.ERROR,
                message=(
                    "chat_completions resolves or invokes a provider before "
                    "intercept_outbound_request."
                ),
                file=file_path,
                line=provider_line,
                rule_id=CHAT_INTERCEPTOR_ORDER_RULE_ID,
                suggestion="Move intercept_outbound_request before provider resolution.",
            )
        ]
    return []


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
    return visitor.findings + _check_chat_route_interceptor_order(tree, str(path))


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
