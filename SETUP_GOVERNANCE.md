# What You Need To Do — AI Governance Gate

The seven-step suite is in the repo. **It will not protect `main` until you finish these setup steps.** Right now you only have Vercel deploy checks + Cursor Bugbot; those stay, and this gate is additive.

## Mental model (read this first)

| Thing | Where it runs | What you do with it |
|-------|---------------|---------------------|
| **Governance Steps 1–6** | GitHub Actions (`AI Code Guardrail` workflow) | Generates the study guide + quiz on every PR |
| **Step 7 Review Dashboard** | **Vercel** (`dashboard/` Next.js app) | Where you **read the guide and take the quiz** |
| Shadow AI Gateway (FastAPI) | Fly / Render — **not Vercel** | Unrelated to the quiz UI |

You cannot take the UI quiz from the Actions log alone. CI builds the quiz, then POSTs it to the dashboard. No dashboard URL → empty UI.

> **Important:** Your GitHub repo currently shows Vercel checks for `sellable-saas-template` / `sellable-saa-s-template`. Those are the **wrong** projects. Create a **new** Vercel project pointed at `dashboard/` (steps below).

---

## 1. Merge this PR (and the architecture ledger PR if still open)

Bring `governance/`, `.github/workflows/ai-guardrail.yml`, and `dashboard/` onto `main`.

## 2. Require the CI checks (the important ones)

GitHub → **Settings → Branches** → protect `main`:

1. Require a pull request before merging
2. Require status checks to pass → select **both**:
   - **`Governance Steps 1–6`** (automated suite)
   - **`Governance Quiz`** (you passed the dashboard quiz for this commit)
3. Optionally keep Vercel + Bugbot required as well

Until these are required, PRs can still merge without understanding the change.

**How `Governance Quiz` works:** CI sets the check to **pending** when the suite runs. After you pass the quiz (≥80%) on the dashboard, the dashboard flips that same check to **success** for the PR head SHA. A new push resets it to pending until you pass again.

For the dashboard to update the check, Vercel needs a GitHub token with **Commit statuses: Read and write** (fine-grained) or classic `repo` scope — set as `GITHUB_TOKEN`, `GH_MERGE_TOKEN`, or `GH_STATUS_TOKEN`.

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

## 4. Deploy the Step 7 dashboard to Vercel (so you can take quizzes)

### 4a. Create a secret you will reuse

Pick a long random string (password manager / `openssl rand -hex 32`). You will paste it in **three** places:

1. Vercel env → `GOVERNANCE_DASHBOARD_SECRET`
2. GitHub Actions secret → `GOVERNANCE_DASHBOARD_SECRET` (same value)
3. Browser “Unlock actions” prompt when you take the quiz

### 4b. Create a new Vercel project for the dashboard

1. Open [vercel.com/new](https://vercel.com/new)
2. **Import** `Alteoziel/Shadow-AI-Gateway` (your GitHub repo)
3. Project name: e.g. `shadow-ai-governance` (anything except the old sellable-saas templates)
4. **Root Directory** → click Edit → set to **`dashboard`** → Continue
5. Framework Preset must be **Next.js** (not Other / Vite / Create React App)
6. **Output Directory** must be **empty / default** — leave it blank.  
   Do **not** set it to `public` (that causes: `No Output Directory named "public" found`).
7. Do **not** deploy yet — first add env + Redis (next steps), or deploy then add and redeploy

If you already hit the `public` error: Project → **Settings → General → Build & Development Settings** → clear **Output Directory** → set Framework to **Next.js** → confirm **Root Directory** is `dashboard` → **Redeploy**.

### 4c. Add Upstash Redis (required on Vercel)

The quiz store cannot use a local JSON file on serverless (each request may hit a different machine). Use Upstash:

1. Vercel project → **Storage** → **Create** → **Upstash Redis** (Marketplace)
2. Connect it to this project — Vercel injects:
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`
3. Redeploy after connecting

### 4d. Set dashboard environment variables

Vercel project → **Settings → Environment Variables** (Production + Preview):

| Env | Value |
|-----|-------|
| `GOVERNANCE_DASHBOARD_SECRET` | The secret from 4a |
| `GOVERNANCE_REVIEWER_SECRET` | Optional; defaults to dashboard secret |
| `GITHUB_TOKEN` or `GH_MERGE_TOKEN` | Fine-grained PAT with `contents:write` + `pull-requests:write` (only needed for **Approve & Merge**) |
| `UPSTASH_REDIS_REST_URL` | Auto from Marketplace (verify present) |
| `UPSTASH_REDIS_REST_TOKEN` | Auto from Marketplace (verify present) |

Then **Deploy** (Deployments → Redeploy, or push a commit).

Copy your production URL, e.g. `https://shadow-ai-governance.vercel.app`.

### 4e. Wire GitHub Actions → dashboard

GitHub repo → **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `GOVERNANCE_DASHBOARD_URL` | Your **real** Production URL from Vercel (Domains), e.g. `https://shadow-ai-governance.vercel.app` — **not** the literal text `https://your-app.vercel.app`. No trailing slash. |
| `GOVERNANCE_DASHBOARD_SECRET` | **Same** string as the Vercel env var `GOVERNANCE_DASHBOARD_SECRET` |

Secret **names** are correct as repository secrets under Actions. Only the URL value must be the live domain after a successful deploy.

### 4f. Take a quiz (end-to-end)

1. Open (or create) a PR into `main`
2. Wait for the **Governance Steps 1–6** check to finish
3. Open your Vercel dashboard URL
4. You should see the PR review with status **quiz pending**
5. Click **Unlock actions** → paste the shared secret
6. Read the study guide → take the quiz (≥80%) → Approve / Merge unlocks

If the list is empty: CI could not POST. Check the latest **Governance Steps 1–6**
Actions log for `Dashboard post failed`. A **401** means
`GOVERNANCE_DASHBOARD_SECRET` in GitHub ≠ the Vercel env var (they must match
exactly). After fixing, re-run the workflow on an open PR.

Also confirm `GOVERNANCE_DASHBOARD_URL` is your live host with no trailing slash,
e.g. `https://shadow-ai-gateway.vercel.app`.

If the site returns **500 / Application error**: open `/api/health` on the same host. You should see JSON with `"ok": true`. Then check Deployment → Logs. Usual causes: Redis not linked to **Preview** (only Production), or an old deploy writing to a read-only path. Redeploy after connecting Upstash to both environments.

### Local alternative (no Vercel)

```bash
cd dashboard
npm install
cp .env.example .env.local
# set GOVERNANCE_DASHBOARD_SECRET=... and GOVERNANCE_ALLOW_INSECURE_DEV=true
npm run dev          # http://localhost:3000
```

Practice the quiz without the UI:

```bash
cd governance
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ai-guardrail quiz --root .. --skip-llm
```

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
   ├─ Vercel check (dashboard deploys, if linked correctly)
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
| Review dashboard | Vercel (+ Upstash Redis) | Quiz + human approve/merge UI |

Full detail: `architecture_and_roadmap.md` §0 and §11.
