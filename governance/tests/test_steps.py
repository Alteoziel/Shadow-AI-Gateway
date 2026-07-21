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


def test_copyright_exact_match_fastapi_httpx_antipattern(tmp_path: Path) -> None:
    signatures = copyright_filter.load_signatures()
    snippet = next(
        sig["content"]
        for sig in signatures
        if sig["id"] == "fastapi_sync_httpx_in_async_route"
    )
    src = tmp_path / "blocked_gateway_clone.py"
    src.write_text(snippet, encoding="utf-8")

    result = copyright_filter.run([src])

    assert result.metrics["signatures"] >= 7
    assert not result.passed
    assert any(
        f.rule_id in {"COPY001_EXACT", "COPY002_SIMILAR"}
        and "fastapi_sync_httpx_in_async_route" in f.message
        for f in result.findings
    )


def test_comprehension_generates_quiz(tmp_path: Path) -> None:
    src = tmp_path / "proxy_bit.py"
    src.write_text(
        '"""tiny helper"""\n'
        "async def intercept_outbound_request(body):\n"
        '    """Pre-flight normalize."""\n'
        "    return body\n"
        "\n"
        "def score_prompt(text: str) -> int:\n"
        "    return len(text)\n",
        encoding="utf-8",
    )
    diff = (
        "diff --git a/proxy_bit.py b/proxy_bit.py\n"
        "--- a/proxy_bit.py\n"
        "+++ b/proxy_bit.py\n"
        "@@ -0,0 +1,8 @@\n"
        '+"""tiny helper"""\n'
        "+async def intercept_outbound_request(body):\n"
        '+\t"""Pre-flight normalize."""\n'
        "+    return body\n"
        "+\n"
        "+def score_prompt(text: str) -> int:\n"
        "+    return len(text)\n"
    )
    result = comprehension_gate.run(
        [src], diff_text=diff, root=tmp_path, skip_llm=True
    )
    assert result.passed
    pack = result.metrics["comprehension"]
    assert pack["pass_threshold"] == 0.8
    coding = [q for q in pack["questions"] if q.get("question_type") == "coding"]
    assert len(coding) >= 2
    for q in coding:
        assert q["entrypoint"]
        assert q["starter_code"]
        assert q["tests"]
        assert q["language"] == "javascript"
    assert pack["study_guide"]["glossary"]
    assert pack["study_guide"]["manual_dev_tasks"]
    assert pack["study_guide"]["what_changed"]["summary"]
    assert "score_prompt" in pack["study_guide"]["what_changed"]["added_symbols"] or (
        "intercept_outbound_request" in pack["study_guide"]["what_changed"]["added_symbols"]
    )
    # Static template IDs from the old bank must not reappear
    banned = {
        "vocab_preflight",
        "vocab_gateway",
        "pic_phases",
        "pic_why_quiz",
        "how_flow",
        "dep_meaning",
        "sec_why_gate",
        "sec_keys",
        "manual_checkpoint",
        "phase1_provider_selection",
        "phase1_provider_flow",
        "phase1_streaming_flow",
        "phase1_checkpoint_501",
    }
    ids = {q["id"] for q in pack["questions"]}
    assert ids.isdisjoint(banned)
    mc = [q for q in pack["questions"] if q.get("question_type") != "coding"]
    assert len(mc) >= 5
    cats = {q["category"] for q in mc}
    assert "what_changed" in cats
    # Prompts should mention this PR's symbols/files, not only generic project lore
    blob = " ".join(q["prompt"] for q in mc).lower()
    assert "intercept_outbound_request" in blob or "proxy_bit" in blob or "score_prompt" in blob
    # Distractors should not be joke options
    all_choices = " ".join(
        c for q in mc for c in (q.get("choices") or [])
    ).lower()
    assert "plane ticket" not in all_choices
    assert "moon is full" not in all_choices


def test_comprehension_quiz_varies_by_pr_files(tmp_path: Path) -> None:
    proxy = tmp_path / "app" / "proxy"
    proxy.mkdir(parents=True)
    dash = tmp_path / "dashboard" / "src" / "lib"
    dash.mkdir(parents=True)

    interceptor = proxy / "interceptor.py"
    interceptor.write_text(
        "async def intercept_outbound_request(body):\n"
        '    """Validate before provider call."""\n'
        "    return body\n",
        encoding="utf-8",
    )
    store = dash / "store.ts"
    store.write_text(
        "import { Redis } from '@upstash/redis';\n"
        "export function gradeComprehension(pack, answers) {\n"
        "  return { passed: true };\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "dashboard" / "package.json").write_text(
        '{"dependencies":{"next":"15.0.0","@upstash/redis":"1.0.0","react":"19.0.0"}}',
        encoding="utf-8",
    )

    pack_a = comprehension_gate.run(
        [interceptor],
        diff_text=(
            "diff --git a/app/proxy/interceptor.py b/app/proxy/interceptor.py\n"
            "--- a/app/proxy/interceptor.py\n"
            "+++ b/app/proxy/interceptor.py\n"
            "@@ -0,0 +1,3 @@\n"
            "+async def intercept_outbound_request(body):\n"
            '+\t"""Validate before provider call."""\n'
            "+    return body\n"
        ),
        root=tmp_path,
        skip_llm=True,
    ).metrics["comprehension"]
    pack_b = comprehension_gate.run(
        [store],
        diff_text=(
            "diff --git a/dashboard/src/lib/store.ts b/dashboard/src/lib/store.ts\n"
            "--- a/dashboard/src/lib/store.ts\n"
            "+++ b/dashboard/src/lib/store.ts\n"
            "@@ -0,0 +1,4 @@\n"
            "+import { Redis } from '@upstash/redis';\n"
            "+export function gradeComprehension(pack, answers) {\n"
            "+  return { passed: true };\n"
            "+}\n"
        ),
        root=tmp_path,
        skip_llm=True,
    ).metrics["comprehension"]

    ids_a = [q["id"] for q in pack_a["questions"] if q.get("question_type") != "coding"]
    ids_b = [q["id"] for q in pack_b["questions"] if q.get("question_type") != "coding"]
    assert ids_a != ids_b

    gloss_a = {g["term"] for g in pack_a["study_guide"]["glossary"]}
    gloss_b = {g["term"] for g in pack_b["study_guide"]["glossary"]}
    assert gloss_a != gloss_b

    assert "proxy" in " ".join(pack_a["study_guide"]["areas"])
    assert "dashboard" in " ".join(pack_b["study_guide"]["areas"])
    assert "intercept_outbound_request" in {
        f["name"] for f in pack_a["study_guide"]["key_functions"]
    }
    assert "gradeComprehension" in {
        f["name"] for f in pack_b["study_guide"]["key_functions"]
    }
    assert pack_a["study_guide"]["what_changed"]["top_file"].endswith("interceptor.py")
    assert pack_b["study_guide"]["what_changed"]["top_file"].endswith("store.ts")

    coding_a = {
        q["id"] for q in pack_a["questions"] if q.get("question_type") == "coding"
    }
    coding_b = {
        q["id"] for q in pack_b["questions"] if q.get("question_type") == "coding"
    }
    assert coding_a != coding_b
    # Proxy PR should get preflight logic; dashboard PR should not get that toy-bank filler
    assert "code_ch_preflight_body" in coding_a
    assert "code_ch_preflight_body" not in coding_b
    # Old always-on toys must not appear on every PR
    assert "code_ch_max_nest" not in coding_a | coding_b
    assert "code_ch_normalize_messages" not in coding_a | coding_b
    # Challenges must embed THIS PR's facts in the prompt (not a generic joke bank)
    proxy_prompts = " ".join(
        q["prompt"]
        for q in pack_a["questions"]
        if q.get("question_type") == "coding"
    )
    assert "intercept_outbound_request" in proxy_prompts or "interceptor.py" in proxy_prompts
    dash_prompts = " ".join(
        q["prompt"]
        for q in pack_b["questions"]
        if q.get("question_type") == "coding"
    )
    assert "gradeComprehension" in dash_prompts or "store.ts" in dash_prompts


def test_parse_diff_facts_extracts_symbols() -> None:
    diff = (
        "diff --git a/app/proxy/foo.py b/app/proxy/foo.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/app/proxy/foo.py\n"
        "@@ -0,0 +1,5 @@\n"
        "+def brand_new_helper(x):\n"
        "+    return x\n"
        "+async def another_one():\n"
        "+    return 1\n"
    )
    facts = comprehension_gate._parse_diff_facts(diff)
    assert facts["top_file"] == "app/proxy/foo.py"
    assert "brand_new_helper" in facts["added_symbols"]
    assert "another_one" in facts["added_symbols"]
    assert facts["total_added"] >= 4
    assert "brand_new_helper" in facts["summary"] or "another_one" in facts["summary"]


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
