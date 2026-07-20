# Shadow AI Guardrail Gateway — Architecture & Roadmap

> **THE LEDGER** — Single source of truth for all agents, humans, and reviewers.
> Read this file before any developmental cycle. Keep it current when phase status changes.

**Last updated:** 2026-07-20  
**Current phase:** Phase 1 — Crawl (Asynchronous Proxy Setup)  
**Checkpoint status:** `blocked_on_human` — Checkpoint #1 (`app/proxy/interceptor.py`)  
**Pre-merge gate:** AI Governance Engine (Steps 1–7) — `in_progress` (comprehension gate added)

---

## 0. Pre-Merge Gate — AI Governance Engine (Steps 1–7)

> **Why this exists before more gateway code ships:** Today the only automated checks on PRs are Vercel deployment status and Cursor Bugbot. Those do **not** enforce AST structure, OWASP patterns, boundary fuzzing, Big-O profiling, copyright similarity, or — critically — that **you understand the change**. This suite is the missing merge gate for `main`.

### What was added (2026-07-20)

| Piece | Path | Role |
|-------|------|------|
| Steps 1–6 CLI | `governance/` | Local + CI analysis suite (`ai-guardrail`) |
| CI workflow | `.github/workflows/ai-guardrail.yml` | Runs on every PR → `main` |
| Step 6 Comprehension | `governance/.../comprehension_gate.py` | Beginner study guide + quiz (blocks merge until passed) |
| Step 7 dashboard | `dashboard/` | Human review + Approve/Merge via GitHub API |
| Signature DB | `governance/governance/signatures/known_snippets.json` | Copyright fingerprints |

### The seven steps

| # | Name | Implementation | Blocks merge? |
|---|------|----------------|---------------|
| 1 | AST Guardrail | `ast` node walk — nested loops, forbidden calls | Yes (error/critical) |
| 2 | Security Auditor | Deterministic OWASP regex + optional LLM diff review | Yes (error/critical) |
| 3 | Fuzz Chamber | Subprocess boundary injection (`null`, `[]`, huge payloads) | Yes (crashes) |
| 4 | Benchmark Engine | Empirical timing at N=10…10k → Big-O slope | Informational (extensible) |
| 5 | Copyright Filter | Rabin-Karp rolling hash + Levenshtein vs signatures | Yes (high similarity) |
| 6 | **Comprehension Gate** | Beginner study guide + quiz (vocab, flow, deps, manual tasks, security) | **Yes — dashboard requires ≥80% before Approve/Merge** |
| 7 | Human Review Panel | Next.js dashboard; merge webhook → GitHub REST | Human gate (after quiz) |

### Step 6 — why it exists (learning + safety)

You are very new to this stack. AI will write most of the boilerplate. **Rubber-stamping a PR you cannot explain is how secrets leak, bugs ship, and resume bullets become indefensible.**

Step 6 forces a pause:

1. **Study guide** — plain-English pitch, bigger picture, glossary, key functions, dependencies, manual tasks, security notes
2. **Quiz** — categories: vocabulary, how it works, architecture, dependencies, manual dev tasks, functions, security
3. **Pass bar** — ≥80% on the dashboard (or `ai-guardrail quiz` locally to practice)
4. **Only then** — Step 7 Approve / Approve & Merge unlocks

Tone: supportive teacher for a beginner, not a gotcha trap. Wrong answers show explanations so you learn.

### Plan adjustments (vs original 6-step deep dive)

1. **Python-first suite** (not a separate Node CLI) — matches the gateway stack and uses stdlib `ast` instead of Babel. The dashboard remains Next.js/TS as planned.
2. **Governance is a parallel track**, not a 5th gateway phase — it gates *all* phases including Phase 1 checkpoint work.
3. **LLM security review is optional** — deterministic OWASP rules always run (no secret required). Set `GOVERNANCE_LLM_API_KEY` / `OPENAI_API_KEY` to enable high-reasoning diff review.
4. **Fuzz sandbox starts as subprocess**; Docker isolation is a later hardening (same crawl→run pattern as the gateway).
5. **Dashboard storage starts as JSON file** (`.data/reviews.json`); migrate to Supabase Postgres when Phase 3 lands (same DB target — do not invent a parallel store).
6. **Vercel is OK for the dashboard only** — still forbidden for the streaming proxy (§8).
7. **Bugbot + Vercel remain** — governance is additive, not a replacement.
8. **Comprehension Gate inserted before human review** — original "Step 6 review panel" is now Step 7. Blind human review without understanding is treated as a first-class risk.

### Required human setup (for the gate to actually protect `main`)

See **§11 Setup Checklist** below. Require status checks:

- **`Governance Steps 1–6`**
- **`Enterprise Layers B–E`** (Dependabot/gitleaks/ruff/mypy/semgrep/tests/trivy/checkov — see [`ENTERPRISE_LAYERS.md`](ENTERPRISE_LAYERS.md))
- **`CodeQL (Layer C)`** after it appears once

Protect Main ruleset now requires those three checks + Code Owner review + dismiss stale reviews. Remaining operator steps (secret push protection, signed commits, second reviewer, etc.) are listed in [`ENTERPRISE_LAYERS.md`](ENTERPRISE_LAYERS.md).

---

## 0b. Enterprise Layers B–E (additive)

| Layer | Focus | Automations in repo |
|-------|-------|---------------------|
| B | Supply chain & secrets | Dependabot, checksummed Gitleaks, pip-audit, npm audit (high+ hard-fail) |
| C | Static analysis | Ruff, Mypy, Semgrep (custom + ERROR packs), CodeQL upload, CODEOWNERS |
| D | Product tests | API integration tests, egress/audit contracts, coverage ≥60% |
| E | Ship & runtime | `EgressCheckedAsyncClient`, audit DDL, non-root Docker→Trivy CRITICAL+HIGH + SBOM, Terraform+Checkov |

Details: [`ENTERPRISE_LAYERS.md`](ENTERPRISE_LAYERS.md).

---

## 1. Executive Context

We are building an **enterprise security proxy** that sits between corporate users and public LLMs (OpenAI / Anthropic) to prevent data leaks **pre-flight**. The gateway:

1. Intercepts outbound LLM traffic before it leaves the private network
2. Sanitizes prompts (Phase 2+) and enforces access rules
3. Tracks token consumption, errors, and risk metrics (Phase 3+)
4. Logs audit trails for compliance and operational risk management
5. Runs as a long-lived async service (Docker on Fly.io / Render / later AWS ECS) — **not** on Vercel serverless (streaming timeout risk)

### Human-in-the-Loop & Resume Constraint

This is a 12-month portfolio project. AI agents do ~90% of boilerplate and heavy lifting. The human Engineering Manager **must hands-on engineer the core logic of each pillar at least once or twice**, so every architectural choice and operational mechanism is resume-defensible.

By project end, the human must truthfully claim:

1. **Developed an asynchronous enterprise API proxy** handling outbound LLM traffic, reducing data-exposure risks by intercepting prompts pre-flight.
2. **Engineered a localized Python data-scrubbing pipeline** using NLP tokenization to automatically redact PII with sub-100ms latency.
3. **Integrated a PostgreSQL database layer** to securely track token consumption metrics, error tracking, and risk-management audit trails.
4. **Packaged application using Docker** and built infrastructure-as-code (Terraform) deployment pipelines to securely host the gateway within a private cloud network.

---

## 2. Agent Hierarchy (Chain of Command)

| Role | Model | When to invoke |
|------|-------|----------------|
| **THE BRAIN** | Opus 4.8 | Extremely sparingly. High-level architectural impasses only. Do **not** invoke unless explicitly told. |
| **SENIOR ENGINEER** | Grok 4.5 | Architect, workflow designer, reviewer. Directs building; not the primary bulk code doer. |
| **THE DOER / ACHIEVER** | Composer 2.5 / Auto 2.5 | Bulk file generation, boilerplate, configurations, baseline tests, refactoring. |
| **THE SECURITY CHIEF** | GPT-5.6 Sol | Extreme edge cases only: data scrubbing perfection, pre-flight tokenization, cryptographic verification, exhaustive security test coverage. |

**Default cycle:** Grok designs → Composer builds → Grok reviews → Human fills checkpoint → validation scripts run.

---

## 3. Four-Phase Timeline & Progression Audit

Status vocabulary: `not_started` | `in_progress` | `blocked_on_human` | `complete`

### Phase 1: The Crawl Phase (Months 1–3) — Asynchronous Proxy Setup

| Field | Value |
|-------|-------|
| **Status** | `in_progress` |
| **Checkpoint status** | `blocked_on_human` |
| **Checkpoint file** | `app/proxy/interceptor.py` |
| **Owner (checkpoint)** | Human |

**What we build:** A FastAPI Python service that accepts a text prompt, forwards it asynchronously to OpenAI or Anthropic, handles streaming responses, and passes the answer back.

**What the human learns:** Web requests, `async`/`await`, API routing, HTTP status codes, environment variables.

**Human checkpoint:** Intercepting the raw outbound client request payload **pre-flight** — implement `intercept_outbound_request(...)` before any upstream provider call.

**Phase 1 technical contract:**

| Item | Spec |
|------|------|
| Runtime | Python 3.12 |
| Framework | FastAPI + Uvicorn |
| HTTP client | `httpx` (async streaming) |
| Config | `pydantic-settings` via env |
| Health | `GET /health` |
| Proxy | `POST /v1/chat/completions` (stream + non-stream) |
| Providers | OpenAI + Anthropic (request or env default) |
| Hosting stubs | `Dockerfile`, `fly.toml`, `render.yaml`, `docker-compose.yml` |
| Out of scope | Scrubbing (Phase 2), DB (Phase 3), Terraform/AWS (Phase 4) |

**Env vars (Phase 1):**

- `OPENAI_API_KEY` — OpenAI upstream key
- `ANTHROPIC_API_KEY` — Anthropic upstream key
- `DEFAULT_PROVIDER` — `openai` \| `anthropic` (default: `openai`)
- `GATEWAY_HOST` / `GATEWAY_PORT` — bind address (default `0.0.0.0:8000`)
- `LOG_LEVEL` — logging verbosity

---

### Phase 2: The Walk Phase (Months 4–6) — Local AI & Data Manipulation

| Field | Value |
|-------|-------|
| **Status** | `not_started` |
| **Checkpoint status** | `not_started` |
| **Checkpoint file** | TBD — core string substitution / regex-NLP scrubbing loop |
| **Owner (checkpoint)** | Human |

**What we build:** Pre-forward inspection: string flags (API keys, credit cards) + lightweight local NLP (spaCy or high-performance regex) to redact names/corporate terms as tokens like `[REDACTED_NAME]`. **Latency budget: sub-100ms.**

**What the human learns:** Data scrubbing, string manipulation, tokenization, local text pipelines.

**Human checkpoint:** The core string substitution / regex-NLP scrubbing array loop.

---

### Phase 3: The Run Phase (Months 7–9) — Database & Audit Logs

| Field | Value |
|-------|-------|
| **Status** | `not_started` |
| **Checkpoint status** | `not_started` |
| **Checkpoint file** | TBD — SQL/ORM insert + analytics schema |
| **Owner (checkpoint)** | Human |

**What we build:** Supabase PostgreSQL. On every employee prompt, asynchronously log timestamp, user ID, token counts, and whether sensitive data leaks were intercepted.

**What the human learns:** SQL schemas, async connection pooling, data relationships, operational risk metrics.

**Human checkpoint:** Writing the raw SQL or ORM model insertion statement and constructing the analytics schema.

---

### Phase 4: The Cloud Phase (Months 10–12) — Infrastructure & DevOps

| Field | Value |
|-------|-------|
| **Status** | `not_started` |
| **Checkpoint status** | `not_started` |
| **Checkpoint file** | TBD — core `Dockerfile` polish + Terraform `main.tf` resources |
| **Owner (checkpoint)** | Human |

**What we build:** Production `Dockerfile` packaging + Terraform (`main.tf`) modeling the container in an AWS ECS / VPC private cloud network. (Phase 1 already ships staging stubs for Fly/Render.)

**What the human learns:** Containerization, cloud networking, private subnets, infrastructure-as-code.

**Human checkpoint:** Writing the core `Dockerfile` build instructions and defining the basic Terraform resources block.

---

## 4. Progression Audit Table

| Phase | Name | Checkpoint file | Checkpoint owner | Phase status | Checkpoint status |
|-------|------|-----------------|------------------|--------------|-------------------|
| 1 | Crawl — Async Proxy | `app/proxy/interceptor.py` | Human | `in_progress` | `blocked_on_human` |
| 2 | Walk — Scrubbing | TBD | Human | `not_started` | `not_started` |
| 3 | Run — Postgres Audit | TBD | Human | `not_started` | `not_started` |
| 4 | Cloud — Docker + Terraform | TBD | Human | `not_started` | `not_started` |

---

## 5. Operational Protocol (Every Developmental Cycle)

1. **Design & Plan (Grok 4.5)** — Map file modifications. Define contracts, constraints, and the human checkpoint boundary.
2. **Boilerplate (Composer / Auto 2.5)** — Generate structural code, configs, provider adapters, baseline tests. **Never** auto-complete human checkpoint implementations.
3. **Establish Learning Checkpoint** — Before a core feature block is finished, inject a clear:

   ```text
   TODO: Human Hands-On Implementation
   ```

   block in the designated file.
4. **Provide the Cheat Sheet** — Accompany the checkpoint with a concise **3-bullet** conceptual breakdown of *why* the underlying engineering concept works.
5. **Human Implements** — Engineering Manager fills the checkpoint.
6. **Security & Latency Validation** — After human completion, run validation scripts for structural security and (from Phase 2 onward) the sub-100ms processing budget.

---

## 6. Human Checkpoint #1 (Active)

**File:** `app/proxy/interceptor.py`  
**Function:** `intercept_outbound_request(...)`  
**Status:** `blocked_on_human`

### Cheat sheet (why this works)

1. **Pre-flight** means inspect/normalize the outbound payload **before** any bytes hit OpenAI/Anthropic — this is the choke point for later scrubbing and audit.
2. **`async def`** keeps the event loop free to serve other requests while awaiting I/O; the gateway must not block on a single upstream call.
3. Return a **normalized internal request** that provider adapters can stream against; raise `HTTPException(4xx)` on invalid input and never call providers on bad payloads.

### Scope rules for Checkpoint #1

- DO: validate required fields (`model`, `messages`), attach `correlation_id` / `received_at`, return the upstream-ready payload.
- DO NOT: implement scrubbing (Phase 2).
- DO NOT: write DB inserts (Phase 3).
- DO NOT: have agents silently complete this function — leave `NotImplementedError` until the human fills it.

**Call site:** `app/api/v1/chat.py` must always invoke `intercept_outbound_request` before provider streaming.

---

## 7. Target Repository Layout

```text
/
├── architecture_and_roadmap.md          # THIS FILE — The Ledger
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml                       # Gateway (Phase 1+)
├── Dockerfile
├── fly.toml
├── render.yaml
├── docker-compose.yml
├── .github/workflows/
│   ├── ai-guardrail.yml                 # Pre-merge governance CI
│   └── enterprise-hygiene.yml           # Layers B–E (supply chain → ship)
├── .github/dependabot.yml               # Layer B
├── .github/CODEOWNERS                   # Layer C
├── app/                                 # Gateway service
│   ├── main.py
│   ├── config.py
│   ├── api/...
│   ├── proxy/
│   │   ├── interceptor.py               # ★ HUMAN CHECKPOINT #1
│   │   └── providers/...
│   ├── security/                        # Layer E egress + audit scaffold
│   └── models/...
├── infra/terraform/                     # Layer E IaC stub (+ Checkov)
├── tests/                               # Gateway tests (Layer D)
├── governance/                          # Steps 1–6 (Python CLI)
│   ├── pyproject.toml
│   ├── README.md
│   ├── governance/
│   │   ├── cli.py
│   │   ├── pipeline.py
│   │   ├── models.py
│   │   ├── reporters/
│   │   ├── signatures/known_snippets.json
│   │   └── steps/
│   │       ├── ast_guardrail.py         # Step 1
│   │       ├── security_auditor.py      # Step 2
│   │       ├── fuzz_chamber.py          # Step 3
│   │       ├── benchmark_engine.py      # Step 4
│   │       ├── copyright_filter.py      # Step 5
│   │       └── comprehension_gate.py    # Step 6 (quiz)
│   └── tests/
└── dashboard/                           # Step 7 (Next.js review panel)
    ├── package.json
    ├── README.md
    └── src/app/...
```

---

## 8. Non-Negotiable Guardrails

1. **No Vercel for the streaming proxy** — use Docker on Fly.io, Render, or (Phase 4) AWS ECS for long-lived async streaming.
2. **Sub-100ms scrub budget** applies from Phase 2 onward; measure and enforce with validation scripts.
3. **Never auto-complete human checkpoint blocks** — agents scaffold, document, and test contracts only.
4. **Secrets only via environment variables** — never commit API keys or `.env` files.
5. **The Ledger stays current** — update phase/checkpoint status in this file whenever status changes.
6. **Supabase PostgreSQL** is the production database target (Phase 3); do not invent a parallel primary store.
7. **Bugbot** is integrated for GitHub issue tracking; treat review findings as first-class work items.
8. **Opus 4.8 and GPT-5.6 Sol** are restricted roles — do not invoke without explicit instruction.
9. **No merge to `main` without the AI Guardrail check** once branch protection is enabled (§11). Agents must not disable or skip the workflow to land green builds.
10. **Dashboard may use Vercel; the streaming gateway may not.**

---

## 9. Resume Defense Map

| Resume claim | Phase | Human-owned artifact |
|--------------|-------|----------------------|
| Async enterprise API proxy / pre-flight intercept | 1 | `app/proxy/interceptor.py` |
| Localized PII scrubbing pipeline (&lt;100ms) | 2 | Scrubbing loop (TBD path) |
| PostgreSQL metrics & audit trails | 3 | Schema + insert path (TBD) |
| Docker + Terraform private cloud hosting | 4 | `Dockerfile` + `infra/terraform/main.tf` (stub landed; expand in Phase 4) |
| Egress allowlist / audit trail readiness | 1→3 | `app/security/egress.py`, `app/security/audit.py` |

---

## 10. Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-07-19 | Initial Ledger created; Phase 1 scaffold kicked off; Checkpoint #1 armed | Senior Engineer (Grok 4.5) |
| 2026-07-20 | Added §0 Pre-Merge Gate; scaffolded Steps 1–6 (`governance/`, CI workflow, `dashboard/`); §11 setup checklist | Senior Engineer (Grok 4.5) |
| 2026-07-20 | Inserted Step 6 Comprehension Gate (beginner quiz); human review panel becomes Step 7; merge locked until ≥80% | Senior Engineer (Grok 4.5) |
| 2026-07-20 | Landed Enterprise Layers B–E (Dependabot, Gitleaks, Ruff/Mypy/Semgrep/CodeQL, coverage floor, egress/audit, Trivy, Terraform+Checkov) | Senior Engineer (Grok 4.5) |
| 2026-07-20 | Hardened Layers B–E: SHA-pinned Actions, checksummed Gitleaks, Semgrep packs hard-fail, Trivy CRITICAL+HIGH + SBOM, CodeQL upload, `EgressCheckedAsyncClient`, non-root image, coverage ≥60% | Senior Engineer (Grok 4.5) |
| 2026-07-20 | Operator: Dependabot + Code scanning enabled; Protect Main tightened (strict checks, last-push approval, signed commits); CodeQL `upload: true` | Human + Senior Engineer |

---

## 11. Setup Checklist — Make the Governance Gate Enforceable

Without these steps, the suite runs in CI but GitHub will still allow merges on green Vercel/Bugbot alone.

### A. Repository secrets & variables (GitHub → Settings → Secrets)

| Secret / Var | Required? | Purpose |
|--------------|-----------|---------|
| _(none for core Steps 1,3,4,5)_ | — | Deterministic checks need no secrets |
| `OPENAI_API_KEY` or `GOVERNANCE_LLM_API_KEY` | Optional | Enables Step 2 LLM OWASP review of the PR diff |
| `GOVERNANCE_DASHBOARD_URL` | Optional until dashboard is live | e.g. `https://your-dashboard.vercel.app` |
| `GOVERNANCE_DASHBOARD_SECRET` | Required if dashboard URL set | Must match dashboard env |
| `GOVERNANCE_LLM_MODEL` (variable) | Optional | Defaults to `gpt-4o-mini` |

`GITHUB_TOKEN` is provided automatically by Actions for PR comments.

### B. Branch protection on `main` (critical)

Prefer the **Protect Main** ruleset (already active). It requires:

1. Pull request before merging
2. Status checks: **`Governance Steps 1–6`**, **`Enterprise Layers B–E`**, **`CodeQL (Layer C)`**
3. **Require review from Code Owners**
4. **Dismiss stale reviews** on new pushes
5. **Require approval of the most recent reviewable push**
6. **Branches up to date** before merging
7. **Signed commits**
8. CodeQL code-scanning gate + Preview deployment

Still optional (see [`ENTERPRISE_LAYERS.md`](ENTERPRISE_LAYERS.md)): secret scanning + push protection (confirm on), second CODEOWNER when you have a teammate, governance dashboard deploy. **Dependabot alerts/security updates** and **Code scanning** are enabled.

**Also enforce comprehension in practice:** even with CI green, use the dashboard’s Step 6 quiz before merge — Approve & Merge stays locked until you pass (≥80%).

### C. Deploy the Step 7 dashboard

```bash
cd dashboard
npm install
# Set GOVERNANCE_DASHBOARD_SECRET + GITHUB_TOKEN (merge rights)
npm run build && npm start
# or: deploy to Vercel and set the same env vars in the project
```

Create a fine-grained PAT / GitHub App token with `contents: write` + `pull-requests: write` on this repo for the **Approve & Merge** button (`GITHUB_TOKEN` / `GH_MERGE_TOKEN` on the dashboard host).

### D. Local dry-run before pushing

```bash
cd governance && pip install -e ".[dev]" && pytest
ai-guardrail run --root .. --skip-llm
ai-guardrail quiz --root .. --skip-llm   # practice Step 6 locally
```

### E. What you still do manually (resume-defensible CS)

The suite is implemented end-to-end so CI works Day 1. Deepen ownership by extending:

1. **AST** — add project-specific forbidden patterns (e.g. disallow sync `httpx` in `app/`)
2. **Fuzz** — target real gateway helpers once Checkpoint #1 lands
3. **Benchmark** — wire per-PR function injection instead of calibration profiles only
4. **Copyright** — grow `known_snippets.json` with frameworks you must not paste
5. **Comprehension** — add domain questions as you learn new phases (scrubbing, SQL, Terraform)
6. **Dashboard** — swap `.data/reviews.json` for Supabase when Phase 3 starts

### F. Relationship to Bugbot & Vercel

| Check | What it catches | What it misses |
|-------|-----------------|----------------|
| Vercel | Dashboard deploy health | Gateway streaming safety, AST, OWASP, fuzz, understanding |
| Bugbot | Reviewer-style code critique | Deterministic policy + forcing *you* to understand |
| **AI Guardrail** | Structural / security / fuzz / copyright / **comprehension quiz** | Product UX polish of the dashboard |
