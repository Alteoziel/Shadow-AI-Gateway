# Design Discussion

## Current State

- Ingest and reviewer mutations are protected by shared-secret route handler checks, with an insecure local escape hatch ignored in production. `dashboard/src/lib/auth.ts:10-39`
- Unauthorized API calls return a JSON error and a setup hint, but the dashboard UI has no persistent deploy/auth status panel for operators. `dashboard/src/lib/auth.ts:41-53`
- Reviewer unlock is session-only and currently shown as a small button or "secret loaded" text. `dashboard/src/components/ReviewPanel.tsx:152-187`
- Approve and merge are already locked in both UI and API unless Step 6 comprehension exists and passes. `dashboard/src/components/ReviewPanel.tsx:444-479`, `dashboard/src/app/api/reviews/[id]/route.ts:96-120`
- The store writes JSON to `.data/reviews.json`, and the Ledger says that remains the default until Phase 3 Supabase/Postgres. `dashboard/src/lib/store.ts:97-115`, `architecture_and_roadmap.md:73-75`
- Existing docs mention deployment, but `dashboard/README.md` understates that `GOVERNANCE_DASHBOARD_SECRET` is required when the dashboard URL is set. `dashboard/README.md:20-35`, `architecture_and_roadmap.md:419-428`

## Desired End State

The dashboard builds cleanly, has a visible auth/setup status, makes ingest authorization failures obvious to operators, keeps Step 6 quiz pass gating for approve/merge, and documents the exact Ledger §11.C deployment path. It remains a JSON-backed Next.js dashboard and does not touch the proxy interceptor or Phase 3 database work.

## Autonomous Decisions

1. **Auth unlock UX**: Use a persistent operational banner and clearer unlock controls instead of a new auth system. This matches the existing `sessionStorage` route-handler secret pattern and avoids middleware/proxy scope.
2. **Ingest failure visibility**: Add a GET-able dashboard status endpoint plus UI copy that shows whether ingest auth is configured and how CI should authenticate. This surfaces setup failures without weakening POST auth.
3. **Quiz gating**: Preserve current API enforcement and only improve explanatory UI/tests around it. The server already blocks approve/merge and is the right source of truth.
4. **Storage**: Keep hard-coded JSON store defaults and clarify that no `DATABASE_URL` is used in this step. This follows Ledger §0 and avoids Phase 3 creep.
5. **Deployment metadata**: Add dashboard-scoped `vercel.json` only if it helps Vercel find the app root and build command. It must not configure the streaming gateway.

## Design Decisions

1. **Operational status endpoint**: Add `GET /api/status` in `dashboard/src/app/api/status/route.ts` returning safe booleans for ingest secret, reviewer secret, insecure dev, JSON store path, and merge token presence.
2. **Visible status panel**: Render a dashboard setup panel on the home page so "CI ingest will 401 until `GOVERNANCE_DASHBOARD_SECRET` is set" is visible before the first POST fails.
3. **Reviewer unlock clarity**: Expand the existing unlock component with "locked/unlocked", which secret header is used, and a reset path for mistyped secrets.
4. **Docs alignment**: Update `dashboard/.env.example` and `dashboard/README.md` so they mirror Ledger §11.C and `SETUP_GOVERNANCE.md`.
5. **Deploy file**: Add `dashboard/vercel.json` with dashboard-local build/install/output settings.

## What We're NOT Doing

- No Supabase/Postgres schema, client, dependency, or `DATABASE_URL` path.
- No middleware/proxy/interceptor implementation.
- No change to `app/proxy/interceptor.py`.
- No weakening of the Step 6 ≥80% approve/merge gate.

## Open Risks

- The JSON store is appropriate for single-instance deployment, but multi-instance Vercel writes can diverge. This is an accepted Ledger trade-off until Phase 3.
- `next lint` may be unavailable because Next 15 removed the old CLI lint command; build is the mandatory deployability check for this task.
