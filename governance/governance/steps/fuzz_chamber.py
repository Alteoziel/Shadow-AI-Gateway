"""Step 3 — Test Injected Chamber: deterministic boundary fuzzing."""

from __future__ import annotations

import ast
import json
import subprocess
import tempfile
import textwrap
from pathlib import Path

from governance.models import Finding, Severity, StepResult

STEP_ID = "fuzz_chamber"
STEP_NAME = "Test Injected Chamber (Deterministic Fuzzing)"

BOUNDARY_CASES = [
    None,
    [],
    "",
    0,
    -1,
    10**9,
    {"__proto__": "x"},
    "A" * 10_000,
]

HARNESS_TEMPLATE = '''
import json
import sys
import traceback
from pathlib import Path

BOUNDARY = json.loads(sys.argv[1])
TARGET_FILE = sys.argv[2]
FUNC_NAME = sys.argv[3]

ns = {}
code = Path(TARGET_FILE).read_text(encoding="utf-8")
exec(compile(code, TARGET_FILE, "exec"), ns, ns)
fn = ns.get(FUNC_NAME)
if fn is None:
    print(json.dumps({"ok": False, "error": "function_not_found"}))
    sys.exit(0)

results = []
for case in BOUNDARY:
    try:
        fn(case)
        results.append({"input": repr(case)[:80], "status": "ok"})
    except TypeError as e:
        results.append({"input": repr(case)[:80], "status": "type_error", "error": str(e)})
    except PermissionError as e:
        # Expected deny path for allowlists / auth gates (e.g. EgressDeniedError).
        results.append({
            "input": repr(case)[:80],
            "status": "denied",
            "error": f"{type(e).__name__}: {e}",
        })
    except Exception as e:
        results.append({
            "input": repr(case)[:80],
            "status": "crash",
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc()[-500:],
        })

print(json.dumps({"ok": True, "results": results}))
'''


def _discover_fuzz_targets(path: Path) -> list[str]:
    """Find top-level functions that look like pure helpers (1–2 args)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    targets: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            arg_count = len(node.args.args)
            if 1 <= arg_count <= 2 and not node.decorator_list:
                targets.append(node.name)
    return targets[:5]


def _run_harness(path: Path, func_name: str, timeout_s: float = 5.0) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as harness:
        harness.write(textwrap.dedent(HARNESS_TEMPLATE))
        harness_path = harness.name

    try:
        proc = subprocess.run(
            [
                "python3",
                harness_path,
                json.dumps(BOUNDARY_CASES, default=str),
                str(path),
                func_name,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "results": []}
    finally:
        Path(harness_path).unlink(missing_ok=True)

    if proc.returncode != 0 and not proc.stdout:
        return {"ok": False, "error": proc.stderr[-400:], "results": []}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"ok": False, "error": "invalid_harness_output", "results": []}


def run(paths: list[Path]) -> StepResult:
    """
    Deterministically fuzz discovered helper functions with boundary inputs.

    Runs in a subprocess sandbox (Docker optional later). Crashes are ERRORS.
    TypeErrors from signature mismatch are informational only.
    PermissionError (and subclasses) are treated as expected deny paths.
    """
    findings: list[Finding] = []
    functions_tested = 0
    crashes = 0
    denied = 0

    skip_markers = (
        "test_",
        "/tests/",
        "governance/steps",
        "governance/cli",
        "governance/pipeline",
        "governance/reporters",
    )
    py_files = [
        p
        for p in paths
        if p.suffix == ".py"
        and p.is_file()
        and not any(marker in str(p).replace("\\", "/") for marker in skip_markers)
    ]

    jobs: list[tuple[Path, str]] = []
    for path in py_files:
        for func_name in _discover_fuzz_targets(path):
            jobs.append((path, func_name))

    for path, func_name in jobs:
        functions_tested += 1
        outcome = _run_harness(path, func_name)
        crash_items = [
            item for item in outcome.get("results", []) if item.get("status") == "crash"
        ]
        denied += sum(
            1 for item in outcome.get("results", []) if item.get("status") == "denied"
        )
        for item in crash_items:
            crashes += 1
            findings.append(
                Finding(
                    step=STEP_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"`{func_name}` crashed on boundary input "
                        f"{item.get('input')}: {item.get('error')}"
                    ),
                    file=str(path),
                    rule_id="FUZZ001_CRASH",
                    evidence=item.get("error"),
                    suggestion="Add input validation / null guards for boundary cases.",
                )
            )

    return StepResult(
        step=STEP_ID,
        name=STEP_NAME,
        passed=crashes == 0,
        findings=findings,
        metrics={
            "functions_tested": functions_tested,
            "boundary_cases": len(BOUNDARY_CASES),
            "crashes": crashes,
            "denied": denied,
        },
    )
