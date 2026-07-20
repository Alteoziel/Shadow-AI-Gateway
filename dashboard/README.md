# AI Governance Review Dashboard (Step 6)

Human review panel for Shadow AI Gateway pull requests. Receives reports from
the Python governance CLI (Steps 1–5) and can merge via GitHub’s REST API.

## Local run

```bash
cd dashboard
cp .env.example .env.local   # optional
npm install
npm run dev
```

Open http://localhost:3000

## Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOVERNANCE_DASHBOARD_SECRET` | Recommended in prod | Shared secret for CI → `/api/reviews` POSTs |
| `GITHUB_TOKEN` or `GH_MERGE_TOKEN` | Required for merge | PAT / fine-grained token with `contents:write` + `pull-requests:write` |

## API

- `GET /api/reviews` — list reviews
- `POST /api/reviews` — ingest pipeline JSON (header `X-Governance-Secret`)
- `POST /api/reviews/:id` — `{ "action": "approve" \| "reject" \| "merge" }`

## Deploy

This dashboard is a normal Next.js app and **can** deploy on Vercel (unlike the
streaming gateway proxy, which must stay on long-lived Docker hosts).
