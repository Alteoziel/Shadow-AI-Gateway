# What You Need To Do — AI Governance Gate

The seven-step suite is in the repo. **It will not protect `main` until you finish these setup steps.** Right now you only have Vercel deploy checks + Cursor Bugbot; those stay, and this gate is additive.

## 1. Merge this PR (and the architecture ledger PR if still open)

Bring `governance/`, `.github/workflows/ai-guardrail.yml`, and `dashboard/` onto `main`.

## 2. Require the CI check (the important one)

GitHub → **Settings → Branches** → protect `main`:

1. Require a pull request before merging
2. Require status checks to pass → select **`Governance Steps 1–6`**
3. Optionally keep Vercel + Bugbot required as well

Until this is on, the workflow is advisory only — PRs can still merge without it.

## 3. (Optional) Enable LLM enrichment (Steps 2 + 6)

Repo → **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `OPENAI_API_KEY` or `GOVERNANCE_LLM_API_KEY` | Your API key |

Optional variable: `GOVERNANCE_LLM_MODEL` (default `gpt-4o-mini`).

Without this:
- Step 2 still runs deterministic OWASP regex rules
- Step 6 still builds a beginner study guide + quiz from the code (no API needed)

With this: both get smarter, diff-aware questions/explanations.

## 4. Deploy the Step 7 dashboard

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
| `GOVERNANCE_DASHBOARD_SECRET` | **Required** shared secret for CI ingest + reviewer actions |
| `GOVERNANCE_REVIEWER_SECRET` | Optional override for quiz/approve/merge (defaults to dashboard secret) |
| `GOVERNANCE_ALLOW_INSECURE_DEV` | Local only (`true`); ignored in production |
| `GITHUB_TOKEN` or `GH_MERGE_TOKEN` | Fine-grained PAT with `contents:write` + `pull-requests:write` for **Approve & Merge** |

On the dashboard UI, click **Unlock actions** and paste the same secret once per browser session.

Then add Actions secrets:

| Secret | Value |
|--------|-------|
| `GOVERNANCE_DASHBOARD_URL` | e.g. `https://your-app.vercel.app` |
| `GOVERNANCE_DASHBOARD_SECRET` | Same string as the dashboard |

## Local dry-run anytime

```bash
cd governance
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ai-guardrail run --root .. --skip-llm
ai-guardrail quiz --root .. --skip-llm    # YOUR comprehension test (graded here / on dashboard, not inside Actions)
```

**Important:** The GitHub check `Governance Steps 1–6` proves the suite ran and generated a quiz. It does **not** mark that *you* passed. Pass locally with `ai-guardrail quiz`, or on the Step 7 dashboard after you deploy it.
## 6. How a PR flows after setup

```text
Open PR → main
   ├─ Vercel check (dashboard deploys, if linked)
   ├─ Cursor Bugbot (review comments)
   └─ AI Code Guardrail workflow
        ├─ Steps 1–5: automated analysis
        ├─ Step 6: generate beginner study guide + quiz
        ├─ PR summary + inline comments on failures
        └─ POST report → dashboard (if URL set)
             ├─ You read the study guide
             ├─ You take the quiz (≥80% required)
             └─ Step 7 unlocks → Approve / Reject / Approve & Merge
```

## Why Step 6 (comprehension) exists

You are new to this. AI will write a lot of the code. Clicking “looks good” without knowing what you’re looking at is how insecure or wrong systems ship — and how resume bullets become lies. The quiz teaches vocabulary, request flow, dependencies, manual tasks, and security implications for *this* change, then checks that it stuck.

## What not to confuse

| Thing | Hosts where? | Job |
|-------|--------------|-----|
| Shadow AI Gateway (FastAPI proxy) | Fly / Render / later AWS ECS — **not Vercel** | Intercept LLM traffic |
| Governance CLI | GitHub Actions + local | Analyze code + generate quiz |
| Review dashboard | Vercel or any Node host | Quiz + human approve/merge UI |

Full detail: `architecture_and_roadmap.md` §0 and §11.
