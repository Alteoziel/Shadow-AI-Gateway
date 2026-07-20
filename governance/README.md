# AI Governance Engine (Steps 1–5)

Python CLI that gates pull requests before they hit `main`.

| Step | Module | What it checks |
|------|--------|----------------|
| 1 | `governance.steps.ast_guardrail` | Nested loops, `eval`/`exec`, complexity |
| 2 | `governance.steps.security_auditor` | OWASP regex rules + optional LLM review |
| 3 | `governance.steps.fuzz_chamber` | Boundary fuzz (null, `[]`, huge inputs) |
| 4 | `governance.steps.benchmark_engine` | Empirical Big-O timing curves |
| 5 | `governance.steps.copyright_filter` | Rabin-Karp + Levenshtein vs signature DB |

Step 6 (human review dashboard) lives in `/dashboard`.

## Install

```bash
cd governance
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run locally

```bash
# From repo root (recommended)
ai-guardrail run --root .

# Specific files
ai-guardrail run --root . -f app/main.py -f app/proxy/interceptor.py

# Changed files only
ai-guardrail run --root . --changed-only --base-ref origin/main
```

## Tests

```bash
pytest
```

## Optional env (CI / LLM auditor)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` / `GOVERNANCE_LLM_API_KEY` | Enable Step 2 LLM OWASP review |
| `GOVERNANCE_LLM_MODEL` | Model id (default `gpt-4o-mini`) |
| `GOVERNANCE_DASHBOARD_URL` | Step 6 ingest base URL |
| `GOVERNANCE_DASHBOARD_SECRET` | Shared secret for dashboard POSTs |
| `GITHUB_TOKEN` | PR comments / inline review comments |
