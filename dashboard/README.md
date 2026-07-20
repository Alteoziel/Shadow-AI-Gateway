# AI Governance Review Dashboard (Step 7)

Human review panel for Shadow AI Gateway pull requests. Receives reports from
the Python governance CLI (Steps 1–6) and can merge via GitHub’s REST API.

**Step 6 comprehension quiz must be passed (≥80%) before Approve / Merge unlock.**

## Local run

```bash
cd dashboard
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

## Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOVERNANCE_DASHBOARD_SECRET` | Recommended in prod | Shared secret for CI → `/api/reviews` POSTs |
| `GITHUB_TOKEN` or `GH_MERGE_TOKEN` | Required for merge | PAT with `contents:write` + `pull-requests:write` |

## API

- `GET /api/reviews` — list reviews
- `POST /api/reviews` — ingest pipeline JSON (header `X-Governance-Secret`)
- `POST /api/reviews/:id` — `{ "action": "submit_quiz" | "approve" | "reject" | "merge" }`

## Deploy

This dashboard is a normal Next.js app and **can** deploy on Vercel (unlike the
streaming gateway proxy, which must stay on long-lived Docker hosts).
