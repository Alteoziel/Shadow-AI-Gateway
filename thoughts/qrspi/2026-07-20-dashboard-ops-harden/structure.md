# Structure Outline

## Approach

Harden dashboard deployability through narrow vertical slices: expose safe operational state, render it in the UI, align deployment docs/examples, and verify the unchanged quiz/store/interceptor boundaries.

## Phase 1: Auth and Ingest Visibility

Add a dashboard-local status API and UI panel showing whether ingest/reviewer auth and merge tokens are configured.

**Files**: `dashboard/src/lib/auth.ts`, `dashboard/src/app/api/status/route.ts`, `dashboard/src/app/page.tsx`, `dashboard/src/components/ReviewPanel.tsx`

**Key changes**:
- `dashboardAuthStatus(): DashboardAuthStatus` — safe config booleans for UI.
- `GET /api/status` — returns auth and store status without secrets.
- `SetupStatusPanel` — visible setup/ingest auth state on the dashboard home page.
- `ReviewerUnlock` — clearer locked/unlocked messaging and reset path.

**Verify**: `npm run build` passes; status endpoint can be imported or exercised without secrets; approve/merge buttons remain quiz-locked.

---

## Phase 2: Deployability Docs and Dashboard Vercel Metadata

Align dashboard docs/env template with Ledger §11.C and add dashboard-scoped deploy metadata.

**Files**: `dashboard/.env.example`, `dashboard/README.md`, `dashboard/vercel.json`, `dashboard/src/lib/store.ts`

**Key changes**:
- `.env.example` labels production-required values and local-only escape hatch.
- `README.md` documents build/start, Vercel deploy, CI ingest secret, JSON store default, and no Supabase/Postgres until Phase 3.
- `dashboard/vercel.json` confines Vercel settings to the dashboard package.
- Store comment says JSON remains default and no DB env is read in this step.

**Verify**: `npm run build` passes; `rg` confirms no Supabase/Postgres implementation and interceptor remains untouched.

---

## Testing Checkpoints

- After Phase 1, UI and API expose auth/setup state without leaking secret values.
- After Phase 2, deployment docs match Ledger §11.C and build succeeds from `dashboard/`.
- Final branch verifies Step 6 quiz gating, JSON store default, and untouched interceptor with targeted `rg`/git checks.
