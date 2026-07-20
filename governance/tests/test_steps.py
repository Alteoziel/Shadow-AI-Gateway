"""Unit tests for governance engine steps."""

from __future__ import annotations

from pathlib import Path

from governance.steps import (
    ast_guardrail,
    comprehension_gate,
    copyright_filter,
    security_auditor,
)
from governance.steps.benchmark_engine import estimate_big_o


def test_ast_flags_nested_loops(tmp_path: Path) -> None:
    src = tmp_path / "bad.py"
    src.write_text(
        "def f(a, b, c):\n"
        "    for x in a:\n"
        "        for y in b:\n"
        "            for z in c:\n"
        "                print(x, y, z)\n",
        encoding="utf-8",
    )
    result = ast_guardrail.run([src])
    assert not result.passed
    assert any(f.rule_id == "AST001_NESTED_LOOPS" for f in result.findings)


def test_ast_flags_eval(tmp_path: Path) -> None:
    src = tmp_path / "evil.py"
    src.write_text("def run(x):\n    return eval(x)\n", encoding="utf-8")
    result = ast_guardrail.run([src])
    assert not result.passed
    assert any(f.rule_id == "AST002_FORBIDDEN_CALL" for f in result.findings)


def test_ast_clean_file(tmp_path: Path) -> None:
    src = tmp_path / "ok.py"
    src.write_text(
        "def lookup(items, key):\n"
        "    index = {x: i for i, x in enumerate(items)}\n"
        "    return index.get(key)\n",
        encoding="utf-8",
    )
    result = ast_guardrail.run([src])
    assert result.passed


def test_security_hardcoded_secret(tmp_path: Path) -> None:
    src = tmp_path / "secrets.py"
    key = "sk-live-" + ("a" * 24)
    src.write_text(f'API_KEY = "{key}"\n', encoding="utf-8")
    result = security_auditor.run([src], diff_text=None)
    assert not result.passed
    assert any(f.rule_id == "SEC001_HARDCODED_SECRET" for f in result.findings)


def test_security_ignores_semgrep_rule_yaml(tmp_path: Path) -> None:
    """Rule definitions mention forbidden APIs — must not block the suite."""
    rules = tmp_path / ".semgrep.yml"
    # Split literals so the auditor does not flag this test file itself.
    forbidden_shell = "os." + "system(...)"
    forbidden_pickle = "pick" + "le.loads"
    rules.write_text(
        "rules:\n"
        "  - id: demo\n"
        f"    pattern: {forbidden_shell}\n"
        f"    message: forbid {forbidden_pickle}\n",
        encoding="utf-8",
    )
    result = security_auditor.run([rules], diff_text=None)
    assert result.passed
    assert result.findings == []


def test_security_ssrf_requires_call_not_type_hint(tmp_path: Path) -> None:
    src = tmp_path / "types.py"
    src.write_text(
        "import httpx\n"
        "def handle(request: httpx.Request) -> None:\n"
        "    return None\n",
        encoding="utf-8",
    )
    result = security_auditor.run([src], diff_text=None)
    assert result.passed
    assert not any(f.rule_id == "SEC005_SSRF" for f in result.findings)


def test_big_o_estimator_linear() -> None:
    sizes = [10, 100, 1000, 10000]
    times = [s * 1e-6 for s in sizes]
    label, slope = estimate_big_o(sizes, times)
    assert label == "O(N)"
    assert 0.8 < slope < 1.2


def test_copyright_exact_match(tmp_path: Path) -> None:
    src = tmp_path / "plagiarized.py"
    src.write_text(
        "def twoSum(nums, target):\n"
        "    for i in range(len(nums)):\n"
        "        for j in range(i + 1, len(nums)):\n"
        "            if nums[i] + nums[j] == target:\n"
        "                return [i, j]\n"
        "    return []\n",
        encoding="utf-8",
    )
    result = copyright_filter.run([src])
    assert not result.passed
    assert any(f.rule_id in {"COPY001_EXACT", "COPY002_SIMILAR"} for f in result.findings)


def test_comprehension_generates_quiz(tmp_path: Path) -> None:
    src = tmp_path / "proxy_bit.py"
    src.write_text(
        '"""tiny helper"""\n'
        "async def intercept_outbound_request(body):\n"
        '    """Pre-flight normalize."""\n'
        "    return body\n",
        encoding="utf-8",
    )
    result = comprehension_gate.run(
        [src], diff_text="diff --git a/x", root=tmp_path, skip_llm=True
    )
    assert result.passed
    pack = result.metrics["comprehension"]
    assert pack["pass_threshold"] == 0.8
    assert len(pack["questions"]) >= 5
    assert pack["study_guide"]["glossary"]
    assert pack["study_guide"]["manual_dev_tasks"]


def test_comprehension_grade_pass_fail() -> None:
    pack = {
        "pass_threshold": 0.8,
        "questions": [
            {
                "id": "a",
                "category": "vocabulary",
                "prompt": "?",
                "choices": ["0", "1", "2", "3"],
                "answer_index": 1,
                "explanation": "because",
            },
            {
                "id": "b",
                "category": "security",
                "prompt": "?",
                "choices": ["0", "1", "2", "3"],
                "answer_index": 0,
                "explanation": "because",
            },
            {
                "id": "c",
                "category": "how_it_works",
                "prompt": "?",
                "choices": ["0", "1", "2", "3"],
                "answer_index": 2,
                "explanation": "because",
            },
            {
                "id": "d",
                "category": "bigger_picture",
                "prompt": "?",
                "choices": ["0", "1", "2", "3"],
                "answer_index": 3,
                "explanation": "because",
            },
            {
                "id": "e",
                "category": "dependencies",
                "prompt": "?",
                "choices": ["0", "1", "2", "3"],
                "answer_index": 1,
                "explanation": "because",
            },
        ],
    }
    perfect = comprehension_gate.grade(
        pack, {"a": 1, "b": 0, "c": 2, "d": 3, "e": 1}
    )
    assert perfect["passed"] is True
    assert perfect["score"] == 1.0

    weak = comprehension_gate.grade(pack, {"a": 0, "b": 0, "c": 0, "d": 0, "e": 0})
    assert weak["passed"] is False
    assert weak["correct"] == 1
