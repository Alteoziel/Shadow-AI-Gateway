# Stage 8: PR

## Title

Harden Step 7 dashboard deployability

## Summary

This change makes the Step 7 dashboard easier to deploy and operate without expanding scope into Phase 3 database work or the human-owned proxy checkpoint. It adds visible auth/setup status, surfaces ingest auth failures through `/api/status` and existing 401 responses, keeps quiz pass gating in the UI and API, and aligns dashboard docs with Ledger §11.C.

## Changes

- Added safe dashboard auth status helper and `GET /api/status`.
- Added a deployment readiness panel showing ingest auth, reviewer unlock mode, merge token status, runtime mode, and `.data/reviews.json`.
- Clarified reviewer unlock/clear flow for browser-session secrets.
- Updated `dashboard/.env.example` and `dashboard/README.md` to match Ledger §11.C.
- Added dashboard-scoped `dashboard/vercel.json`.
- Preserved JSON store default and Step 6 approve/merge gate.

## Verification

- `cd dashboard && npm run build` — passed.
- Built dashboard smoke test:
  - `GET /api/status` — returned safe auth/store status.
  - unauthenticated `POST /api/reviews` — returned 401 with `GOVERNANCE_DASHBOARD_SECRET` / `X-Governance-Secret` hint.
- `rg -n "comprehension_required|quizLocked|mergeLocked" dashboard/src` — confirmed quiz gating remains.
- `rg -n "DATABASE_URL|@supabase|createClient\\(|from ['\\\"]pg['\\\"]|from ['\\\"]postgres['\\\"]" dashboard/{src,package.json,vercel.json}` — no matches.
- `git diff -- app/proxy/interceptor.py --exit-code` — empty.

## References

- Ledger: `architecture_and_roadmap.md`
- QRSPI design: `thoughts/qrspi/2026-07-20-dashboard-ops-harden/design.md`
- QRSPI plan: `thoughts/qrspi/2026-07-20-dashboard-ops-harden/plan.md`
- QRSPI autonomous mode used for stages 1-8.
