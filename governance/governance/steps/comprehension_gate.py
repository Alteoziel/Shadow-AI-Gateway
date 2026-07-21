"""Step 6 — Comprehension Gate: beginner study guide + understanding quiz.

Sits after automated analysis (Steps 1–5) and before the human review/merge
panel (Step 7). Goal: you must understand what shipped — vocabulary, how it
works, bigger picture, dependencies, manual tasks, functions, security —
before approving a merge. Shipping code you cannot explain is the danger.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import random
import re
from pathlib import Path
from typing import Any

import httpx

from governance.models import Finding, Severity, StepResult

STEP_ID = "comprehension_gate"
STEP_NAME = "Comprehension Gate (Dev Understanding Check)"

PASS_THRESHOLD = 0.8  # 80% correct required on the dashboard quiz

# Tagged glossary — only terms whose tags match this PR's areas/files are shown.
TERM_BANK: list[dict[str, Any]] = [
    {
        "term": "pre-flight",
        "tags": {"proxy", "interceptor", "api"},
        "definition": (
            "Inspecting/normalizing an outbound LLM request BEFORE any bytes "
            "leave your network toward OpenAI/Anthropic."
        ),
        "near_miss": "Running pytest after the provider already returned a response",
    },
    {
        "term": "proxy / gateway",
        "tags": {"proxy", "api", "security"},
        "definition": (
            "A service between clients and public LLM APIs so outbound prompts "
            "can be inspected and controlled."
        ),
        "near_miss": "A static file CDN that only caches images",
    },
    {
        "term": "provider adapter",
        "tags": {"proxy", "api"},
        "definition": (
            "Code that maps our internal request shape to OpenAI's or Anthropic's API."
        ),
        "near_miss": "A React component that renders chat bubbles",
    },
    {
        "term": "FastAPI",
        "tags": {"proxy", "api"},
        "definition": (
            "Python web framework used for gateway routes like POST /v1/chat/completions."
        ),
        "near_miss": "The Next.js App Router used only by the review dashboard",
    },
    {
        "term": "interceptor",
        "tags": {"proxy", "interceptor"},
        "definition": (
            "The pre-flight hook (`intercept_outbound_request`) that validates/"
            "normalizes bodies before provider adapters run."
        ),
        "near_miss": "A GitHub Action that only posts commit statuses",
    },
    {
        "term": "Governance Quiz",
        "tags": {"dashboard", "governance", "quiz"},
        "definition": (
            "GitHub commit-status check set to pending by CI and flipped to success "
            "only after you pass Step 6 on the dashboard."
        ),
        "near_miss": "A Vercel build badge that turns green when npm install finishes",
    },
    {
        "term": "comprehension gate",
        "tags": {"governance", "quiz", "dashboard"},
        "definition": (
            "Step 6 of the guardrail suite: study guide + quiz you must pass before "
            "Approve & Merge unlocks."
        ),
        "near_miss": "Step 1 AST scan that only checks nested loop depth",
    },
    {
        "term": "provider",
        "tags": {"proxy", "api"},
        "definition": (
            "The outside LLM service the gateway can call, such as OpenAI or "
            "Anthropic. Phase 1 chooses one per request or from config."
        ),
        "near_miss": "The local governance pytest suite that never calls an LLM",
    },
    {
        "term": "upstream provider",
        "tags": {"proxy", "api"},
        "definition": (
            "The external provider API reached after the gateway route and "
            "human-owned interceptor checkpoint have allowed the request forward."
        ),
        "near_miss": "The review dashboard's Upstash Redis store",
    },
    {
        "term": "streaming / SSE",
        "tags": {"proxy", "api"},
        "definition": (
            "A response mode where tokens/chunks flow back over time instead of "
            "waiting for one complete JSON response."
        ),
        "near_miss": "A one-shot JSON POST that waits for the full reply",
    },
    {
        "term": "HTTP 501",
        "tags": {"proxy", "interceptor", "api"},
        "definition": (
            "Not Implemented. In Phase 1 it means Checkpoint #1 is still pending "
            "and the human must complete the interceptor before provider forwarding."
        ),
        "near_miss": "HTTP 401 Unauthorized from a missing reviewer secret",
    },
    {
        "term": "async / await",
        "tags": {"proxy", "api"},
        "definition": (
            "Python concurrency style that lets the server handle many requests "
            "while waiting on network I/O (e.g. calling OpenAI) without blocking."
        ),
        "near_miss": "A synchronous sleep that blocks the whole process on purpose",
    },
    {
        "term": "AST",
        "tags": {"governance", "ast"},
        "definition": (
            "Abstract Syntax Tree — structured parse of source used to catch bad "
            "structure (e.g. nested loops) without executing the code."
        ),
        "near_miss": "A runtime profiler that only measures HTTP latency",
    },
    {
        "term": "Upstash Redis",
        "tags": {"dashboard", "store"},
        "definition": (
            "Serverless Redis used by the Vercel dashboard to persist review/quiz state "
            "(no local disk writes)."
        ),
        "near_miss": "Postgres audit log planned for Phase 3 of the proxy",
    },
    {
        "term": "reviewer secret",
        "tags": {"dashboard", "auth"},
        "definition": (
            "Shared password (`GOVERNANCE_DASHBOARD_SECRET` / reviewer secret) required "
            "to submit the quiz and take human approve/merge actions."
        ),
        "near_miss": "The public GitHub Actions run ID printed in CI logs",
    },
    {
        "term": "commit status",
        "tags": {"dashboard", "github", "quiz"},
        "definition": (
            "Per-commit GitHub Checks API state (pending/success/failure) that branch "
            "protection can require before merge."
        ),
        "near_miss": "A label applied to the PR title for triage",
    },
    {
        "term": "environment variable",
        "tags": {"security", "config", "dashboard", "proxy"},
        "definition": (
            "Runtime config/secret (e.g. OPENAI_API_KEY) injected by the host — never "
            "committed as source."
        ),
        "near_miss": "A constant string literal checked into the repo for convenience",
    },
    {
        "term": "PII",
        "tags": {"security", "proxy"},
        "definition": (
            "Personally Identifiable Information — later phases redact it before "
            "prompts leave the network."
        ),
        "near_miss": "Public package names listed in requirements.txt",
    },
    {
        "term": "node:vm",
        "tags": {"dashboard", "coding", "quiz"},
        "definition": (
            "Node sandbox used by the dashboard to re-grade coding-challenge "
            "submissions server-side with a short timeout."
        ),
        "near_miss": "The browser MiniCodeEditor textarea that only stores draft text",
    },
]

CATEGORY_LABELS = {
    "vocabulary": "Vocabulary & definitions",
    "what_changed": "What changed in this PR",
    "how_it_works": "How this change works",
    "bigger_picture": "Bigger picture / architecture",
    "dependencies": "Dependencies & what it touches",
    "manual_tasks": "Manual things you must do",
    "functions": "Functions & call flow",
    "security": "Security implications",
    "coding_problem": "Coding problem (from this PR)",
}

# Near-miss packages from THIS monorepo (used as plausible wrong answers).
PROJECT_PACKAGE_DISTRACTORS = [
    "fastapi",
    "httpx",
    "pydantic",
    "typer",
    "next",
    "react",
    "@upstash/redis",
    "openai",
    "anthropic",
    "pytest",
]


def _rel(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _python_arg_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Positional + keyword-only arg names (skip self/cls)."""
    names: list[str] = []
    for a in list(node.args.args) + list(node.args.kwonlyargs):
        if a.arg in {"self", "cls"}:
            continue
        names.append(a.arg)
    return names


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
                    "args": _python_arg_names(node),
                    "lineno": node.lineno,
                    "doc": ast.get_docstring(node) or "",
                }
            )
        elif isinstance(node, ast.AsyncFunctionDef):
            info["async_functions"].append(
                {
                    "name": node.name,
                    "args": _python_arg_names(node),
                    "lineno": node.lineno,
                    "doc": ast.get_docstring(node) or "",
                }
            )
        elif isinstance(node, ast.ClassDef):
            info["classes"].append(node.name)
    info["imports"] = sorted(set(info["imports"]))
    return info


def _extract_ts_symbols(path: Path) -> dict[str, Any]:
    """Lightweight TS/JS export/function scan (regex — no nested AST walks)."""
    info: dict[str, Any] = {
        "imports": [],
        "functions": [],
        "async_functions": [],
        "classes": [],
        "exported": [],
    }
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return info

    for m in re.finditer(
        r"""from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)""",
        text,
    ):
        mod = m.group(1) or m.group(2) or ""
        top = mod.split("/")[0].lstrip("@") if mod.startswith("@") else mod.split("/")[0]
        if top and not top.startswith("."):
            info["imports"].append(top)

    for m in re.finditer(
        r"(?P<export>export\s+)?(?P<async>async\s+)?function\s+(?P<name>[A-Za-z_][\w]*)\s*\((?P<args>[^)]*)\)",
        text,
    ):
        args = [a.strip().split(":")[0].strip() for a in m.group("args").split(",") if a.strip()]
        args = [a for a in args if a and a != "this"]
        entry = {
            "name": m.group("name"),
            "args": args,
            "lineno": text[: m.start()].count("\n") + 1,
            "doc": "",
            "exported": bool(m.group("export")),
        }
        if m.group("async"):
            info["async_functions"].append(entry)
        else:
            info["functions"].append(entry)
        if m.group("export"):
            info["exported"].append(m.group("name"))

    for m in re.finditer(
        r"export\s+(?:const|let|var)\s+(?P<name>[A-Za-z_][\w]*)\s*=\s*(?P<async>async\s*)?\(",
        text,
    ):
        entry = {
            "name": m.group("name"),
            "args": [],
            "lineno": text[: m.start()].count("\n") + 1,
            "doc": "",
            "exported": True,
        }
        if m.group("async"):
            info["async_functions"].append(entry)
        else:
            info["functions"].append(entry)
        info["exported"].append(m.group("name"))

    info["imports"] = sorted(set(info["imports"]))
    info["exported"] = sorted(set(info["exported"]))
    return info


def _read_npm_deps(root: Path | None) -> list[str]:
    if root is None:
        return []
    pkg = root / "dashboard" / "package.json"
    if not pkg.is_file():
        return []
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
    return sorted(deps.keys())


def _areas_for_files(rels: list[str]) -> set[str]:
    areas: set[str] = set()
    for rel in rels:
        low = rel.replace("\\", "/").lower()
        if "interceptor" in low:
            areas.add("interceptor")
        if "/proxy/" in low or low.startswith("app/proxy"):
            areas.add("proxy")
        if "dashboard" in low:
            areas.add("dashboard")
        if "governance" in low:
            areas.add("governance")
        if "ast_guardrail" in low or "/ast" in low:
            areas.add("ast")
        if "comprehension" in low or "quiz" in low or "codinggrade" in low:
            areas.add("quiz")
        if "/security/" in low or "auth.ts" in low:
            areas.add("security")
        if "store.ts" in low or "redis" in low:
            areas.add("store")
        if "github.ts" in low or "statuses" in low:
            areas.add("github")
        if low.startswith("app/api") or "/api/" in low:
            areas.add("api")
        if "config" in low or ".env" in low:
            areas.add("config")
        if "minicodeeditor" in low or "coding" in low:
            areas.add("coding")
        if low.endswith(".tsx") or low.endswith(".ts"):
            areas.add("dashboard")
    if not areas:
        areas.add("general")
    return areas


def _scan_security_hints(paths: list[Path], root: Path | None) -> list[str]:
    hints: list[str] = []
    patterns = [
        (re.compile(r"API_KEY\s*=\s*[\"']sk-"), "Hardcoded API key literal in source"),
        (re.compile(r"eval\s*\("), "Use of eval() — arbitrary code execution risk"),
        (re.compile(r"sessionStorage|localStorage"), "Browser storage of potentially sensitive data"),
        (re.compile(r"Authorization.*Bearer|GITHUB_TOKEN"), "GitHub/token authorization handling"),
        (re.compile(r"password|secret|token", re.I), "Secret/password/token handling"),
    ]
    for path in paths:
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = _rel(path, root)
        for rx, label in patterns:
            if rx.search(text):
                hints.append(f"{label} (`{rel}`)")
                break
    # de-dupe
    seen: set[str] = set()
    out: list[str] = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out[:8]


def _detect_manual_tasks(
    paths: list[Path],
    symbols: dict[str, dict],
    *,
    areas: set[str],
    rels: list[str],
) -> list[str]:
    tasks: list[str] = []
    joined = " ".join(rels).lower()

    if "interceptor" in areas:
        tasks.append(
            "If `intercept_outbound_request` still raises NotImplementedError / 501, "
            "implement and test it in `app/proxy/interceptor.py` before claiming the feature."
        )
    if "dashboard" in areas:
        tasks.append(
            "Dashboard: set `GOVERNANCE_DASHBOARD_SECRET` on Vercel to match the GitHub "
            "repo secret, then redeploy so CI can POST reviews."
        )
    if "quiz" in areas or "github" in areas:
        tasks.append(
            "After this lands: re-run Governance CI, take the new quiz on the dashboard, "
            "and ensure the **Governance Quiz** commit status can flip to success "
            "(needs a GitHub token with statuses:write on Vercel)."
        )
    if "store" in areas:
        tasks.append(
            "Confirm Upstash Redis is linked on the Vercel project (no disk store on serverless)."
        )
    if any(".env" in r or "config" in r for r in rels):
        tasks.append(
            "Copy `.env.example` → `.env` locally and fill secrets — never commit `.env`."
        )
    if "dockerfile" in joined or "fly.toml" in joined or "render.yaml" in joined:
        tasks.append(
            "If deploying the proxy: set secrets in the host dashboard (Fly/Render), not in git."
        )
    if "governance" in areas:
        tasks.append(
            "After changing governance rules: `cd governance && pytest` and "
            "`ai-guardrail run --root ..` before opening/updating the PR."
        )

    for path, meta in symbols.items():
        fn_list = meta.get("functions", []) + meta.get("async_functions", [])
        for fn in fn_list:
            if "notimplemented" in (fn.get("doc") or "").lower():
                tasks.append(
                    f"Finish incomplete function `{fn['name']}` in `{path}` "
                    "(docstring mentions NotImplemented)."
                )

    for path in paths:
        if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.name
        if "TODO: Human Hands-On Implementation" in text:
            tasks.append(
                f"There is a human hands-on TODO in `{rel}` — implement it yourself; "
                "agents must not silently complete it."
            )
        # Only flag real raises — string literals in quiz templates must not count.
        if re.search(r"raise\s+NotImplementedError\b", text):
            tasks.append(
                f"`{rel}` still raises NotImplementedError — the feature is scaffolded "
                "but not finished."
            )

    seen: set[str] = set()
    out: list[str] = []
    for t in tasks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    if not out:
        file_hint = ", ".join(rels[:5]) if rels else "these files"
        out.append(
            f"No automated checklist markers in this diff — still read `{file_hint}` "
            "and pass the quiz before merging."
        )
    return out


def _stable_seed(rels: list[str], diff_text: str | None) -> int:
    material = "\n".join(sorted(rels)) + "\n" + (diff_text or "")[:4000]
    return int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:12], 16)


def _parse_diff_facts(diff_text: str | None) -> dict[str, Any]:
    """Pull concrete, beginner-friendly facts from a unified diff for quiz grounding."""
    facts: dict[str, Any] = {
        "files": [],
        "added_symbols": [],
        "removed_symbols": [],
        "sample_added_lines": [],
        "total_added": 0,
        "total_removed": 0,
        "summary": "",
        "top_file": "",
    }
    if not (diff_text or "").strip():
        return facts

    current: dict[str, Any] | None = None
    file_re = re.compile(r"^diff --git a/(.+?) b/(.+)$")
    add_sym = re.compile(
        r"^\+\s*(?:export\s+)?(?:async\s+)?(?:def|function|class)\s+([A-Za-z_][\w]*)"
        r"|^\+\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][\w]*)\s*="
    )
    rem_sym = re.compile(
        r"^\-\s*(?:export\s+)?(?:async\s+)?(?:def|function|class)\s+([A-Za-z_][\w]*)"
        r"|^\-\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][\w]*)\s*="
    )

    def _flush() -> None:
        nonlocal current
        if current is not None:
            facts["files"].append(current)
            current = None

    for line in diff_text.splitlines():
        m = file_re.match(line)
        if m:
            _flush()
            current = {
                "path": m.group(2),
                "added": 0,
                "removed": 0,
                "status": "modified",
            }
            continue
        if current is None:
            continue
        if line.startswith("new file mode"):
            current["status"] = "added"
            continue
        if line.startswith("deleted file mode"):
            current["status"] = "deleted"
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            current["added"] += 1
            facts["total_added"] += 1
            sm = add_sym.match(line)
            if sm:
                name = sm.group(1) or sm.group(2)
                if name and name not in facts["added_symbols"]:
                    facts["added_symbols"].append(name)
            content = line[1:].strip()
            if (
                content
                and not content.startswith(("#", "//", "*", "import ", "from "))
                and len(content) > 12
                and len(facts["sample_added_lines"]) < 6
            ):
                facts["sample_added_lines"].append(content[:140])
        elif line.startswith("-"):
            current["removed"] += 1
            facts["total_removed"] += 1
            sm = rem_sym.match(line)
            if sm:
                name = sm.group(1) or sm.group(2)
                if name and name not in facts["removed_symbols"]:
                    facts["removed_symbols"].append(name)
    _flush()

    if facts["files"]:
        top = max(facts["files"], key=lambda f: f["added"] + f["removed"])
        facts["top_file"] = top["path"]
        n_files = len(facts["files"])
        bits = [
            f"Edits touch {n_files} file(s) "
            f"(+{facts['total_added']}/−{facts['total_removed']} lines)."
        ]
        if facts["added_symbols"]:
            bits.append(
                "New/updated symbols include: "
                + ", ".join(f"`{s}`" for s in facts["added_symbols"][:5])
                + "."
            )
        elif facts["top_file"]:
            bits.append(f"Most churn is in `{facts['top_file']}`.")
        facts["summary"] = " ".join(bits)
    return facts


def _pick_glossary(areas: set[str], *, limit: int = 6) -> list[dict[str, str]]:
    matched = [
        t for t in TERM_BANK if areas & set(t.get("tags") or ())
    ]
    if len(matched) < 3:
        matched = list(TERM_BANK[:5])
    # Prefer diversity of terms; stable order by term name then truncate
    matched = sorted(matched, key=lambda t: t["term"])
    # Rotate by area fingerprint so different PRs surface different vocab first
    offset = sum(ord(c) for c in "".join(sorted(areas))) % max(len(matched), 1)
    rotated = matched[offset:] + matched[:offset]
    out: list[dict[str, str]] = []
    for t in rotated[:limit]:
        out.append({"term": t["term"], "definition": t["definition"]})
    return out


def _subsystem_label(areas: set[str]) -> str:
    if "dashboard" in areas and "proxy" not in areas:
        return "the governance review dashboard (Next.js on Vercel)"
    if "proxy" in areas or "interceptor" in areas:
        return "the Shadow AI Guardrail Gateway (FastAPI proxy)"
    if "governance" in areas:
        return "the AI Guardrail governance suite (CI Steps 1–6)"
    return "this repository's AI governance / gateway stack"


def _build_deterministic_pack(
    paths: list[Path],
    *,
    root: Path | None = None,
    diff_text: str | None = None,
) -> dict[str, Any]:
    file_paths = [p for p in paths if p.is_file()]
    py_files = [p for p in file_paths if p.suffix == ".py"]
    ts_files = [p for p in file_paths if p.suffix.lower() in {".ts", ".tsx", ".js", ".jsx"}]

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

    for path in ts_files[:40]:
        rel = _rel(path, root)
        meta = _extract_ts_symbols(path)
        symbols[rel] = meta
        all_imports.update(meta["imports"])
        for fn in meta["functions"] + meta["async_functions"]:
            all_fns.append((rel, fn))

    # Prefer exported / documented callables when building quiz focus
    def _fn_rank(item: tuple[str, dict]) -> tuple[int, int, str]:
        rel, fn = item
        exported = 0 if fn.get("exported") or fn["name"] in set(
            symbols.get(rel, {}).get("exported") or []
        ) else 1
        has_doc = 0 if (fn.get("doc") or "").strip() else 1
        return (exported, has_doc, fn["name"])

    all_fns.sort(key=_fn_rank)

    changed_names = [_rel(p, root) for p in file_paths][:30]
    areas = _areas_for_files(changed_names)
    manual = _detect_manual_tasks(paths, symbols, areas=areas, rels=changed_names)
    security_hints = _scan_security_hints(file_paths, root)
    npm_deps = _read_npm_deps(root) if "dashboard" in areas else []
    seed = _stable_seed(changed_names, diff_text)
    diff_facts = _parse_diff_facts(diff_text)

    key_functions = []
    for rel, fn in all_fns[:12]:
        async_names = {f["name"] for f in symbols.get(rel, {}).get("async_functions", [])}
        kind = "async function" if fn["name"] in async_names else "function"
        plain = (fn.get("doc") or "").strip() or (
            f"A {kind} named `{fn['name']}` in `{rel}`. "
            f"Arguments: {', '.join(fn['args']) or 'none'}."
        )
        key_functions.append(
            {"name": fn["name"], "file": rel, "plain_english": plain[:400]}
        )

    glossary = _pick_glossary(areas)
    subsystem = _subsystem_label(areas)

    elevator_bits = [f"This PR changes {subsystem}."]
    if diff_facts.get("summary"):
        elevator_bits.append(str(diff_facts["summary"]))
    elif changed_names:
        elevator_bits.append(
            "Files involved: " + ", ".join(changed_names[:8]) + "."
        )
    else:
        elevator_bits.append("Review the study guide for what is being proposed.")
    if key_functions:
        elevator_bits.append(
            "Focus first on: "
            + ", ".join(f"`{kf['name']}`" for kf in key_functions[:3])
            + "."
        )
    elevator = " ".join(elevator_bits)

    bigger_bits = [
        f"Primary areas touched: {', '.join(sorted(areas))}."
    ]
    if "dashboard" in areas:
        bigger_bits.append(
            "The dashboard is Step 7 of governance: humans take the Step 6 quiz here "
            "and approve/merge; it is not the streaming LLM proxy."
        )
    if "proxy" in areas or "interceptor" in areas:
        bigger_bits.append(
            "The FastAPI gateway is the production choke point for outbound LLM traffic; "
            "it must not be deployed as a Vercel serverless function."
        )
    if "governance" in areas or "quiz" in areas:
        bigger_bits.append(
            "CI Steps 1–6 analyze the PR and generate this quiz; merging should stay "
            "blocked until comprehension (and other required checks) pass."
        )
    if not any(k in areas for k in ("dashboard", "proxy", "governance", "quiz")):
        bigger_bits.append(
            "Place this change in the wider system: what calls it, what it calls, "
            "and what breaks if it is wrong."
        )
    bigger = " ".join(bigger_bits)

    deps = sorted(all_imports)
    if npm_deps:
        deps = sorted(set(deps) | set(npm_deps[:20]))
    if not deps:
        deps = ["(no imports detected in scanned files — still name sibling modules this code calls)"]

    security_notes_out: list[str] = []
    seen_sec: set[str] = set()
    candidates = list(security_hints[:4])
    if "dashboard" in areas:
        candidates.append(
            "Keep the reviewer secret in memory only in the browser — never sessionStorage."
        )
    if "proxy" in areas or "interceptor" in areas:
        candidates.append(
            "Bad validation in the interceptor means prompts can leave unchecked — "
            "treat it as the security choke point."
        )
    if "github" in areas or "quiz" in areas:
        candidates.append(
            "Tokens used for commit statuses / merge must be scoped narrowly and stored "
            "as Vercel env vars, not in the repo."
        )
    candidates.append(
        "Never commit real API keys — use environment variables / host secret stores."
    )
    for s in candidates:
        if s not in seen_sec:
            seen_sec.add(s)
            security_notes_out.append(s)

    study_guide = {
        "elevator_pitch": elevator,
        "bigger_picture": bigger,
        "glossary": glossary,
        "key_functions": key_functions,
        "dependencies": deps[:24],
        "manual_dev_tasks": manual,
        "security_notes": security_notes_out[:6],
        "files_touched": changed_names,
        "areas": sorted(areas),
        "diff_chars": len(diff_text or ""),
        "what_changed": {
            "summary": diff_facts.get("summary") or "",
            "top_file": diff_facts.get("top_file") or (changed_names[0] if changed_names else ""),
            "added_symbols": list(diff_facts.get("added_symbols") or [])[:8],
            "removed_symbols": list(diff_facts.get("removed_symbols") or [])[:8],
            "total_added": int(diff_facts.get("total_added") or 0),
            "total_removed": int(diff_facts.get("total_removed") or 0),
        },
    }

    questions = _make_questions(
        study_guide,
        all_fns,
        all_imports,
        paths=paths,
        root=root,
        areas=areas,
        seed=seed,
        npm_deps=npm_deps,
        security_hints=security_hints,
        diff_facts=diff_facts,
    )
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
    *,
    format: str = "text",
    seed: int = 0,
) -> dict[str, Any]:
    """Build a question and shuffle choices (stable per qid+seed)."""
    rng = random.Random(f"{seed}:{qid}")
    indexed = list(enumerate(choices))
    rng.shuffle(indexed)
    shuffled = [c for _, c in indexed]
    new_answer = next(i for i, (old_i, _) in enumerate(indexed) if old_i == answer_index)
    return {
        "id": qid,
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "prompt": prompt,
        "choices": shuffled,
        "answer_index": new_answer,
        "explanation": explanation,
        "format": format,
    }


def _other_files(files: list[str], correct: str, n: int = 3) -> list[str]:
    others = [f for f in files if f != correct]
    if len(others) >= n:
        return others[:n]
    fillers = [
        "app/main.py",
        "dashboard/src/app/page.tsx",
        "governance/governance/cli.py",
        "app/proxy/providers/openai.py",
        "tests/test_health.py",
    ]
    out = list(others)
    for f in fillers:
        if f != correct and f not in out:
            out.append(f)
        if len(out) >= n:
            break
    return out[:n]


def _other_fns(fns: list[tuple[str, dict]], correct: str, n: int = 3) -> list[str]:
    names = []
    for _, fn in fns:
        name = fn["name"]
        if name != correct and name not in names:
            names.append(name)
    fillers = [
        "intercept_outbound_request",
        "gradeComprehension",
        "parseGithubRepo",
        "setGovernanceQuizStatus",
        "collect_paths",
        "run_ast_guardrail",
    ]
    for f in fillers:
        if f != correct and f not in names:
            names.append(f)
        if len(names) >= n:
            break
    return names[:n]


def _fake_packages(real: set[str], n: int = 3) -> list[str]:
    """Prefer other packages from this monorepo as near-miss distractors."""
    out: list[str] = []
    for c in PROJECT_PACKAGE_DISTRACTORS:
        if c not in real and c not in out:
            out.append(c)
        if len(out) >= n:
            return out[:n]
    # Fallback only if the PR somehow already imports everything above
    for c in ("django", "flask", "express", "mongodb", "jquery", "rails"):
        if c not in real and c not in out:
            out.append(c)
        if len(out) >= n:
            break
    return out[:n]


def _build_mc_pool(
    guide: dict[str, Any],
    all_fns: list[tuple[str, dict]],
    imports: set[str],
    *,
    areas: set[str],
    seed: int,
    npm_deps: list[str],
    security_hints: list[str],
    diff_facts: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Candidate MC questions grounded in this PR (caller selects a subset)."""
    pool: list[dict[str, Any]] = []
    files = list(guide.get("files_touched") or [])
    glossary = list(guide.get("glossary") or [])
    tasks = list(guide.get("manual_dev_tasks") or [])
    deps = list(guide.get("dependencies") or [])
    key_fns = list(guide.get("key_functions") or [])
    security_notes = list(guide.get("security_notes") or [])
    diff_facts = diff_facts or {}
    wc = guide.get("what_changed") or {}

    # --- What changed (basics of THIS PR) ---
    top_file = str(wc.get("top_file") or diff_facts.get("top_file") or (files[0] if files else ""))
    if top_file:
        distractor_files = _other_files(files or [top_file], top_file)
        pool.append(
            _q(
                "changed_top_file",
                "what_changed",
                "Which file has the most churn (added+removed lines) or is the primary focus of this PR?",
                [top_file, *distractor_files],
                0,
                f"Diff/file scan points at `{top_file}` as the main focus for this change.",
                seed=seed + 1,
            )
        )

    added_syms = list(wc.get("added_symbols") or diff_facts.get("added_symbols") or [])
    if added_syms:
        correct = added_syms[0]
        wrong = _other_fns(all_fns, correct, 3)
        # Prefer other symbols from the repo that were NOT added in this diff
        for filler in ("intercept_outbound_request", "gradeComprehension", "collect_paths"):
            if filler != correct and filler not in wrong and filler not in added_syms:
                wrong.append(filler)
        pool.append(
            _q(
                f"changed_symbol_{correct[:28]}",
                "what_changed",
                "Which symbol appears as newly added/updated in this PR’s diff?",
                [correct, *wrong[:3]],
                0,
                f"Unified diff shows `{correct}` on added lines among: "
                + ", ".join(added_syms[:5])
                + ".",
                seed=seed + 2,
            )
        )
    elif key_fns:
        kf = key_fns[0]
        wrong = _other_fns(all_fns, kf["name"], 3)
        pool.append(
            _q(
                f"changed_focus_{kf['name'][:28]}",
                "what_changed",
                "Which callable should you be able to explain after reading this PR?",
                [kf["name"], *wrong[:3]],
                0,
                f"`{kf['name']}` is a key function in `{kf['file']}` for this change set.",
                seed=seed + 2,
            )
        )

    if files:
        area_list = ", ".join(sorted(areas)) or "general"
        correct = (
            f"It modifies `{files[0]}` and related files under: {area_list}."
        )
        pool.append(
            _q(
                "changed_scope",
                "what_changed",
                "In plain English, what is the scope of this PR?",
                [
                    correct,
                    "It only renames a README badge and touches no application code",
                    "It replaces the entire gateway with a mobile-only client",
                    "It deletes the governance suite and removes the quiz gate",
                ],
                0,
                "Grounded in files_touched + detected areas for this pack.",
                seed=seed + 3,
            )
        )

    # --- Vocabulary (from this PR's glossary) ---
    for i, g in enumerate(glossary[:4]):
        term = g["term"]
        bank = next((t for t in TERM_BANK if t["term"] == term), None)
        near = (bank or {}).get("near_miss") or (
            "A related CI status check with a different merge effect"
        )
        other_defs = [
            x["definition"]
            for x in glossary
            if x["term"] != term
        ][:2]
        # Prefer near-miss definitions from the TERM_BANK for other project areas
        while len(other_defs) < 2:
            for t in TERM_BANK:
                if t["term"] == term:
                    continue
                if t["definition"] not in other_defs and t["definition"] != g["definition"]:
                    other_defs.append(t["definition"])
                if len(other_defs) >= 2:
                    break
            break
        while len(other_defs) < 2:
            other_defs.append(
                "A related concept from another subsystem of this monorepo"
            )
        choices = [g["definition"], near, other_defs[0], other_defs[1]]
        pool.append(
            _q(
                f"vocab_{re.sub(r'[^a-z0-9]+', '_', term.lower())[:40]}",
                "vocabulary",
                f"In **this PR’s study guide**, what does **{term}** mean?",
                choices,
                0,
                f"See the vocabulary entry for `{term}` — it was included because this "
                f"change touches: {', '.join(sorted(areas))}.",
                seed=seed + i,
            )
        )

    # --- Functions / files ---
    if key_fns:
        kf = key_fns[0]
        distractor_files = _other_files(files or [kf["file"]], kf["file"])
        pool.append(
            _q(
                f"fn_where_{kf['name'][:32]}",
                "functions",
                f"Which file in this change defines `{kf['name']}`?",
                [kf["file"], *distractor_files],
                0,
                f"`{kf['name']}` is listed under Key functions for `{kf['file']}`.",
                seed=seed + 11,
            )
        )
        if kf.get("plain_english"):
            wrong_descs = [
                f"Legacy helper kept only for docs examples — not called from `{kf['file']}`",
                f"Test fixture factory used exclusively under `tests/`, unrelated to `{kf['file']}`",
                f"Provider adapter that talks to Anthropic — different module from `{kf['name']}`",
            ]
            # Prefer other key-function descriptions as near-miss distractors
            for other in key_fns[1:4]:
                if other.get("plain_english"):
                    wrong_descs.insert(0, other["plain_english"][:200])
            pool.append(
                _q(
                    f"fn_role_{kf['name'][:32]}",
                    "functions",
                    f"What is the role of `{kf['name']}` in `{kf['file']}`?",
                    [kf["plain_english"][:220], *wrong_descs[:3]],
                    0,
                    f"From the study guide key-functions section for `{kf['name']}`.",
                    seed=seed + 12,
                )
            )

    if len(all_fns) >= 1:
        rel, fn = all_fns[min(1, len(all_fns) - 1)]
        arg_str = ", ".join(fn["args"]) if fn["args"] else "(no parameters)"
        wrong_args = [
            "request, response, session, cookie_jar",
            "(no parameters)",
            "argc, argv",
        ]
        if arg_str in wrong_args:
            wrong_args = [w for w in wrong_args if w != arg_str]
            wrong_args.append("owner, repo, pull_number, merge_method")
        pool.append(
            _q(
                f"fn_args_{fn['name'][:32]}",
                "how_it_works",
                f"What parameters does `{fn['name']}` (in `{rel}`) take?",
                [arg_str, *wrong_args[:3]],
                0,
                f"Signature scan of `{rel}` shows args: {arg_str}.",
                seed=seed + 13,
            )
        )

    if len(files) >= 2:
        focus = files[0]
        sibling = files[1]
        pool.append(
            _q(
                "how_files_relate",
                "how_it_works",
                f"How should you think about `{focus}` relative to `{sibling}` in this PR?",
                [
                    f"Both are in this change set — understand how `{focus}` and `{sibling}` interact before merge",
                    f"`{sibling}` is unrelated noise; only `{focus}` can affect runtime behavior",
                    f"Reviewing either file is enough because they are duplicate copies of the same module",
                    "Ignore both until after merge; CI will rewrite them on main",
                ],
                0,
                "Multi-file PRs need a mental model of how the touched pieces connect.",
                seed=seed + 14,
            )
        )
    elif files:
        focus = files[0]
        area_guess = sorted(_areas_for_files([focus]))
        pool.append(
            _q(
                "how_file_matters",
                "how_it_works",
                f"What should you verify about `{focus}` before approving?",
                [
                    f"Why it changed, what calls it, and what breaks in the {', '.join(area_guess) or 'system'} if it is wrong",
                    "Only whether the filename looks familiar — skip reading the body",
                    "Only whether Prettier/Black formatting changed",
                    "Only whether the author is a bot account",
                ],
                0,
                f"`{focus}` is in files_touched; basics first, then blast radius.",
                seed=seed + 14,
            )
        )

    # --- Bigger picture / subsystem ---
    subsystem = _subsystem_label(areas)
    wrong_systems = [
        "a mobile-only React Native client with no server component",
        "a Terraform-only repo with no application code",
        "an unrelated LeetCode solutions dump",
    ]
    if "dashboard" in areas:
        wrong_systems[0] = (
            "the streaming FastAPI LLM proxy that must not run on Vercel serverless"
        )
    elif "proxy" in areas:
        wrong_systems[0] = (
            "the Next.js governance dashboard hosted on Vercel for quiz/approve only"
        )
    pool.append(
        _q(
            "pic_subsystem",
            "bigger_picture",
            "Which subsystem does this PR primarily change?",
            [subsystem, *wrong_systems],
            0,
            f"Areas detected from paths: {', '.join(sorted(areas))}.",
            seed=seed + 20,
        )
    )

    if "dashboard" in areas and "quiz" in areas:
        pool.append(
            _q(
                "pic_quiz_gate",
                "bigger_picture",
                "For this dashboard/quiz change, what must happen before merge is safe?",
                [
                    "Pass the Step 6 comprehension quiz (and required GitHub checks) for this commit",
                    "Only wait for a green Vercel build — quiz score does not matter",
                    "Merge immediately so CI can generate the quiz afterward",
                    "Disable branch protection until the next release",
                ],
                0,
                "This PR’s areas include dashboard/quiz — comprehension is a merge gate.",
                seed=seed + 21,
            )
        )
    elif "proxy" in areas or "interceptor" in areas:
        pool.append(
            _q(
                "pic_proxy_role",
                "bigger_picture",
                "Where does this proxy/interceptor change sit in the request path?",
                [
                    "Client → gateway route → interceptor/pre-flight → provider adapter → upstream LLM",
                    "Client → OpenAI directly, skipping the gateway entirely",
                    "Client → governance dashboard quiz → merge button → LLM",
                    "Client → Upstash Redis only, with no HTTP API",
                ],
                0,
                "Gateway changes affect the pre-flight path before provider adapters.",
                seed=seed + 21,
            )
        )
    elif "governance" in areas:
        pool.append(
            _q(
                "pic_governance_role",
                "bigger_picture",
                "What is the job of this governance-suite change?",
                [
                    "Analyze the PR in CI and/or generate the comprehension materials that gate merge",
                    "Stream tokens from Anthropic to browsers",
                    "Replace the need for any human review forever",
                    "Host production LLM traffic on Vercel edge functions",
                ],
                0,
                "Governance Steps 1–6 are CI analysis + comprehension, not the LLM proxy.",
                seed=seed + 21,
            )
        )

    # --- Dependencies ---
    def _preferred_dep(candidates: list[str]) -> str | None:
        prefer = [
            "fastapi",
            "httpx",
            "pydantic",
            "openai",
            "anthropic",
            "next",
            "react",
            "@upstash/redis",
            "typer",
            "pytest",
        ]
        clean = [d for d in candidates if d and not d.startswith("(") and not d.startswith("@types")]
        for p in prefer:
            if p in clean:
                return p
        return clean[0] if clean else None

    real_dep = _preferred_dep(deps)
    if real_dep:
        fakes = _fake_packages(set(deps) | set(npm_deps), 3)
        pool.append(
            _q(
                f"dep_has_{re.sub(r'[^a-z0-9]+', '_', real_dep.lower())[:24]}",
                "dependencies",
                "Which dependency/import shows up in the files scanned for this PR?",
                [real_dep, *fakes],
                0,
                f"Detected from changed sources: {', '.join(deps[:10])}.",
                seed=seed + 30,
            )
        )
    if npm_deps and "dashboard" in areas:
        pick = _preferred_dep(npm_deps) or npm_deps[seed % len(npm_deps)]
        fakes = _fake_packages(set(npm_deps), 3)
        pool.append(
            _q(
                "dep_npm_dashboard",
                "dependencies",
                "Which package is declared for the dashboard (`dashboard/package.json`) "
                "and may matter for this change?",
                [pick, *fakes],
                0,
                "From dashboard package.json dependencies (sample relevant to this PR).",
                seed=seed + 31,
            )
        )
    if files:
        pool.append(
            _q(
                "dep_sibling",
                "dependencies",
                "When reviewing dependencies for this change, what should you verify?",
                [
                    "Imports/modules these files use and sibling project files they call at runtime",
                    "Only whether Vercel preview DNS propagated for the marketing site",
                    "Only whether the AST guardrail nested-loop limit is set to 2",
                    "Only whether the Governance Quiz commit status emoji is present",
                ],
                0,
                f"This PR touches {len(files)} file(s); check their real import graph.",
                seed=seed + 32,
            )
        )

    # --- Manual tasks ---
    if tasks:
        task = tasks[0]
        short = task if len(task) < 180 else task[:177] + "…"
        pool.append(
            _q(
                "manual_primary",
                "manual_tasks",
                "Which manual follow-up applies to **this** PR according to the study guide?",
                [
                    short,
                    "Only re-run Bugbot — skip dashboard secrets, Redis, and local pytest",
                    "Merge first, then generate the study guide on `main` afterward",
                    "Treat env/config changes as optional documentation-only edits",
                ],
                0,
                "Taken from this pack’s manual_dev_tasks — not a generic checklist.",
                seed=seed + 40,
            )
        )
    if any("NotImplemented" in t or "hands-on" in t.lower() for t in tasks):
        pool.append(
            _q(
                "manual_nyi",
                "manual_tasks",
                "This PR’s checklist mentions unfinished / NotImplemented work. What should you do?",
                [
                    "Implement or explicitly track it yourself before treating the feature as done",
                    "Leave the stub shipped and rely on upstream adapters to validate instead",
                    "Comment out the function so CI stops reporting the NotImplementedError",
                    "Mark the PR as docs-only so branch protection ignores the stub",
                ],
                0,
                "Human checkpoints exist so you learn the choke points — do not rubber-stamp stubs.",
                seed=seed + 41,
            )
        )

    # --- Security ---
    if security_hints:
        hint = security_hints[0]
        pool.append(
            _q(
                "sec_hint_primary",
                "security",
                "Which security concern did the scanner flag in **this** change set?",
                [
                    hint,
                    "Only outdated npm patch versions with no secret or auth impact",
                    "Missing alt text on a decorative dashboard SVG",
                    "A flaky unit test timeout unrelated to auth or data egress",
                ],
                0,
                "Derived from scanning the files in this PR.",
                seed=seed + 50,
            )
        )
    if security_notes:
        note = security_notes[0]
        near_wrong = [
            "Hardcode provider keys in source so local demos need no `.env`",
            "Persist the reviewer secret in sessionStorage across reloads",
            "Allow unauthenticated merge actions when the suite is green",
        ]
        pool.append(
            _q(
                "sec_note_primary",
                "security",
                "Which security note is attached to **this** PR’s study guide?",
                [note, *near_wrong],
                0,
                "From this pack’s security_notes (area-specific).",
                seed=seed + 51,
            )
        )
    if "dashboard" in areas:
        pool.append(
            _q(
                "sec_dashboard_secret",
                "security",
                "For this dashboard change, how should the reviewer secret be handled in the browser?",
                [
                    "Keep it in process memory for the session — never sessionStorage/localStorage",
                    "Write it to sessionStorage so refresh keeps you logged in forever",
                    "Commit it into `dashboard/src/lib/auth.ts` as a default string",
                    "Print it into the public PR description for teammates",
                ],
                0,
                "CodeQL and the dashboard design forbid clear-text web storage of the secret.",
                seed=seed + 52,
            )
        )
    if "proxy" in areas or "interceptor" in areas:
        pool.append(
            _q(
                "sec_interceptor",
                "security",
                "Why is the interceptor a security-sensitive part of this change?",
                [
                    "It is the pre-flight choke point — weak validation lets prompts leave unchecked",
                    "It only renames CSS classes and cannot affect outbound data",
                    "It runs exclusively after the upstream LLM response is discarded",
                    "It is unused legacy code with no callers",
                ],
                0,
                "Proxy/interceptor areas make outbound validation the critical review focus.",
                seed=seed + 52,
            )
        )

    return pool


def _select_mc_questions(pool: list[dict[str, Any]], *, seed: int, target: int = 8) -> list[dict[str, Any]]:
    """Pick ~target MC questions covering categories; vary by PR seed."""
    rng = random.Random(seed)
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for q in pool:
        by_cat.setdefault(q["category"], []).append(q)

    preferred = [
        "what_changed",
        "vocabulary",
        "functions",
        "how_it_works",
        "bigger_picture",
        "dependencies",
        "manual_tasks",
        "security",
    ]
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for cat in preferred:
        options = by_cat.get(cat) or []
        if not options:
            continue
        pick = options[rng.randrange(len(options))]
        if pick["id"] not in seen_ids:
            selected.append(pick)
            seen_ids.add(pick["id"])

    leftovers = [q for q in pool if q["id"] not in seen_ids]
    rng.shuffle(leftovers)
    for q in leftovers:
        if len(selected) >= target:
            break
        selected.append(q)
        seen_ids.add(q["id"])

    # Prefer leading with what_changed / vocabulary so the quiz opens on PR basics
    selected.sort(
        key=lambda q: 0
        if q["category"] in {"what_changed", "vocabulary", "functions"}
        else 1
    )
    rotate = seed % max(min(3, len(selected)), 1)
    selected = selected[rotate:] + selected[:rotate]
    return selected[:target]


def _make_questions(
    guide: dict[str, Any],
    all_fns: list[tuple[str, dict]],
    imports: set[str],
    *,
    paths: list[Path] | None = None,
    root: Path | None = None,
    areas: set[str] | None = None,
    seed: int = 0,
    npm_deps: list[str] | None = None,
    security_hints: list[str] | None = None,
    diff_facts: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    areas = areas or set(guide.get("areas") or ["general"])
    pool = _build_mc_pool(
        guide,
        all_fns,
        imports,
        areas=areas,
        seed=seed,
        npm_deps=npm_deps or [],
        security_hints=security_hints or [],
        diff_facts=diff_facts,
    )
    questions = _select_mc_questions(pool, seed=seed, target=8)
    questions.extend(
        _make_coding_questions(paths or [], root=root, all_fns=all_fns)
    )
    return questions


def _truncate_code(text: str, limit: int = 700) -> str:
    text = text.strip("\n")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n# ..."


def _return_expressions(source: str, fn_node: ast.AST) -> list[str]:
    """Collect return expression source snippets (kept shallow for AST guardrail)."""
    out: list[str] = []
    for child in ast.walk(fn_node):
        if isinstance(child, ast.Return) and child.value is not None:
            piece = ast.get_source_segment(source, child.value)
            if piece:
                out.append(piece.strip())
            if len(out) >= 4:
                break
    return out


def _snippet_from_function(
    source: str, rel: str, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> dict[str, Any] | None:
    seg = ast.get_source_segment(source, node) or ""
    if len(seg.strip()) < 20:
        return None
    args = _python_arg_names(node)
    return {
        "file": rel,
        "name": node.name,
        "async": isinstance(node, ast.AsyncFunctionDef),
        "args": args,
        "source": _truncate_code(seg),
        "returns": _return_expressions(source, node),
        "doc": ast.get_docstring(node) or "",
    }


def _extract_python_snippets(
    paths: list[Path], *, root: Path | None, limit: int = 8
) -> list[dict[str, Any]]:
    """Pull real callables from the PR so coding questions are about this diff."""
    snippets: list[dict[str, Any]] = []
    py_paths = [p for p in paths if p.is_file() and p.suffix == ".py"]
    for path in py_paths:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue
        rel = _rel(path, root)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            snip = _snippet_from_function(source, rel, node)
            if snip is None:
                continue
            snippets.append(snip)
            if len(snippets) >= limit:
                return snippets
    return snippets


def _coding_challenge(
    *,
    qid: str,
    prompt: str,
    starter_code: str,
    entrypoint: str,
    tests: list[dict[str, Any]],
    explanation: str,
) -> dict[str, Any]:
    """Interactive coding challenge (write code in the dashboard editor)."""
    return {
        "id": qid,
        "question_type": "coding",
        "category": "coding_problem",
        "category_label": CATEGORY_LABELS["coding_problem"],
        "prompt": prompt,
        "language": "javascript",
        "starter_code": starter_code,
        "entrypoint": entrypoint,
        "tests": tests,
        "choices": [],
        "answer_index": -1,
        "explanation": explanation,
        "format": "code",
    }


def _make_coding_questions(
    paths: list[Path],
    *,
    root: Path | None,
    all_fns: list[tuple[str, dict]],
) -> list[dict[str, Any]]:
    """Emit ≥2 short coding challenges the learner must solve in an editor.

    Challenges are JavaScript so the dashboard can run/grade them safely in the
    browser and again on the server (node:vm). Prompts are tied to this PR's
    files/concepts when possible.
    """
    rels = [_rel(p, root).replace("\\", "/") for p in paths if p.is_file()]
    joined = " ".join(rels).lower()
    snippets = _extract_python_snippets(paths, root=root)
    questions: list[dict[str, Any]] = []

    # --- Challenge pool (pick PR-relevant ones first) ---
    pool: list[dict[str, Any]] = []

    if any("github" in r for r in rels) or "quiz" in joined or "governance" in joined:
        pool.append(
            _coding_challenge(
                qid="code_ch_parse_repo",
                prompt=(
                    "**Coding challenge — GitHub repo ref (this PR’s governance check).**\n\n"
                    "Implement `parseOwnerRepo(repo)`.\n"
                    "- Input is a string like `\"Alteoziel/Shadow-AI-Gateway\"`.\n"
                    "- If valid `owner/name` (letters, numbers, `_`, `.`, `-`), "
                    "return `{ owner, name, full }` where `full` is `owner/name`.\n"
                    "- Otherwise return `null`.\n"
                    "- Trim whitespace. Reject empty parts or extra `/` segments."
                ),
                starter_code=(
                    "function parseOwnerRepo(repo) {\n"
                    "  // TODO: implement\n"
                    "}\n"
                ),
                entrypoint="parseOwnerRepo",
                tests=[
                    {
                        "id": "t1",
                        "args": ["Alteoziel/Shadow-AI-Gateway"],
                        "expected": {
                            "owner": "Alteoziel",
                            "name": "Shadow-AI-Gateway",
                            "full": "Alteoziel/Shadow-AI-Gateway",
                        },
                    },
                    {"id": "t2", "args": ["  a/b  "], "expected": {"owner": "a", "name": "b", "full": "a/b"}},
                    {"id": "t3", "args": ["nope"], "expected": None},
                    {"id": "t4", "args": ["a/b/c"], "expected": None},
                    {"id": "t5", "args": [""], "expected": None},
                ],
                explanation=(
                    "Same rules as `parseGithubRepo` in the dashboard — validate before "
                    "building GitHub API URLs."
                ),
            )
        )

    pool.append(
        _coding_challenge(
            qid="code_ch_quiz_score",
            prompt=(
                "**Coding challenge — comprehension scoring.**\n\n"
                "Implement `quizPassed(correct, total, threshold)`.\n"
                "- `correct` and `total` are non-negative integers; `threshold` is 0–1 "
                "(e.g. `0.8`).\n"
                "- Return `true` iff `total > 0` and `(correct / total) >= threshold`.\n"
                "- If `total === 0`, return `false`."
            ),
            starter_code=(
                "function quizPassed(correct, total, threshold) {\n"
                "  // TODO: implement\n"
                "}\n"
            ),
            entrypoint="quizPassed",
            tests=[
                {"id": "t1", "args": [8, 10, 0.8], "expected": True},
                {"id": "t2", "args": [7, 10, 0.8], "expected": False},
                {"id": "t3", "args": [0, 0, 0.8], "expected": False},
                {"id": "t4", "args": [4, 5, 0.8], "expected": True},
                {"id": "t5", "args": [1, 2, 0.5], "expected": True},
            ],
            explanation="Matches the dashboard Step 6 pass rule (≥ threshold).",
        )
    )

    pool.append(
        _coding_challenge(
            qid="code_ch_normalize_messages",
            prompt=(
                "**Coding challenge — gateway request shape.**\n\n"
                "Implement `normalizeMessages(body)` for chat payloads:\n"
                "- Read `body.messages`.\n"
                "- If missing/undefined/null, treat as `[]`.\n"
                "- If it is not an array, throw `Error` with message "
                "`messages must be a list`.\n"
                "- Otherwise return a **new** object: all keys from `body`, with "
                "`messages` set to that array (do not mutate the input)."
            ),
            starter_code=(
                "function normalizeMessages(body) {\n"
                "  // TODO: implement\n"
                "}\n"
            ),
            entrypoint="normalizeMessages",
            tests=[
                {
                    "id": "t1",
                    "args": [{"model": "x", "messages": [{"role": "user"}]}],
                    "expected": {"model": "x", "messages": [{"role": "user"}]},
                },
                {
                    "id": "t2",
                    "args": [{"model": "x"}],
                    "expected": {"model": "x", "messages": []},
                },
                {
                    "id": "t3",
                    "args": [{"messages": "oops"}],
                    "raises": "Error",
                },
            ],
            explanation=(
                "Same pre-flight discipline as the gateway interceptor — validate "
                "before upstream calls."
            ),
        )
    )

    pool.append(
        _coding_challenge(
            qid="code_ch_quiz_status",
            prompt=(
                "**Coding challenge — Governance Quiz commit status.**\n\n"
                "Implement `quizCommitState(comprehensionPassed)` used when CI/dashboard "
                "updates the GitHub check:\n"
                "- If `comprehensionPassed` is strictly `true`, return `\"success\"`.\n"
                "- Otherwise return `\"pending\"`."
            ),
            starter_code=(
                "function quizCommitState(comprehensionPassed) {\n"
                "  // TODO: implement\n"
                "}\n"
            ),
            entrypoint="quizCommitState",
            tests=[
                {"id": "t1", "args": [True], "expected": "success"},
                {"id": "t2", "args": [False], "expected": "pending"},
                {"id": "t3", "args": [None], "expected": "pending"},
            ],
            explanation="CI opens the check as pending; a passed quiz flips it to success.",
        )
    )

    if any("ast" in r or "comprehension" in r for r in rels) or snippets:
        pool.append(
            _coding_challenge(
                qid="code_ch_max_nest",
                prompt=(
                    "**Coding challenge — AST nested-loop depth.**\n\n"
                    "Implement `maxNestDepth(depths)` where `depths` is an array of "
                    "integers (loop nesting at various points).\n"
                    "- Return the maximum value in the array.\n"
                    "- If the array is empty, return `0`.\n\n"
                    f"This PR’s governance AST rule fails when depth exceeds 2"
                    + (
                        f" — related files include `{snippets[0]['file']}`."
                        if snippets
                        else "."
                    )
                ),
                starter_code=(
                    "function maxNestDepth(depths) {\n"
                    "  // TODO: implement\n"
                    "}\n"
                ),
                entrypoint="maxNestDepth",
                tests=[
                    {"id": "t1", "args": [[1, 2, 3, 2]], "expected": 3},
                    {"id": "t2", "args": [[]], "expected": 0},
                    {"id": "t3", "args": [[1]], "expected": 1},
                    {"id": "t4", "args": [[2, 2, 1]], "expected": 2},
                ],
                explanation="AST001 blocks merge when nested loop depth > 2.",
            )
        )

    # Prefer challenges whose ids mention themes present in the PR; keep unique order
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _take(qid: str) -> None:
        for q in pool:
            if q["id"] == qid and qid not in seen:
                selected.append(q)
                seen.add(qid)
                return

    if any("github" in r for r in rels):
        _take("code_ch_parse_repo")
    if "quiz" in joined or "comprehension" in joined or "governance" in joined:
        _take("code_ch_quiz_score")
        _take("code_ch_quiz_status")
    if any("proxy" in r or "interceptor" in r or "gateway" in r for r in rels):
        _take("code_ch_normalize_messages")
    if snippets or any("ast" in r or "comprehension" in r for r in rels):
        _take("code_ch_max_nest")

    for q in pool:
        if len(selected) >= 2:
            break
        if q["id"] not in seen:
            selected.append(q)
            seen.add(q["id"])

    # Always at least 2; if pool somehow tiny, duplicate-safe fill already handled
    while len(selected) < 2 and pool:
        for q in pool:
            if q["id"] not in seen:
                selected.append(q)
                seen.add(q["id"])
            if len(selected) >= 2:
                break
        break

    # If PR is large, offer a third challenge when we have extras
    if len(seen) < len(pool) and len(selected) == 2:
        for q in pool:
            if q["id"] not in seen:
                selected.append(q)
                break

    assert len(selected) >= 2
    return selected


def _llm_enrich(pack: dict[str, Any], diff_text: str) -> dict[str, Any]:
    """Optionally ask an LLM to add beginner-friendly questions from the real diff."""
    api_key = os.getenv("GOVERNANCE_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key or not diff_text.strip():
        return pack

    base_url = os.getenv("GOVERNANCE_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("GOVERNANCE_LLM_MODEL", "gpt-4o-mini")
    system = """You help an absolute beginner engineer understand THIS PR before merging.
Return JSON only:
{
  "extra_glossary": [{"term":"...","definition":"..."}],
  "extra_questions": [{
    "id":"llm_...",
    "category":"what_changed|vocabulary|how_it_works|bigger_picture|dependencies|manual_tasks|functions|security",
    "prompt":"...",
    "choices":["...","...","...","..."],
    "answer_index":0,
    "explanation":"..."
  }],
  "plain_english_summary":"2-4 sentences: what this PR changed (basics first), then how it fits the wider project"
}
Hard rules:
- Focus mainly on BASIC facts of what happened in THIS diff (files, functions, behavior).
- Also teach how the change fits the wider Shadow AI Gateway / governance dashboard project.
- Produce 5-8 questions covering as many categories as possible (especially what_changed).
- Exactly 4 choices each. Distractors must be PLAUSIBLE near-misses from THIS codebase
  (other real subsystems: FastAPI proxy, interceptor, dashboard quiz, Upstash, governance CI).
- NEVER use joke/absurd options (moon, plane tickets, emoji counts, Discord, LeetCode dumps).
- Kind tone; define jargon in the question or explanation. Use real names from the diff.
"""
    guide_snip = {
        k: pack["study_guide"].get(k)
        for k in (
            "elevator_pitch",
            "bigger_picture",
            "glossary",
            "key_functions",
            "dependencies",
            "manual_dev_tasks",
            "security_notes",
            "files_touched",
            "areas",
            "what_changed",
        )
    }
    payload = {
        "model": model,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    "Diff to teach from:\n\n"
                    + diff_text[:50000]
                    + "\n\nStudy guide facts JSON:\n"
                    + json.dumps(guide_snip)[:10000]
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

    llm_questions: list[dict[str, Any]] = []
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
        # Reject absurd distractors if the model slips
        joined = " ".join(str(c).lower() for c in choices)
        if any(
            bad in joined
            for bad in ("plane ticket", "moon is full", "leetcode", "discord", "emoji")
        ):
            continue
        cat = str(raw.get("category") or "what_changed")
        llm_questions.append(
            _q(
                str(raw.get("id") or f"llm_{len(llm_questions)}"),
                cat,
                str(raw.get("prompt") or "What does this change do?"),
                [str(c) for c in choices],
                idx,
                str(raw.get("explanation") or "Review the study guide."),
                seed=hash(str(raw.get("id"))) & 0xFFFF,
            )
        )

    if llm_questions:
        coding = [q for q in pack["questions"] if q.get("question_type") == "coding"]
        deterministic_mc = [
            q for q in pack["questions"] if q.get("question_type") != "coding"
        ]
        # Prefer LLM (diff-aware) questions; fill remaining category gaps from deterministic
        covered = {q["category"] for q in llm_questions}
        fillers = [q for q in deterministic_mc if q["category"] not in covered]
        merged_mc = (llm_questions + fillers)[:8]
        pack["questions"] = merged_mc + coding
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
