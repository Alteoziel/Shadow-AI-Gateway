# Shadow AI Guardrail Gateway

Enterprise security proxy that sits between corporate users and public LLMs (OpenAI / Anthropic) to intercept outbound traffic **pre-flight**.

> **Read first:** [`architecture_and_roadmap.md`](architecture_and_roadmap.md) — **The Ledger** — phases, checkpoints, guardrails.
> **Task process:** [`.cursor/qrspi/`](.cursor/qrspi/) — mandatory QRSPI (see `AUTONOMOUS_MODE.md` + `CONTEXT_ISOLATION.md`).
> **Security hardening:** human-only steps (secrets, Protect Main, FOSSA/Snyk, deploy keys) → [`SECURITY_OPERATOR_CHECKLIST.md`](SECURITY_OPERATOR_CHECKLIST.md).

## Pre-merge gate (AI Governance Engine)

Before more gateway code ships, PRs are analyzed by a seven-step suite:

1. AST · 2. OWASP · 3. Fuzz · 4. Big-O · 5. Copyright · **6. Comprehension quiz** · 7. Human review / merge

| Component | Path |
|-----------|------|
| CLI (Steps 1–6) | [`governance/`](governance/) |
| GitHub Action | [`.github/workflows/ai-guardrail.yml`](.github/workflows/ai-guardrail.yml) — check name **`Governance Steps 1–6`** |
| Review panel (Step 7) | [`dashboard/`](dashboard/) |
| **Enterprise Layers B–E** | [`ENTERPRISE_LAYERS.md`](ENTERPRISE_LAYERS.md) + [`.github/workflows/enterprise-hygiene.yml`](.github/workflows/enterprise-hygiene.yml) |
| Human setup checklist | Ledger **§11** + [`SETUP_GOVERNANCE.md`](SETUP_GOVERNANCE.md) |

```bash
cd governance && pip install -e ".[dev]" && ai-guardrail run --root ..
ai-guardrail quiz --root .. --skip-llm   # YOUR understanding test (not graded inside Actions)
```

**Actions vs your quiz:** CI generates the quiz and must stay green. You take the quiz locally (`ai-guardrail quiz`) or on the dashboard after it’s deployed — that’s how *you* prove you understand the PR.
Require status checks on `main`: **`Governance Steps 1–6`**, **`Enterprise Layers B–E`**, and **`CodeQL (Layer C)`**. Operator checklist: [`ENTERPRISE_LAYERS.md`](ENTERPRISE_LAYERS.md).

## Phase 1 status

- FastAPI async proxy with OpenAI + Anthropic provider adapters
- Streaming and non-streaming `POST /v1/chat/completions`
- **Human Checkpoint #1:** `app/proxy/interceptor.py` — returns `501` until implemented
- Governance suite + CI + review dashboard scaffolded (see Ledger §0)

## Quickstart (local)

### Prerequisites

- Python 3.12+
- API keys for OpenAI and/or Anthropic

### Setup

```bash
cp .env.example .env
# Edit .env — set OPENAI/ANTHROPIC keys AND a long random GATEWAY_API_KEY

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# Or (preferred, frozen): curl -LsSf https://astral.sh/uv/install.sh | sh && uv sync --frozen --extra dev
```

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Chat completion (requires gateway API key):

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello"}]}'
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Service listens on port `8000` (override with `GATEWAY_PORT` in `.env`).

## Deployment stubs

| Target | Config |
|--------|--------|
| Fly.io | `fly.toml` — app name `shadow-ai-gateway` |
| Render | `render.yaml` — web service from `Dockerfile` |

Set secrets (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) in the platform dashboard — never commit them.

## Tests

```bash
pytest
```

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI upstream API key | — |
| `ANTHROPIC_API_KEY` | Anthropic upstream API key | — |
| `DEFAULT_PROVIDER` | `openai` or `anthropic` | `openai` |
| `GATEWAY_HOST` | Bind host | `0.0.0.0` |
| `GATEWAY_PORT` | Bind port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `GATEWAY_API_KEY` | Bearer / X-API-Key required for `/v1/*` | — (required) |
| `GATEWAY_API_KEYS` | Optional comma-separated extra keys | — |
| `GATEWAY_RATE_LIMIT_PER_MINUTE` | Per-key sliding window limit (≤0 falls back to 60) | `60` |
| `GATEWAY_RATE_LIMIT_DISABLED` | Set `true` to disable rate limiting | unset |

See `.env.example` for a copy-paste template.

**Security hardening:** full operator click-path checklist → [`SECURITY_OPERATOR_CHECKLIST.md`](SECURITY_OPERATOR_CHECKLIST.md).

## Project layout

See **§7** in [The Ledger](architecture_and_roadmap.md) for the canonical repository tree and phase boundaries.
