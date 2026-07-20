# AI Governance Review Dashboard (Step 7)

Human review panel for Shadow AI Gateway pull requests. It receives reports from
the Python governance CLI (Steps 1–6), teaches the reviewer with the Step 6
study guide, grades the quiz, and can merge through GitHub's REST API.

**Step 6 comprehension quiz must be passed (>=80%) before Approve or Approve &
Merge unlock.** The API enforces this even if a button is bypassed.

## Local run

```bash
cd dashboard
npm install
cp .env.example .env.local
# edit .env.local
npm run dev
```

Open http://localhost:3000. The top "Deployment readiness" panel shows whether
ingest auth, reviewer auth, merge token, and the JSON store are configured.

## Build / start

Ledger §11.C deploy check:

```bash
cd dashboard
npm install
# Set GOVERNANCE_DASHBOARD_SECRET + GITHUB_TOKEN (merge rights)
npm run build && npm start
```

This dashboard is a normal Next.js app and **can** deploy on Vercel. The
streaming gateway proxy still must not deploy to Vercel.

## Environment

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `GOVERNANCE_DASHBOARD_SECRET` | Required in production and whenever `GOVERNANCE_DASHBOARD_URL` is set | Shared secret for GitHub Actions ingest to `POST /api/reviews`; CI must send `X-Governance-Secret` |
| `GOVERNANCE_REVIEWER_SECRET` | Optional | Separate browser unlock secret for quiz/approve/reject/merge; defaults to `GOVERNANCE_DASHBOARD_SECRET` |
| `GOVERNANCE_ALLOW_INSECURE_DEV` | Local only | Set `true` only for local demos without secrets; ignored in production |
| `GITHUB_TOKEN` or `GH_MERGE_TOKEN` | Required only for Approve & Merge | Fine-grained PAT or GitHub App token with `contents:write` + `pull-requests:write` |

If CI posts without the correct `X-Governance-Secret`, `/api/reviews` returns
HTTP 401 with a setup hint. Set the same `GOVERNANCE_DASHBOARD_SECRET` on the
dashboard host and in GitHub Actions.

## Reviewer unlock flow

1. Open the dashboard.
2. Click **Unlock actions**.
3. Paste `GOVERNANCE_REVIEWER_SECRET` or the dashboard secret.
4. The secret is stored only in this browser session's `sessionStorage`.
5. Use **Clear saved reviewer secret** if a quiz/action returns 401.

## API

- `GET /api/status` — safe deploy/auth/store status, no secret values
- `GET /api/reviews` — list reviews
- `POST /api/reviews` — ingest pipeline JSON with `X-Governance-Secret`
- `GET /api/reviews/:id` — fetch one review
- `POST /api/reviews/:id` — `{ "action": "submit_quiz" | "approve" | "reject" | "merge" }`

## Storage

The default store is JSON at `.data/reviews.json` for local and single-instance
dashboard deployments. Do not configure Supabase/Postgres for this Step 7
hardening pass; the Ledger reserves that migration for Phase 3.
