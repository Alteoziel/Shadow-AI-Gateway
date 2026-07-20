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
| `GOVERNANCE_DASHBOARD_SECRET` | Yes in prod | Shared secret for CI → `/api/reviews` POSTs |
| `UPSTASH_REDIS_REST_URL` | **Yes on Vercel** | Durable quiz/review store |
| `UPSTASH_REDIS_REST_TOKEN` | **Yes on Vercel** | Durable quiz/review store |
| `GITHUB_TOKEN` or `GH_MERGE_TOKEN` | For merge | PAT with `contents:write` + `pull-requests:write` |
| `GITHUB_REPOSITORY` | Optional | When set, merge only allows this `owner/name` |

Locally, reviews stay in process memory (lost on restart). On Vercel, use Upstash
Redis (Marketplace → Storage) — required for durable quizzes across lambdas.
Never persists HTTP ingest payloads to disk (avoids CodeQL http-to-file alerts).

## API

- `GET /api/reviews` — list reviews
- `POST /api/reviews` — ingest pipeline JSON (header `X-Governance-Secret`)
- `POST /api/reviews/:id` — `{ "action": "submit_quiz" | "approve" | "reject" | "merge" }`

## Deploy on Vercel

1. Import this GitHub repo as a **new** Vercel project
2. Set **Root Directory** to `dashboard`
3. Framework = **Next.js**; leave **Output Directory blank** (never `public`)
4. Add Upstash Redis from the Storage / Marketplace tab
5. Set `GOVERNANCE_DASHBOARD_SECRET` (and optional GitHub merge token)
6. Deploy, then set GitHub Actions secrets:
   - `GOVERNANCE_DASHBOARD_URL` = your real Production URL (not a placeholder)
   - `GOVERNANCE_DASHBOARD_SECRET` = same secret as Vercel

`vercel.json` in this folder pins the framework to Next.js so Vercel does not
treat the app as a static `public/` site.

Full click-path: [`SETUP_GOVERNANCE.md`](../SETUP_GOVERNANCE.md) §4.
