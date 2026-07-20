# What You Need To Do — AI Governance Gate

The six-step suite is in the repo. **It will not protect `main` until you finish these setup steps.** Right now you only have Vercel deploy checks + Cursor Bugbot; those stay, and this gate is additive.

## 1. Merge this PR (and the architecture ledger PR if still open)

Bring `governance/`, `.github/workflows/ai-guardrail.yml`, and `dashboard/` onto `main`.

## 2. Require the CI check (the important one)

GitHub → **Settings → Branches** → protect `main`:

1. Require a pull request before merging
2. Require status checks to pass → select **`Governance Steps 1–5`**
3. Optionally keep Vercel + Bugbot required as well

Until this is on, the workflow is advisory only — PRs can still merge without it.

## 3. (Optional) Enable LLM OWASP review (Step 2 upgrade)

Repo → **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `OPENAI_API_KEY` or `GOVERNANCE_LLM_API_KEY` | Your API key |

Optional variable: `GOVERNANCE_LLM_MODEL` (default `gpt-4o-mini`).

Without this, Step 2 still runs deterministic OWASP regex rules (secrets, SQLi, shell injection, pickle, etc.).

## 4. Deploy the Step 6 dashboard

```bash
cd dashboard
npm install
cp .env.example .env.local
# edit .env.local
npm run dev          # local
# or deploy to Vercel (OK for the dashboard — NOT for the streaming gateway)
```

Set on the dashboard host:

| Env | Purpose |
|-----|---------|
| `GOVERNANCE_DASHBOARD_SECRET` | Shared secret for CI ingest |
| `GITHUB_TOKEN` or `GH_MERGE_TOKEN` | Fine-grained PAT with `contents:write` + `pull-requests:write` for **Approve & Merge** |

Then add Actions secrets:

| Secret | Value |
|--------|-------|
| `GOVERNANCE_DASHBOARD_URL` | e.g. `https://your-app.vercel.app` |
| `GOVERNANCE_DASHBOARD_SECRET` | Same string as the dashboard |

## 5. Local dry-run anytime

```bash
cd governance
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ai-guardrail run --root .. --skip-llm
```

## 6. How a PR flows after setup

```text
Open PR → main
   ├─ Vercel check (dashboard deploys, if linked)
   ├─ Cursor Bugbot (review comments)
   └─ AI Code Guardrail workflow
        ├─ Steps 1–5 run on changed files
        ├─ PR summary + inline comments on failures
        └─ POST report → dashboard (if URL set)
             └─ You open dashboard → Approve / Reject / Approve & Merge
```

## What not to confuse

| Thing | Hosts where? | Job |
|-------|--------------|-----|
| Shadow AI Gateway (FastAPI proxy) | Fly / Render / later AWS ECS — **not Vercel** | Intercept LLM traffic |
| Governance CLI | GitHub Actions + local | Analyze code before merge |
| Review dashboard | Vercel or any Node host | Human approve/merge UI |

Full detail: `architecture_and_roadmap.md` §0 and §11.
