# Implementation Plan

## Overview

Make the Step 7 dashboard deployable and operationally obvious while preserving JSON storage, Step 6 quiz gating, and the human-owned interceptor boundary.

## Autonomous Assumptions

- Build success is the required deployability gate because the user explicitly requested `npm run build must succeed`.
- UI manual behavior can be verified through build plus static/route checks in this non-running implementation pass.
- `dashboard/vercel.json` is dashboard-scoped and does not imply Vercel support for the streaming proxy.

## Phase 1: Auth and Ingest Visibility

### Changes

#### 1. Auth status helper
**File**: `dashboard/src/lib/auth.ts`  
**Action**: modify

- Add exported `DashboardAuthStatus` type.
- Add `dashboardAuthStatus()` returning booleans for dashboard secret, reviewer secret, insecure dev, production, merge token, and the expected header names.
- Keep existing `authorizeIngest`, `authorizeReviewer`, and `unauthorizedResponse` behavior intact.

#### 2. Safe status API
**File**: `dashboard/src/app/api/status/route.ts`  
**Action**: create

- Export `GET()` that returns `{ auth, store }`.
- Include store path `.data/reviews.json`; do not return secret values.

#### 3. Visible dashboard status
**File**: `dashboard/src/app/page.tsx`  
**Action**: modify

- Import `dashboardAuthStatus`.
- Render a setup panel above the reviews grid showing ingest auth configured/missing, reviewer auth mode, merge token availability, insecure dev state, and JSON store path.

#### 4. Clear reviewer unlock flow
**File**: `dashboard/src/components/ReviewPanel.tsx`  
**Action**: modify

- Expand `ReviewerUnlock` copy to say actions are locked until a reviewer secret is loaded.
- Keep `sessionStorage` behavior and clear button.
- Leave approve/merge disable logic unchanged.

### Verification
#### Automated
- [x] `cd dashboard && npm run build` passes after Phase 1.
- [x] `rg -n "comprehension_required|quizLocked|mergeLocked" dashboard/src` confirms quiz gating remains in UI and API.

#### Manual
- [x] autonomous: verified via source/build that status panel exposes auth setup and no secret values.

---

## Phase 2: Deployability Docs and Dashboard Vercel Metadata

### Changes

#### 1. Env template
**File**: `dashboard/.env.example`  
**Action**: modify

- Mark `GOVERNANCE_DASHBOARD_SECRET` required in production / when dashboard URL is set.
- Explain `GOVERNANCE_REVIEWER_SECRET`, local-only insecure dev, and merge token choices.

#### 2. README
**File**: `dashboard/README.md`  
**Action**: modify

- Align with Ledger §11.C commands: `npm install`, set env, `npm run build && npm start`, or deploy to Vercel.
- Document CI POST header and visible 401 behavior.
- Document JSON store default `.data/reviews.json` and no Supabase/Postgres until Phase 3.

#### 3. Store comment
**File**: `dashboard/src/lib/store.ts`  
**Action**: modify

- Replace optional `DATABASE_URL` wording with explicit JSON-default wording.

#### 4. Optional Vercel metadata
**File**: `dashboard/vercel.json`  
**Action**: create

- Add dashboard package build/install/output settings only.

### Verification
#### Automated
- [x] `cd dashboard && npm run build` passes after Phase 2.
- [x] `rg -n "DATABASE_URL|@supabase|createClient\\(|from ['\\\"]pg['\\\"]|from ['\\\"]postgres['\\\"]" dashboard/{src,package.json,vercel.json}` shows no DB implementation.
- [x] `git diff -- app/proxy/interceptor.py --exit-code` is empty.

#### Manual
- [x] autonomous: verified via docs diff that README and `.env.example` match Ledger §11.C dashboard setup.
