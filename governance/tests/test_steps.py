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


def _write_app_file(tmp_path: Path, relative: str, source: str) -> Path:
    path = tmp_path / "app" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


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


def test_ast_flags_requests_sync_usage_in_app(tmp_path: Path) -> None:
    src = _write_app_file(
        tmp_path,
        "bad_requests.py",
        "import requests\n\n"
        "def call(url):\n"
        "    return requests.get(url)\n",
    )
    result = ast_guardrail.run([src])
    assert not result.passed
    assert any(
        f.rule_id == "AST004_SYNC_HTTP_CLIENT_IN_APP" for f in result.findings
    )


def test_ast_flags_httpx_sync_client_in_app(tmp_path: Path) -> None:
    src = _write_app_file(
        tmp_path,
        "bad_httpx.py",
        "from httpx import Client\n\n"
        "def call(url):\n"
        "    with Client() as client:\n"
        "        return client.get(url)\n",
    )
    result = ast_guardrail.run([src])
    assert not result.passed
    assert any(
        f.rule_id == "AST004_SYNC_HTTP_CLIENT_IN_APP" for f in result.findings
    )


def test_ast_allows_httpx_async_client_in_app(tmp_path: Path) -> None:
    src = _write_app_file(
        tmp_path,
        "ok_async_httpx.py",
        "import httpx\n\n"
        "async def call(url):\n"
        "    async with httpx.AsyncClient() as client:\n"
        "        return await client.get(url)\n",
    )
    result = ast_guardrail.run([src])
    assert result.passed
    assert not any(
        f.rule_id == "AST004_SYNC_HTTP_CLIENT_IN_APP" for f in result.findings
    )


def test_ast_sync_http_rule_is_app_scoped(tmp_path: Path) -> None:
    src = tmp_path / "governance_client.py"
    src.write_text(
        "import httpx\n\n"
        "def call(url):\n"
        "    with httpx.Client() as client:\n"
        "        return client.get(url)\n",
        encoding="utf-8",
    )
    result = ast_guardrail.run([src])
    assert result.passed
    assert not any(
        f.rule_id == "AST004_SYNC_HTTP_CLIENT_IN_APP" for f in result.findings
    )


def test_ast_flags_chat_route_provider_before_interceptor(tmp_path: Path) -> None:
    src = _write_app_file(
        tmp_path,
        "api/v1/chat.py",
        "async def intercept_outbound_request(**kwargs):\n"
        "    return kwargs\n\n"
        "def _resolve_provider(request):\n"
        "    return 'openai'\n\n"
        "async def chat_completions(request_body, request):\n"
        "    provider_name = _resolve_provider(request_body)\n"
        "    normalized = await intercept_outbound_request(body={})\n"
        "    return provider_name, normalized\n",
    )
    result = ast_guardrail.run([src])
    assert not result.passed
    assert any(
        f.rule_id == "AST005_CHAT_INTERCEPTOR_ORDER" for f in result.findings
    )


def test_ast_current_chat_route_calls_interceptor_before_provider() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "app" / "api" / "v1" / "chat.py"
    result = ast_guardrail.run([src])
    assert result.passed
    assert not any(
        f.rule_id == "AST005_CHAT_INTERCEPTOR_ORDER" for f in result.findings
    )


def test_security_hardcoded_secret(tmp_path: Path) -> None:
    src = tmp_path / "secrets.py"
    key = "sk-live-" + ("a" * 24)
    src.write_text(f'API_KEY = "{key}"\n', encoding="utf-8")
    result = security_auditor.run([src], diff_text=None)
    assert not result.passed
    assert any(f.rule_id == "SEC001_HARDCODED_SECRET" for f in result.findings)


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
