# Research Findings

## Q1: How does the dashboard currently authenticate CI ingest requests and reviewer mutation requests?

### Findings

- `authorizeIngest` reads `GOVERNANCE_DASHBOARD_SECRET` and compares it to `X-Governance-Secret`; if no secret is configured, only non-production `GOVERNANCE_ALLOW_INSECURE_DEV=true` allows writes. `dashboard/src/lib/auth.ts:10-25`
- `authorizeReviewer` reads `GOVERNANCE_REVIEWER_SECRET` or falls back to `GOVERNANCE_DASHBOARD_SECRET`, then checks `X-Governance-Reviewer-Secret` or `X-Governance-Secret`. `dashboard/src/lib/auth.ts:27-39`
- `unauthorizedResponse` returns JSON with `error: "unauthorized"` plus a setup hint and HTTP 401. `dashboard/src/lib/auth.ts:41-53`
- `POST /api/reviews` rejects before parsing the body when ingest auth fails. `dashboard/src/app/api/reviews/route.ts:20-23`
- `POST /api/reviews/[id]` rejects before loading the review when reviewer auth fails. `dashboard/src/app/api/reviews/[id]/route.ts:33-36`

## Q2: How does the dashboard currently display reviewer unlock state, quiz status, and approve/merge locking?

### Findings

- The browser stores the reviewer secret in `sessionStorage` under `governance_reviewer_secret`. `dashboard/src/components/ReviewPanel.tsx:14-23`
- `ReviewerUnlock` shows either "Reviewer secret loaded" with a Clear button or "Unlock actions (enter reviewer secret)". `dashboard/src/components/ReviewPanel.tsx:152-187`
- `ComprehensionPanel` tells users that approve/merge stay locked when no quiz is attached. `dashboard/src/components/ReviewPanel.tsx:205-213`
- A passed quiz shows the score and states Step 7 approve/merge is unlocked, while merge still depends on the suite being green. `dashboard/src/components/ReviewPanel.tsx:216-230`
- `ReviewActions` disables Approve unless a comprehension pack exists and is passed, and disables Approve & Merge unless the quiz is passed and the suite passed. `dashboard/src/components/ReviewPanel.tsx:444-479`
- The API independently rejects approve/merge when the quiz is missing or not passed. `dashboard/src/app/api/reviews/[id]/route.ts:96-120`

## Q3: How does the dashboard ingest, persist, sanitize, and update review records?

### Findings

- The store creates `.data/reviews.json` under `process.cwd()` and writes a JSON array. `dashboard/src/lib/store.ts:97-115`
- `extractComprehension` reads the Step 6 pack from the `comprehension_gate` step metrics. `dashboard/src/lib/store.ts:117-124`
- `publicComprehension`, `sanitizeStepsForClient`, and `sanitizeReviewForClient` remove answer keys and explanations from client payloads. `dashboard/src/lib/store.ts:136-172`
- `gradeComprehension` calculates `score = correct / total`, defaults the pass threshold to `0.8`, and passes when `score >= threshold`. `dashboard/src/lib/store.ts:174-193`
- `upsertReview` resets comprehension status when the quiz fingerprint changes and preserves a previous pass only for the same quiz on the same commit. `dashboard/src/lib/store.ts:211-269`

## Q4: What deployment and environment variable instructions already exist for the dashboard in repository docs?

### Findings

- Ledger §11.C says to `cd dashboard`, `npm install`, set `GOVERNANCE_DASHBOARD_SECRET + GITHUB_TOKEN`, and run `npm run build && npm start` or deploy to Vercel. `architecture_and_roadmap.md:419-428`
- `SETUP_GOVERNANCE.md` says the dashboard host needs `GOVERNANCE_DASHBOARD_SECRET`, optional `GOVERNANCE_REVIEWER_SECRET`, local-only `GOVERNANCE_ALLOW_INSECURE_DEV`, and `GITHUB_TOKEN` or `GH_MERGE_TOKEN`. `SETUP_GOVERNANCE.md:42-59`
- `SETUP_GOVERNANCE.md` says the UI unlock flow is to click "Unlock actions" and paste the secret once per browser session. `SETUP_GOVERNANCE.md:60-68`
- `dashboard/README.md` documents local run commands, `GOVERNANCE_DASHBOARD_SECRET`, and `GITHUB_TOKEN` / `GH_MERGE_TOKEN`, but calls the dashboard secret only "Recommended in prod". `dashboard/README.md:8-35`
- `dashboard/.env.example` contains placeholder values for dashboard, reviewer, insecure dev, and merge tokens. `dashboard/.env.example:1-13`

## Q5: What repository guardrails constrain database work, Vercel usage, and the human-owned interceptor checkpoint?

### Findings

- The Ledger says dashboard storage starts as JSON under `.data/reviews.json`; Supabase Postgres is for Phase 3 and should not be introduced as a parallel store. `architecture_and_roadmap.md:73-75`
- The Ledger says Supabase PostgreSQL is the production database target for Phase 3 and not to invent a parallel primary store. `architecture_and_roadmap.md:360-361`
- The Ledger says the dashboard may use Vercel but the streaming gateway proxy may not. `architecture_and_roadmap.md:350-365`
- The Ledger says `app/proxy/interceptor.py` is Human Checkpoint #1, must retain `NotImplementedError`, and agents must not silently complete it. `architecture_and_roadmap.md:276-292`
- Root `README.md` repeats that `app/proxy/interceptor.py` remains human-owned and returns `501` until implemented. `README.md:35-41`
