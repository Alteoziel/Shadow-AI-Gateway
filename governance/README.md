# AI Governance Engine (Steps 1–6)

Python CLI that gates pull requests before they hit `main`.

| Step | Module | What it checks |
|------|--------|----------------|
| 1 | `governance.steps.ast_guardrail` | Nested loops, `eval`/`exec`, complexity |
| 2 | `governance.steps.security_auditor` | OWASP regex rules + optional LLM review |
| 3 | `governance.steps.fuzz_chamber` | Boundary fuzz (null, `[]`, huge inputs) |
| 4 | `governance.steps.benchmark_engine` | Empirical Big-O timing curves |
| 5 | `governance.steps.copyright_filter` | Rabin-Karp + Levenshtein vs signature DB |
| 6 | `governance.steps.comprehension_gate` | Beginner study guide + understanding quiz |

Step 7 (human review dashboard) lives in `/dashboard` — merge stays locked until the Step 6 quiz is passed (≥80%).

## Install

```bash
cd governance
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run locally

```bash
ai-guardrail run --root .

# Practice the comprehension quiz interactively
ai-guardrail quiz --root . --skip-llm

ai-guardrail run --root . -f app/main.py -f app/proxy/interceptor.py
ai-guardrail run --root . --changed-only --base-ref origin/main
```

## Tests

```bash
pytest
```

## Optional env (CI / LLM)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` / `GOVERNANCE_LLM_API_KEY` | Step 2 LLM OWASP review + richer Step 6 questions |
| `GOVERNANCE_LLM_MODEL` | Model id (default `gpt-4o-mini`) |
| `GOVERNANCE_DASHBOARD_URL` | Step 7 ingest base URL |
| `GOVERNANCE_DASHBOARD_SECRET` | Shared secret for dashboard POSTs |
| `GITHUB_TOKEN` | PR comments / inline review comments |
