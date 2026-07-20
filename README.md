# Shadow AI Guardrail Gateway

Enterprise security proxy that sits between corporate users and public LLMs (OpenAI / Anthropic) to intercept outbound traffic **pre-flight**.

> **Read first:** [`architecture_and_roadmap.md`](architecture_and_roadmap.md) — **The Ledger** — single source of truth for phases, checkpoints, and guardrails.

## Pre-merge gate (AI Governance Engine)

Before more gateway code ships, PRs are analyzed by a seven-step suite:

1. AST · 2. OWASP · 3. Fuzz · 4. Big-O · 5. Copyright · **6. Comprehension quiz** · 7. Human review / merge

| Component | Path |
|-----------|------|
| CLI (Steps 1–6) | [`governance/`](governance/) |
| GitHub Action | [`.github/workflows/ai-guardrail.yml`](.github/workflows/ai-guardrail.yml) |
| Review panel (Step 7) | [`dashboard/`](dashboard/) |
| Human setup checklist | Ledger **§11** + [`SETUP_GOVERNANCE.md`](SETUP_GOVERNANCE.md) |

```bash
cd governance && pip install -e ".[dev]" && ai-guardrail run --root ..
ai-guardrail quiz --root .. --skip-llm   # practice understanding the change
```

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
# Edit .env with your API keys

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Chat completion (returns `501` until Checkpoint #1 is filled):

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
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

See `.env.example` for a copy-paste template.

## Project layout

See **§7** in [The Ledger](architecture_and_roadmap.md) for the canonical repository tree and phase boundaries.
