# AI Governance Review Dashboard (Step 7)

Human review panel for Shadow AI Gateway pull requests. Receives reports from
the Python governance CLI (Steps 1–6) and can merge via GitHub’s REST API.

**Step 6 comprehension quiz must be passed (≥80%) before Approve / Merge unlock.**
Passing also sets the GitHub commit status **`Governance Quiz`** to success so
branch protection can block merges until you understand the change.

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
| `GOVERNANCE_SITE_PASSWORD` | **Recommended on public Vercel** | Browser password gate (`/login`); httpOnly cookie lasts **7 days** |
| `UPSTASH_REDIS_REST_URL` | **Yes on Vercel** | Durable quiz/review store |
| `UPSTASH_REDIS_REST_TOKEN` | **Yes on Vercel** | Durable quiz/review store |
| `GITHUB_TOKEN` / `GH_MERGE_TOKEN` / `GH_STATUS_TOKEN` | For **Governance Quiz** check + optional merge | Commit statuses write; add contents + PRs for merge |
| `GITHUB_REPOSITORY` | Optional | When set, merge/status only allows this `owner/name` |
| `GOVERNANCE_DASHBOARD_PUBLIC_URL` | Optional | Link target on the GitHub quiz check |

Locally, reviews stay in process memory (lost on restart). On Vercel, use Upstash
Redis (Marketplace → Storage) — required for durable quizzes across lambdas.
Never persists HTTP ingest payloads to disk (avoids CodeQL http-to-file alerts).

## API

- `GET /api/reviews` — list reviews (site password cookie, or machine secret header)
- `POST /api/reviews` — ingest pipeline JSON (header `X-Governance-Secret`)
- `POST /api/reviews/:id` — `{ "action": "submit_quiz" | "approve" | "reject" | "merge" }`
- `POST /api/auth/login` — `{ "password": "..." }` sets a 7-day httpOnly session cookie
- `POST /api/auth/logout` — clears the site session cookie

### Site password gate

Vercel Hobby **Standard Protection** does **not** lock production domains. Set
`GOVERNANCE_SITE_PASSWORD` so humans hit `/login` before seeing reviews. CI keeps
working via `X-Governance-Secret` without the browser cookie.

## Deploy on Vercel

1. Import this GitHub repo as a **new** Vercel project
2. Set **Root Directory** to `dashboard`
3. Framework = **Next.js**; leave **Output Directory blank** (never `public`)
4. Add Upstash Redis from the Storage / Marketplace tab
5. Set `GOVERNANCE_DASHBOARD_SECRET`, **`GOVERNANCE_SITE_PASSWORD`** (browser gate), and optional GitHub merge token
6. Deploy, then set GitHub Actions secrets:
   - `GOVERNANCE_DASHBOARD_URL` = your real Production URL (not a placeholder)
   - `GOVERNANCE_DASHBOARD_SECRET` = same secret as Vercel

`vercel.json` in this folder pins the framework to Next.js so Vercel does not
treat the app as a static `public/` site.

Full click-path: [`SETUP_GOVERNANCE.md`](../SETUP_GOVERNANCE.md) §4.
