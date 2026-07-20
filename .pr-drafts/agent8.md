# Harden Step 7 dashboard deployability

## Summary

This hardens the Step 7 dashboard deployment path without moving into Phase 3 DB work or touching the human-owned interceptor. It adds visible auth/setup status, makes CI ingest auth failures diagnosable, preserves the Step 6 quiz gate for approve/merge, and aligns dashboard docs/env examples with Ledger §11.C.

## Design Decisions

- Keep route-handler shared-secret auth; do not add middleware/proxy/interceptor scope.
- Expose only safe booleans and labels in `/api/status`; never return secret values.
- Keep `.data/reviews.json` as the default store; no Supabase/Postgres client or env path.
- Preserve API-side approve/merge enforcement so UI bypasses still fail until the quiz is passed.

## Changes

- Added `dashboardAuthStatus()` and `GET /api/status`.
- Added a deployment readiness panel to the dashboard home page.
- Clarified reviewer unlock/clear flow for browser-session secrets.
- Updated `dashboard/.env.example` and `dashboard/README.md` to match Ledger §11.C.
- Added dashboard-scoped `dashboard/vercel.json`.
- Added QRSPI artifacts under `thoughts/qrspi/2026-07-20-dashboard-ops-harden/`.

## How to Verify

- `cd dashboard && npm run build`
- Built dashboard smoke:
  - `GET /api/status` returns safe auth/store status.
  - unauthenticated `POST /api/reviews` returns 401 with the dashboard secret/header hint.
- `rg -n "comprehension_required|quizLocked|mergeLocked" dashboard/src`
- `rg -n "DATABASE_URL|@supabase|createClient\\(|from ['\\\"]pg['\\\"]|from ['\\\"]postgres['\\\"]" dashboard/{src,package.json,vercel.json}`
- `git diff -- app/proxy/interceptor.py --exit-code`

## References

- Ledger: `architecture_and_roadmap.md`
- QRSPI design: `thoughts/qrspi/2026-07-20-dashboard-ops-harden/design.md`
- QRSPI plan: `thoughts/qrspi/2026-07-20-dashboard-ops-harden/plan.md`
- QRSPI autonomous mode used for stages 1-8.

## Scope Confirmation

- Interceptor untouched.
- JSON store remains default at `.data/reviews.json`.
- Quiz >=80% still gates approve/merge.
- No Supabase/Postgres migration.
