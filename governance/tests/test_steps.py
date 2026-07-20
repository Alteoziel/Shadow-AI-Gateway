"""Unit tests for governance engine steps."""

from __future__ import annotations

from pathlib import Path

from governance.steps import ast_guardrail, copyright_filter, security_auditor
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
    # Build payload at runtime so this test file itself does not trip the scanner
    key = "sk-live-" + ("a" * 24)
    src.write_text(f'API_KEY = "{key}"\n', encoding="utf-8")
    result = security_auditor.run([src], diff_text=None)
    assert not result.passed
    assert any(f.rule_id == "SEC001_HARDCODED_SECRET" for f in result.findings)


def test_big_o_estimator_linear() -> None:
    sizes = [10, 100, 1000, 10000]
    # Ideal linear times
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
