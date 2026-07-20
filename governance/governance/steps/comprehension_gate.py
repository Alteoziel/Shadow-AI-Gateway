"""Step 6 — Comprehension Gate: beginner study guide + understanding quiz.

Sits after automated analysis (Steps 1–5) and before the human review/merge
panel (Step 7). Goal: you must understand what shipped — vocabulary, how it
works, bigger picture, dependencies, manual tasks, functions, security —
before approving a merge. Shipping code you cannot explain is the danger.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any

import httpx

from governance.models import Finding, Severity, StepResult

STEP_ID = "comprehension_gate"
STEP_NAME = "Comprehension Gate (Dev Understanding Check)"

PASS_THRESHOLD = 0.8  # 80% correct required on the dashboard quiz

# Project-level vocabulary a brand-new engineer should internalize
PROJECT_GLOSSARY: list[dict[str, str]] = [
    {
        "term": "pre-flight",
        "definition": (
            "Inspecting/normalizing an outbound LLM request BEFORE any bytes "
            "leave your network toward OpenAI/Anthropic. This is the choke point."
        ),
    },
    {
        "term": "proxy / gateway",
        "definition": (
            "A service that sits between the user and the public AI API. "
            "Clients talk to YOUR gateway; the gateway talks to the AI provider."
        ),
    },
    {
        "term": "FastAPI",
        "definition": (
            "A Python web framework for building HTTP APIs. Routes like "
            "POST /v1/chat/completions are defined here."
        ),
    },
    {
        "term": "async / await",
        "definition": (
            "Python concurrency style that lets the server handle many requests "
            "while waiting on network I/O (e.g. calling OpenAI) without blocking."
        ),
    },
    {
        "term": "environment variable",
        "definition": (
            "A secret or config value injected at runtime (e.g. OPENAI_API_KEY). "
            "Never commit real keys into git."
        ),
    },
    {
        "term": "PII",
        "definition": (
            "Personally Identifiable Information — names, emails, card numbers, "
            "etc. Phase 2 of this project redacts PII before prompts leave."
        ),
    },
    {
        "term": "provider adapter",
        "definition": (
            "Code that translates our internal request shape into OpenAI's or "
            "Anthropic's specific API format."
        ),
    },
    {
        "term": "AST",
        "definition": (
            "Abstract Syntax Tree — a structured tree of your code (functions, "
            "loops, calls) used by Step 1 to catch bad structure without running it."
        ),
    },
]

CATEGORY_LABELS = {
    "vocabulary": "Vocabulary & definitions",
    "how_it_works": "How this change works",
    "bigger_picture": "Bigger picture / architecture",
    "dependencies": "Dependencies & what it touches",
    "manual_tasks": "Manual things you must do",
    "functions": "Functions & call flow",
    "security": "Security implications",
}


def _rel(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _extract_python_symbols(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "imports": [],
        "functions": [],
        "async_functions": [],
        "classes": [],
    }
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return info

    for node in tree.body:
        if isinstance(node, ast.Import):
            info["imports"].extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            info["imports"].append(node.module.split(".")[0])
        elif isinstance(node, ast.FunctionDef):
            info["functions"].append(
                {
                    "name": node.name,
                    "args": [a.arg for a in node.args.args],
                    "lineno": node.lineno,
                    "doc": ast.get_docstring(node) or "",
                }
            )
        elif isinstance(node, ast.AsyncFunctionDef):
            info["async_functions"].append(
                {
                    "name": node.name,
                    "args": [a.arg for a in node.args.args],
                    "lineno": node.lineno,
                    "doc": ast.get_docstring(node) or "",
                }
            )
        elif isinstance(node, ast.ClassDef):
            info["classes"].append(node.name)
    info["imports"] = sorted(set(info["imports"]))
    return info


def _detect_manual_tasks(paths: list[Path], symbols: dict[str, dict]) -> list[str]:
    tasks: list[str] = []
    joined = " ".join(str(p) for p in paths).lower()

    if "interceptor.py" in joined:
        tasks.append(
            "Human Checkpoint #1: implement `intercept_outbound_request` in "
            "`app/proxy/interceptor.py` (it currently raises NotImplementedError / 501)."
        )
    if any(".env" in str(p) or "config.py" in str(p) for p in paths):
        tasks.append(
            "Copy `.env.example` → `.env` and fill real API keys locally "
            "(never commit `.env`)."
        )
    if "dockerfile" in joined or "fly.toml" in joined or "render.yaml" in joined:
        tasks.append(
            "If deploying: set secrets in the host dashboard (Fly/Render), not in git."
        )
    if "governance" in joined:
        tasks.append(
            "After changing governance rules: run `cd governance && pytest` and "
            "`ai-guardrail run --root ..` before opening a PR."
        )
    if "dashboard" in joined:
        tasks.append(
            "Dashboard: `cd dashboard && npm install && npm run dev`. "
            "Set GOVERNANCE_DASHBOARD_SECRET (+ GITHUB_TOKEN for merge)."
        )

    # NotImplemented / TODO markers
    for path, meta in symbols.items():
        for fn in meta.get("functions", []) + meta.get("async_functions", []):
            if "notimplemented" in (fn.get("doc") or "").lower():
                tasks.append(
                    f"Finish incomplete function `{fn['name']}` in `{path}` "
                    "(docstring mentions NotImplemented)."
                )

    for path in paths:
        if not path.is_file() or path.suffix != ".py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "TODO: Human Hands-On Implementation" in text:
            tasks.append(
                f"There is a human hands-on TODO in `{path.name}` — agents must not "
                "silently complete it; you implement it."
            )
        if "NotImplementedError" in text:
            tasks.append(
                f"`{path.name}` still raises NotImplementedError — the feature is "
                "scaffolded but not finished."
            )

    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in tasks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    if not out:
        out.append(
            "No extra manual checklist detected for this diff — still read the "
            "study guide and pass the quiz before merging."
        )
    return out


def _build_deterministic_pack(
    paths: list[Path],
    *,
    root: Path | None = None,
    diff_text: str | None = None,
) -> dict[str, Any]:
    py_files = [p for p in paths if p.is_file() and p.suffix == ".py"]
    symbols: dict[str, dict] = {}
    all_imports: set[str] = set()
    all_fns: list[tuple[str, dict]] = []

    for path in py_files[:40]:
        rel = _rel(path, root)
        meta = _extract_python_symbols(path)
        symbols[rel] = meta
        all_imports.update(meta["imports"])
        for fn in meta["functions"] + meta["async_functions"]:
            all_fns.append((rel, fn))

    changed_names = [_rel(p, root) for p in paths if p.is_file()][:25]
    manual = _detect_manual_tasks(paths, symbols)

    key_functions = []
    for rel, fn in all_fns[:12]:
        kind = "async function" if fn in symbols.get(rel, {}).get("async_functions", []) else "function"
        # fix kind detection
        async_names = {f["name"] for f in symbols.get(rel, {}).get("async_functions", [])}
        kind = "async function" if fn["name"] in async_names else "function"
        plain = fn.get("doc") or (
            f"A {kind} named `{fn['name']}` in `{rel}`. "
            f"Arguments: {', '.join(fn['args']) or 'none'}."
        )
        key_functions.append(
            {
                "name": fn["name"],
                "file": rel,
                "plain_english": plain[:400],
            }
        )

    # Relevant glossary subset + always core terms
    core_terms = {"pre-flight", "proxy / gateway", "environment variable", "FastAPI"}
    glossary = [g for g in PROJECT_GLOSSARY if g["term"] in core_terms]
    # Add more if imports suggest them
    if "httpx" in all_imports or "fastapi" in all_imports:
        glossary = PROJECT_GLOSSARY[:6]
    else:
        glossary = PROJECT_GLOSSARY[:5]

    elevator = (
        "This change touches the Shadow AI Guardrail Gateway — an enterprise proxy "
        "that sits between users and public LLMs so sensitive data can be inspected "
        "pre-flight. "
    )
    if changed_names:
        elevator += "Files in this change include: " + ", ".join(changed_names[:8]) + "."
    else:
        elevator += "Review the study guide to understand what is being proposed."

    bigger = (
        "Bigger picture: Phase 1 builds the async FastAPI proxy; Phase 2 adds PII "
        "scrubbing; Phase 3 adds Postgres audit logs; Phase 4 packages with Docker/"
        "Terraform. The governance suite (this quiz included) gates merges so you "
        "never ship AI-written code you cannot explain."
    )

    deps = sorted(all_imports) or ["(no Python imports detected in scanned files)"]
    security_notes = [
        "Never commit real API keys — use environment variables.",
        "The interceptor is the security choke point: bad validation here means "
        "prompts can leave the network unchecked later.",
        "Passing Bugbot/Vercel alone is not enough — AST/OWASP/fuzz/copyright + "
        "this comprehension quiz must clear before merge.",
    ]
    if any("secret" in n.lower() or "key" in n.lower() for n in changed_names):
        security_notes.insert(
            0,
            "This diff touches secret/key-related files — double-check nothing "
            "sensitive is hardcoded.",
        )

    study_guide = {
        "elevator_pitch": elevator,
        "bigger_picture": bigger,
        "glossary": glossary,
        "key_functions": key_functions,
        "dependencies": deps,
        "manual_dev_tasks": manual,
        "security_notes": security_notes,
        "files_touched": changed_names,
        "diff_chars": len(diff_text or ""),
    }

    questions = _make_questions(study_guide, all_fns, all_imports)
    return {
        "learner_level": "absolute_beginner",
        "pass_threshold": PASS_THRESHOLD,
        "generator": "deterministic",
        "study_guide": study_guide,
        "questions": questions,
    }


def _q(
    qid: str,
    category: str,
    prompt: str,
    choices: list[str],
    answer_index: int,
    explanation: str,
) -> dict[str, Any]:
    return {
        "id": qid,
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "prompt": prompt,
        "choices": choices,
        "answer_index": answer_index,
        "explanation": explanation,
    }


def _make_questions(
    guide: dict[str, Any],
    all_fns: list[tuple[str, dict]],
    imports: set[str],
) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []

    # Vocabulary
    questions.append(
        _q(
            "vocab_preflight",
            "vocabulary",
            "What does **pre-flight** mean in this project?",
            [
                "Running unit tests after deploying to production",
                "Inspecting/normalizing an LLM request BEFORE it leaves your network",
                "Formatting Python code with Black",
                "Buying a plane ticket for an on-call engineer",
            ],
            1,
            "Pre-flight is the choke point: validate/scrub before any upstream provider call.",
        )
    )
    questions.append(
        _q(
            "vocab_gateway",
            "vocabulary",
            "What is the Shadow AI **gateway**?",
            [
                "A React weather app",
                "A CDN that caches images",
                "A proxy between users and public LLM APIs that can inspect outbound prompts",
                "A database of LeetCode solutions",
            ],
            2,
            "It is an enterprise security proxy for outbound LLM traffic.",
        )
    )

    # Bigger picture
    questions.append(
        _q(
            "pic_phases",
            "bigger_picture",
            "Which statement matches the 12-month plan?",
            [
                "Skip scrubbing and go straight to Terraform on day one",
                "Phase 1 proxy → Phase 2 scrubbing → Phase 3 Postgres audit → Phase 4 Docker/Terraform",
                "Only build a Next.js marketing site",
                "Host the streaming proxy on Vercel serverless",
            ],
            1,
            "Crawl → Walk → Run → Cloud. Vercel is forbidden for the streaming proxy.",
        )
    )
    questions.append(
        _q(
            "pic_why_quiz",
            "bigger_picture",
            "Why does this comprehension quiz exist before merge?",
            [
                "GitHub requires emojis on every PR",
                "So you can rubber-stamp AI code without reading it",
                "Because merging code you cannot explain is dangerous — you must understand it first",
                "To replace writing tests forever",
            ],
            2,
            "You are learning; AI wrote a lot of this. Understanding is the resume-defense gate.",
        )
    )

    # How it works / functions
    if all_fns:
        rel, fn = all_fns[0]
        questions.append(
            _q(
                "fn_primary",
                "functions",
                f"In this change, what is `{fn['name']}` (in `{rel}`)?",
                [
                    f"A {('async ' if fn['name'] in {x['name'] for _, x in all_fns} else '')}function defined in this codebase that you should be able to explain",
                    "A built-in Python keyword like `if`",
                    "An AWS region name",
                    "A CSS class in the dashboard",
                ],
                0,
                f"`{fn['name']}` is application code in `{rel}`. Args: {', '.join(fn['args']) or 'none'}.",
            )
        )
    else:
        questions.append(
            _q(
                "fn_interceptor",
                "functions",
                "Where should outbound LLM requests be validated pre-flight?",
                [
                    "In a random CSS file",
                    "Inside `app/proxy/interceptor.py` via `intercept_outbound_request`",
                    "Only on the user's phone",
                    "After the response returns from OpenAI",
                ],
                1,
                "Checkpoint #1 is the interceptor — before any provider adapter runs.",
            )
        )

    questions.append(
        _q(
            "how_flow",
            "how_it_works",
            "Roughly, what is the happy-path request flow for the gateway?",
            [
                "Browser → OpenAI directly (gateway unused)",
                "Client → Gateway route → interceptor → provider adapter → upstream LLM → stream back",
                "Client → Postgres → Terraform → done",
                "Client → Bugbot → Vercel → merge",
            ],
            1,
            "The gateway owns the path; providers are adapters behind the interceptor.",
        )
    )

    # Dependencies
    dep_choice_correct = (
        "Libraries/modules this code imports or relies on (e.g. FastAPI, httpx) "
        "plus sibling project files it calls"
    )
    questions.append(
        _q(
            "dep_meaning",
            "dependencies",
            "When we say **dependencies** for a change, what should you check?",
            [
                "Only the color of the README badge",
                dep_choice_correct,
                "Whether the moon is full",
                "Only the number of emojis in the commit message",
            ],
            1,
            f"Detected imports in this scan: {', '.join(sorted(imports)[:12]) or 'none yet'}.",
        )
    )

    # Manual tasks
    tasks = guide.get("manual_dev_tasks") or []
    has_checkpoint = any("Checkpoint" in t or "NotImplemented" in t for t in tasks)
    questions.append(
        _q(
            "manual_checkpoint",
            "manual_tasks",
            "If a file has `TODO: Human Hands-On Implementation` or `NotImplementedError`, what should you do?",
            [
                "Ignore it and merge anyway",
                "Ask an agent to silently fill it with no learning",
                "Treat it as YOUR job — implement/understand it before claiming the resume bullet",
                "Delete the whole repository",
            ],
            2,
            "The ledger forbids agents from auto-completing human checkpoints.",
        )
    )
    if has_checkpoint:
        questions.append(
            _q(
                "manual_env",
                "manual_tasks",
                "Where do real API keys belong?",
                [
                    "Committed into GitHub so teammates can see them",
                    "Hardcoded in interceptor.py",
                    "In local `.env` / host secret stores — never in git",
                    "In a public Discord channel",
                ],
                2,
                "Secrets only via environment variables (§8 of the Ledger).",
            )
        )

    # Security
    questions.append(
        _q(
            "sec_keys",
            "security",
            "Which is a security red flag in a PR?",
            [
                "Using pydantic-settings to read env vars",
                "A hardcoded `API_KEY = \"sk-...\"` string in source",
                "Adding a `/health` endpoint",
                "Writing a README",
            ],
            1,
            "Hardcoded secrets are critical findings in the OWASP auditor.",
        )
    )
    questions.append(
        _q(
            "sec_why_gate",
            "security",
            "Why is reviewing AI-generated code without understanding it dangerous?",
            [
                "It isn't — AI is always correct",
                "You might approve insecure, wrong, or unmaintainable logic you cannot defend in an interview or outage",
                "GitHub will revoke your account for reading code",
                "Tests become illegal",
            ],
            1,
            "This quiz exists so 'human review' means informed review, not a blind click.",
        )
    )

    return questions


def _llm_enrich(pack: dict[str, Any], diff_text: str) -> dict[str, Any]:
    """Optionally ask an LLM to add beginner-friendly questions from the real diff."""
    api_key = os.getenv("GOVERNANCE_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key or not diff_text.strip():
        return pack

    base_url = os.getenv("GOVERNANCE_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("GOVERNANCE_LLM_MODEL", "gpt-4o-mini")
    system = """You help an absolute beginner engineer understand a PR before merging.
Return JSON only:
{
  "extra_glossary": [{"term":"...","definition":"..."}],
  "extra_questions": [{
    "id":"llm_...",
    "category":"how_it_works|bigger_picture|dependencies|manual_tasks|functions|security|vocabulary",
    "prompt":"...",
    "choices":["...","...","...","..."],
    "answer_index":0,
    "explanation":"..."
  }],
  "plain_english_summary":"2-4 sentences at a beginner level"
}
Rules: kind tone, no jargon without defining it, 3-5 extra questions, exactly 4 choices each.
"""
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    "Diff to teach from:\n\n"
                    + diff_text[:50000]
                    + "\n\nExisting study guide JSON:\n"
                    + json.dumps(pack["study_guide"])[:8000]
                ),
            },
        ],
        "response_format": {"type": "json_object"},
    }
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
    except Exception:  # noqa: BLE001
        return pack

    guide = pack["study_guide"]
    for g in data.get("extra_glossary") or []:
        if g.get("term") and g.get("definition"):
            guide["glossary"].append(
                {"term": str(g["term"]), "definition": str(g["definition"])}
            )
    if data.get("plain_english_summary"):
        guide["elevator_pitch"] = str(data["plain_english_summary"])

    for raw in data.get("extra_questions") or []:
        choices = raw.get("choices") or []
        if len(choices) != 4:
            continue
        try:
            idx = int(raw.get("answer_index", 0))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx > 3:
            continue
        cat = str(raw.get("category") or "how_it_works")
        pack["questions"].append(
            _q(
                str(raw.get("id") or f"llm_{len(pack['questions'])}"),
                cat,
                str(raw.get("prompt") or "What does this change do?"),
                [str(c) for c in choices],
                idx,
                str(raw.get("explanation") or "Review the study guide."),
            )
        )
    pack["generator"] = "deterministic+llm"
    return pack


def grade(pack: dict[str, Any], answers: dict[str, int]) -> dict[str, Any]:
    """Grade a learner's answers. `answers` maps question id → choice index."""
    questions = pack.get("questions") or []
    total = len(questions)
    correct = 0
    details = []
    for q in questions:
        qid = q["id"]
        expected = q["answer_index"]
        got = answers.get(qid)
        ok = got == expected
        if ok:
            correct += 1
        details.append(
            {
                "id": qid,
                "correct": ok,
                "expected": expected,
                "got": got,
                "explanation": q.get("explanation"),
                "category": q.get("category"),
            }
        )
    score = (correct / total) if total else 0.0
    threshold = float(pack.get("pass_threshold") or PASS_THRESHOLD)
    return {
        "score": score,
        "correct": correct,
        "total": total,
        "passed": score >= threshold,
        "threshold": threshold,
        "details": details,
    }


def run(
    paths: list[Path],
    *,
    diff_text: str | None = None,
    root: Path | None = None,
    skip_llm: bool = False,
) -> StepResult:
    """Generate study guide + quiz pack for the changed files."""
    # Prefer diff-touched paths; fall back to provided scan set
    pack = _build_deterministic_pack(paths, root=root, diff_text=diff_text)
    if not skip_llm:
        pack = _llm_enrich(pack, diff_text or "")

    findings = [
        Finding(
            step=STEP_ID,
            severity=Severity.INFO,
            message=(
                f"Comprehension quiz ready ({len(pack['questions'])} questions, "
                f"pass ≥ {int(PASS_THRESHOLD * 100)}%). Complete it on the dashboard "
                "BEFORE Approve & Merge — shipping code you cannot explain is the risk."
            ),
            rule_id="COMP001_QUIZ_READY",
            suggestion="Open the review dashboard → read the study guide → take the quiz.",
        )
    ]

    # Surface manual tasks as warnings (do not block CI — dashboard blocks merge)
    for task in pack["study_guide"].get("manual_dev_tasks") or []:
        if "No extra manual" in task:
            continue
        findings.append(
            Finding(
                step=STEP_ID,
                severity=Severity.WARNING,
                message=f"Manual dev task: {task}",
                rule_id="COMP002_MANUAL_TASK",
            )
        )

    return StepResult(
        step=STEP_ID,
        name=STEP_NAME,
        passed=True,  # generation succeeded; human pass is enforced on dashboard
        findings=findings,
        metrics={
            "comprehension": pack,
            "question_count": len(pack["questions"]),
            "pass_threshold": PASS_THRESHOLD,
            "generator": pack.get("generator"),
        },
    )
