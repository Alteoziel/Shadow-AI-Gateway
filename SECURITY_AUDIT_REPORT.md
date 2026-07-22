# Security Audit Report — Shadow AI Ledger

**Date:** 2026-07-22  
**Baseline (last security update):** `e4ad4b2` — *Security hardening: authz, rate limits, audit, lockfile, CI gates* (#41)  
**HEAD audited:** `1473809` (post-#41: docs-only §12 Open-Source Trust playbook)  
**Panel:** 7 specialized sub-agents (Cursor Grok 4.5 High) + Lead Auditor synthesis  
**Scope:** Exhaustive review of application, dashboard, governance, CI, and deploy manifests (~10.9k LOC source)

---

## Executive Summary

- **Total files audited:** 87 primary source/config files under `app/`, `dashboard/src/`, `governance/governance/`, `tests/`, `.github/`, `perf/`, plus root security/deploy manifests (Dockerfile, lockfiles, Semgrep, Gitleaks, operator checklist). Estimated **~10,900 LOC** of Python/TS/JS covered (excluding `uv.lock` / `package-lock.json` bulk and `thoughts/` design docs).
- **Overall risk rating:** **High**
- **Key areas of concern introduced / remaining since last security update (#41):**
  1. **No post-#41 code regression** — `git diff e4ad4b2..HEAD` is documentation-only. Gateway #41 controls (Bearer/X-API-Key, rate limit, PBKDF2 fingerprints, frozen CI, coverage ≥98%, Semgrep authz) remain present.
  2. **Critical residual risks predate or were outside #41’s gateway focus:** dashboard coding grader RCE via `node:vm`, stored XSS via `dangerouslySetInnerHTML`, CI fuzz-chamber `exec` of PR code, and optional site-gate leaving review GET APIs world-readable.
  3. **Incomplete #41 surfaces:** deny-path audit events (`AUTH_DENIED` / `RATE_LIMITED`) never emitted; process-local rate limits; Dockerfile ignores `uv.lock`; FOSSA soft-skips without secret.

Gateway authz from #41 is solid and fail-closed. The highest actionable risk is the **governance dashboard code-execution and XSS surface**, followed by **opt-in read access control**.

---

## High-Priority Security Findings

### CRITICAL

#### C1 — Server-side RCE via coding quiz grader (`node:vm`)

- **Location:** `dashboard/src/lib/codingGrade.ts` (Lines 45–66); invoked from `dashboard/src/lib/store.ts` (Lines 271–281) → `dashboard/src/app/api/reviews/[id]/route.ts` (`submit_quiz`)
- **Agent Responsible:** Agent 2 (Data Sanitization & Injection Specialist)
- **Vulnerability / Flaw:** User-submitted source runs in `vm.runInContext`. Node’s `vm` is **not** a security boundary. The denylist (`require|process\.|globalThis|Function|…`) is bypassable (e.g. `this.constructor.constructor('return process')()`). `question.entrypoint` is interpolated into executable JS without allowlisting; ingest accepts arbitrary `metrics` (`z.record(z.unknown())`).
- **Impact:** Authenticated `submit_quiz` (reviewer secret) — or poisoned pack via ingest secret — can achieve RCE on the Next.js/Vercel Node process: read env secrets (`GITHUB_TOKEN`, dashboard secrets), pivot, or abuse merge capabilities.
- **Remediation:** Do not use `node:vm` as a sandbox. Prefer isolated workers / WASM / offline AST checks only. Until then: allowlist `entrypoint` to `/^[A-Za-z_][A-Za-z0-9_]*$/`, parse source with a real AST and reject freeform execution, never string-build code from untrusted fields, and Zod-validate coding-question schema on ingest.

#### C2 — CI RCE — fuzz chamber `exec` of scanned Python

- **Location:** `governance/governance/steps/fuzz_chamber.py` (Lines 28–40, harness; Lines 121–138 invocation); triggered by `.github/workflows/ai-guardrail.yml` (`--changed-only`)
- **Agent Responsible:** Agent 2 (Data Sanitization & Injection Specialist)
- **Vulnerability / Flaw:** Harness does `exec(compile(code, TARGET_FILE, "exec"), …)` on functions discovered in PR-changed `.py` files. Comment admits “Docker optional later”; no seccomp/network isolation on the default Actions runner.
- **Impact:** Malicious PR that adds/changes a fuzzable helper runs attacker code on the GitHub Actions runner with access to job secrets (`OPENAI_API_KEY`, `GOVERNANCE_DASHBOARD_SECRET`, `GITHUB_TOKEN`).
- **Remediation:** Run fuzz only inside a locked-down container (no network, dropped caps, read-only FS), or restrict targets to an explicit allowlist under `app/` with content hash pins. Never `exec` untrusted PR trees on the default runner identity.

---

### HIGH

#### H1 — Stored XSS via quiz prompt `dangerouslySetInnerHTML`

- **Location:** `dashboard/src/components/ReviewPanel.tsx` (Lines 183–205)
- **Agent Responsible:** Agent 2 (Data Sanitization & Injection Specialist)
- **Vulnerability / Flaw:** Prompt segments are injected as HTML after only a `**bold**` regex replace. No HTML escaping/DOMPurify. Prompts originate from stored review data; ingest accepts unvalidated `metrics`.
- **Impact:** Holder of ingest secret (or compromised CI) can plant `<img onerror=…>` / script payloads executed in every reviewer’s browser when the quiz renders → session/token theft, reviewer-secret phishing via XSS.
- **Remediation:** Remove `dangerouslySetInnerHTML`. Render bold via React nodes (`<strong>`), or sanitize with a strict allowlist. Zod-validate comprehension prompts as plain text on ingest.

#### H2 — Unauthenticated review listing/read when site gate is off (BOLA)

- **Location:** `dashboard/src/app/api/reviews/route.ts` (Lines 21–27); `dashboard/src/app/api/reviews/[id]/route.ts` (GET); `dashboard/src/middleware.ts` (Lines 62–65)
- **Agent Responsible:** Agent 1 (Identity & Auth Guardian) / Agent 7 (Diff & Security Regression Tracker)
- **Vulnerability / Flaw:** GET review APIs never call `authorizeIngest` / `authorizeReviewer`. Protection is only optional middleware when `GOVERNANCE_SITE_PASSWORD` is set. When unset, middleware is a no-op.
- **Impact:** Public dashboard deploy without site password exposes PR metadata, guardrail findings, study guides, and quiz content (including coding `expected` values — see M2).
- **Remediation:** Require site session **or** machine secret on every GET. In production (`NODE_ENV=production` / Vercel), fail closed if neither `GOVERNANCE_SITE_PASSWORD` nor dashboard secret is configured.

#### H3 — Dockerfile ignores `uv.lock` (supply-chain drift vs #41)

- **Location:** `Dockerfile` (Lines 10–14)
- **Agent Responsible:** Agent 5 (Dependency & Integration Specialist) / Agent 7
- **Vulnerability / Flaw:** Image build runs `pip install .` without copying or freezing against `uv.lock`. CI uses `uv sync --frozen`; production images can resolve different transitive versions.
- **Impact:** Undetected CVEs / supply-chain drift between audited CI and deployed gateway images.
- **Remediation:** `COPY uv.lock pyproject.toml` then `uv sync --frozen --no-dev` (or install from locked hashes). Align Trivy/pip-audit with the image.

#### H4 — Governance LLM / dashboard URLs lack HTTPS host allowlist

- **Location:** `governance/governance/steps/security_auditor.py`, `comprehension_gate.py` (`GOVERNANCE_LLM_BASE_URL`); `governance/governance/reporters/github.py` (`GOVERNANCE_DASHBOARD_URL`)
- **Agent Responsible:** Agent 5 (Dependency & Integration Specialist)
- **Vulnerability / Flaw:** Outbound base URLs are env-controlled with no scheme/host allowlist; plain `httpx.Client`.
- **Impact:** Misconfig or compromised CI secret can send API keys + PR diffs over cleartext HTTP or to an attacker host (SSRF/exfil from runner).
- **Remediation:** Enforce `https://` + allowlist (`api.openai.com` and approved hosts); fail closed on `http://`; optionally reuse gateway-style egress checks.

---

### MEDIUM

#### M1 — Login endpoint has no rate limit / lockout

- **Location:** `dashboard/src/app/api/auth/login/route.ts` (Lines 14–55)
- **Agent Responsible:** Agent 1 / Agent 6 (Resource & DoS Specialist)
- **Vulnerability / Flaw:** Unlimited password guesses against shared `GOVERNANCE_SITE_PASSWORD`.
- **Impact:** Online brute-force of the site gate → full review read access.
- **Remediation:** Sliding-window limit (e.g. 5/min/IP) returning 429; optional lockout after N failures.

#### M2 — Coding quiz answer keys (`expected`) leak via sanitize

- **Location:** `dashboard/src/lib/store.ts` (Lines 214–225) (`publicComprehension`)
- **Agent Responsible:** Agent 1 (Identity & Auth Guardian)
- **Vulnerability / Flaw:** Strips `answer_index` / `explanation` but leaves `tests[].expected` (and full `tests`) on coding questions.
- **Impact:** Anyone who can read a review can solve coding challenges without understanding them, weakening Step 6 before approve/merge.
- **Remediation:** Strip `expected` (and ideally full `tests`) from client packs; keep hidden tests server-side only in `gradeComprehension`.

#### M3 — Client-side code execution (`new Function`) for “Run tests”

- **Location:** `dashboard/src/lib/codingGradeBrowser.ts` (Lines 45–49); `ReviewPanel.tsx` (Run tests)
- **Agent Responsible:** Agent 2
- **Vulnerability / Flaw:** Same unsanitized `entrypoint` interpolation in the reviewer browser.
- **Impact:** Session/token theft if comprehension pack is poisoned (pairs with H1 ingest path).
- **Remediation:** Entrypoint allowlist; iframe sandbox with opaque origin for preview grading.

#### M4 — No gateway max request body / message size limits

- **Location:** `app/main.py`, `app/models/schemas.py`, `app/api/v1/chat.py`
- **Agent Responsible:** Agent 6 (Resource & DoS Specialist)
- **Vulnerability / Flaw:** No max body size; `ChatMessage.content` / `messages` / `extra_body` unbounded. Starlette buffers full JSON before/alongside auth.
- **Impact:** Multi‑MB bodies → OOM / worker stall (works without a valid key for parse path).
- **Remediation:** Early `Content-Length` reject (e.g. 1–2 MB); Pydantic `Field(max_length=…)`; cap message count; return 413.

#### M5 — Unbounded dashboard review store growth

- **Location:** `dashboard/src/lib/store.ts`; `dashboard/src/lib/ingest.ts`
- **Agent Responsible:** Agent 6 / Agent 4
- **Vulnerability / Flaw:** Reviews list never capped; Zod ingest schema has no `.max()` on arrays/strings.
- **Impact:** Memory/Redis exhaustion; `GET /api/reviews` full dump → response DoS.
- **Remediation:** Cap store (max N / TTL); paginate list API; add max array/string lengths on ingest.

#### M6 — Dashboard store TOCTOU / lost updates; approve/merge race

- **Location:** `dashboard/src/lib/store.ts` (`readReviews`/`writeReviews`); `dashboard/src/app/api/reviews/[id]/route.ts` (approve/merge/`submit_quiz`)
- **Agent Responsible:** Agent 4 (Logic & State Machine Auditor)
- **Vulnerability / Flaw:** Classic read-modify-write without Redis WATCH/Lua. Gate checks `comprehension_passed` on a snapshot then writes without re-validating. `submit_quiz` can downgrade `approved`/`merged` back to pending.
- **Impact:** Lost quiz/approve state; approve after gate revoked; post-merge status regression.
- **Remediation:** Atomic conditional updates; reject `submit_quiz` in terminal states; per-review keys with optimistic locking.

#### M7 — Ingest-controlled `pass_threshold` can auto-pass quiz

- **Location:** `dashboard/src/lib/store.ts` `gradeComprehension`; `dashboard/src/lib/ingest.ts` (`metrics: z.record(z.unknown())`)
- **Agent Responsible:** Agent 4
- **Vulnerability / Flaw:** Grading trusts pack `pass_threshold` (e.g. `0`).
- **Impact:** Holder of dashboard secret can forge packs that auto-pass Step 6.
- **Remediation:** Clamp/override threshold server-side (e.g. `Math.max(0.8, …)`); validate pack schema on ingest.

#### M8 — Process-local rate limit (multi-worker bypass) + disable kill-switch

- **Location:** `app/security/rate_limit.py` (Lines 15–16, 31–57); `app/config.py`
- **Agent Responsible:** Agent 1 / Agent 4 / Agent 6 / Agent 7
- **Vulnerability / Flaw:** `_buckets` is process-local; `GATEWAY_RATE_LIMIT_PER_MINUTE=0` disables limiting.
- **Impact:** Effective limit ≈ `N ×` quota across workers; misconfig removes #41 cost control.
- **Remediation:** Shared Redis bucket; disallow `0` in production (or require explicit `RATE_LIMIT_DISABLED=true`).

#### M9 — `AUTH_DENIED` / `RATE_LIMITED` audit events never emitted

- **Location:** `app/security/auth.py` (Lines 73–78); `app/security/rate_limit.py`; `app/security/audit.py`; contrast `app/api/v1/chat.py` success path
- **Agent Responsible:** Agent 1 / Agent 7 (Diff & Security Regression Tracker)
- **Vulnerability / Flaw:** 401/429 raised in Depends before route; enum values exist but unused. PR template asks for deny-path audit.
- **Impact:** Failed auth/abuse invisible in audit trail.
- **Remediation:** Emit from auth/rate-limit before raising, or exception middleware mapping 401/429 → audit events.

#### M10 — Dashboard shared-secret compares are not timing-safe

- **Location:** `dashboard/src/lib/auth.ts` (Lines 53, 67); `dashboard/src/middleware.ts` (Lines 37–38)
- **Agent Responsible:** Agent 1 / Agent 3 / Agent 5
- **Vulnerability / Flaw:** Uses `===` for ingest/reviewer secrets. Site password path correctly uses `timingSafeEqual` / HMAC.
- **Impact:** Theoretical timing oracle on secret length/content (practical risk low over network).
- **Remediation:** Reuse `timingSafeEqual` / hash-then-compare for all secret header checks.

#### M11 — Secret-scanner evidence echoes matched secrets

- **Location:** `governance/governance/steps/security_auditor.py` (~Lines 92–104)
- **Agent Responsible:** Agent 3 (Secrets & Leakage Detector)
- **Vulnerability / Flaw:** Matched secret regex put in `evidence=snippet[:120]`, then shipped to dashboard / PR comments.
- **Impact:** Secondary disclosure of a committed secret into CI artifacts and GitHub.
- **Remediation:** Redact/fingerprint evidence; never echo the full match.

#### M12 — Optional `GITHUB_REPOSITORY` pin for merge/status

- **Location:** `dashboard/src/lib/github.ts`
- **Agent Responsible:** Agent 5
- **Vulnerability / Flaw:** Repo allowlist only applies when env is set.
- **Impact:** Stolen dashboard token + crafted review `repo` can merge/status against any reachable repo.
- **Remediation:** Require `GITHUB_REPOSITORY` in production; refuse merge/status when unset.

#### M13 — Path escape in governance pipeline `--file`

- **Location:** `governance/governance/pipeline.py` (Lines 27–28)
- **Agent Responsible:** Agent 2
- **Vulnerability / Flaw:** Absolute/`..` paths can resolve outside repo root.
- **Impact:** Operator/CI misuse can scan or fuzz unintended host files (workflow today uses `--changed-only`).
- **Remediation:** `resolve()` and require `path.is_relative_to(root.resolve())`.

---

### LOW

#### L1 — OpenAPI UI unauthenticated; status/health recon when gate off

- **Location:** `app/main.py` (FastAPI defaults); `dashboard/src/app/api/status/route.ts`, `health/route.ts`
- **Agent Responsible:** Agent 1
- **Remediation:** Disable docs in production; keep health minimal; gate `/api/status`.

#### L2 — Streaming relays nearly all upstream headers; auth headers passed into interceptor

- **Location:** `app/proxy/streaming.py`; `app/api/v1/chat.py`
- **Agent Responsible:** Agent 3 / Agent 5
- **Remediation:** Allowlist SSE headers; strip `Authorization` / `X-API-Key` before interceptor.

#### L3 — Open-redirect edge after login (`/\evil.com`)

- **Location:** `dashboard/src/app/login/page.tsx` (`safeNextPath`)
- **Agent Responsible:** Agent 2
- **Remediation:** Allow only `^/[A-Za-z0-9._~/-]*$` or same-origin URL parse.

#### L4 — FOSSA soft-skips; Semgrep rate-limit rule is WARNING; Locust/pre-commit not in CI

- **Location:** `.github/workflows/fossa-license.yml`; `.semgrep.yml`; `perf/locustfile.py`; `.pre-commit-config.yaml`
- **Agent Responsible:** Agent 7
- **Remediation:** Fail required FOSSA on main when secret missing; promote rate-limit Semgrep to ERROR; schedule Locust optionally.

#### L5 — `render.yaml` omits `GATEWAY_API_KEY`; §12 trust playbook stale vs #41

- **Location:** `render.yaml`; `architecture_and_roadmap.md` §12
- **Agent Responsible:** Agent 3 / Agent 7
- **Remediation:** Add `GATEWAY_API_KEY` as sync-false; sync §12 status table to landed controls.

#### L6 — Unbounded SSE stream duration; empty rate-limit bucket key retention

- **Location:** `app/proxy/streaming.py`; `app/security/rate_limit.py`
- **Agent Responsible:** Agent 6
- **Remediation:** Cap relayed bytes / absolute stream deadline; delete empty bucket keys.

---

## General Code Quality & Technical Debt

- **Phase 2 scrub unwired:** `app/scrub/pipeline.py` still raises `NotImplementedError` — prompts egress without PII scrub (roadmap-known; not a #41 regression).
- **In-memory audit sink:** unbounded append, no lock; Phase 3 Postgres planned — document multi-instance limits.
- **Governance no lockfile:** `governance/` installs from PyPI ranges in CI — weaker reproducibility than gateway `uv.lock`.
- **Reviewer secret via `window.prompt`:** weaker UX than a dedicated form; XSS can still read in-memory secret.
- **`extra_body` passthrough:** clients can inject provider features beyond gateway policy — allowlist keys.
- **Auth fingerprint cost:** 10k PBKDF2 iterations per successful auth — fine at 60 rpm; document if raising limits.
- **Copyright filter / huge files:** no file-size cap before hashing — CI DoS risk on oversized inputs.
- **Documentation drift:** §12 Open-Source Trust playbook understates #41 (marks Hypothesis/rate-limit as Target).
- **Positive notes:** No committed live secrets; gateway fail-closed without `GATEWAY_API_KEY`; egress HTTPS allowlist + Semgrep ban on bare `httpx.AsyncClient`; MC quiz `answer_index` stripped; site cookie HMAC + timing-safe password compare; coverage floor 98% + Hypothesis tests present.

---

## Verification & Clean Bill Checklist

| Directory / Area | Files (approx) | Agent 1 Auth | Agent 2 Injection | Agent 3 Secrets | Agent 4 Logic | Agent 5 Deps | Agent 6 DoS | Agent 7 Regression | Status |
|------------------|----------------|--------------|-------------------|-----------------|---------------|--------------|-------------|--------------------|--------|
| `app/security/` | 6 | ⚠ M8–M10,M9 | ✅ | ✅ | ⚠ M8–M9 | ✅ | ⚠ M8,L6 | ⚠ M9 | **PASS w/ findings** |
| `app/api/` + `main.py` + `config.py` | 6 | ✅ /v1 | ✅ | ⚠ L2 | ⚠ interceptor meta | ✅ | ⚠ M4 | ✅ | **PASS w/ findings** |
| `app/proxy/` | 8 | ✅ | ✅ egress | ⚠ L2 | ⚠ payload strip | ✅ | ⚠ L6 streams | ✅ | **PASS w/ findings** |
| `app/scrub/` | 3 | N/A | ✅ unused | ✅ | ⚠ unwired | N/A | ⚠ future ReDoS | ⚠ Phase 2 gap | **KNOWN GAP** |
| `app/models/` | 2 | N/A | ✅ | ✅ | ✅ | ✅ | ⚠ M4 | ✅ | **PASS w/ findings** |
| `dashboard/src/lib/` | 8 | ⚠ H2,M2,M10 | **C1**,M3 | ⚠ M10 | **M6–M7** | ⚠ M12 | ⚠ M5 | ⚠ H2 | **FAIL (C1)** |
| `dashboard/src/app/api/` | 7 | **H2**,M1 | ✅ | ⚠ | ⚠ M6 | ✅ | ⚠ M1,M5 | ⚠ H2 | **FAIL (H2)** |
| `dashboard/src/components/` | 3 | L3 prompt | **H1**,M3 | ⚠ | ✅ | N/A | ✅ | ⚠ H1 | **FAIL (H1)** |
| `dashboard/src/middleware.ts` + pages | 5 | ⚠ opt-in gate | ⚠ L3 redirect | ✅ | ✅ | ✅ | ⚠ M1 | ⚠ PARTIAL #38 | **PASS w/ findings** |
| `governance/governance/steps/` | 7 | N/A | **C2**,M13 | ⚠ M11 | ✅ | **H4** | ⚠ fuzz/copyright | N/A | **FAIL (C2)** |
| `governance/` reporters/cli/pipeline | 5 | ✅ secret header | ⚠ M13 | ✅ | ✅ | ⚠ H4 | ✅ | ✅ | **PASS w/ findings** |
| `tests/` | 18 | ✅ coverage | ✅ | ✅ fixtures | ✅ | ✅ | ✅ | ✅ #41 tests | **PASS** |
| `.github/workflows/` | 5 | N/A | ⚠ C2 trigger | ✅ | N/A | ⚠ FOSSA soft | ✅ | ⚠ L4 | **PASS w/ findings** |
| Root deploy / security config | 12+ | ✅ | ✅ | ⚠ L5 | N/A | **H3** Dockerfile | ✅ Locust file | ⚠ L4–L5 | **PASS w/ findings** |
| Post-#41 diff (`e4ad4b2..HEAD`) | docs only | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ no code regression | **CLEAN** |

**Legend:** ✅ clean for that discipline · ⚠ actionable finding · **FAIL** = Critical/High must-fix before production trust

### #41 Hardening Status (Agent 7)

| Control | Status |
|---------|--------|
| Bearer/X-API-Key on `/v1` | **PASS** |
| Sliding-window rate limit | **PASS** (kill-switch PARTIAL) |
| In-memory audit on request path | **PARTIAL** (deny path missing) |
| `uv.lock` + frozen CI | **PASS** (Dockerfile PARTIAL) |
| mypy strict / coverage ≥98% | **PASS** |
| Hypothesis / streaming failure tests | **PASS** |
| pre-commit / Locust / asyncio-debug | **PARTIAL** (asyncio CI only) |
| FOSSA workflow | **PARTIAL** (soft-skip) |
| Semgrep authz | **PASS** (rate-limit WARNING) |
| PBKDF2 key fingerprinting | **PASS** |
| sharp `^0.35.0` override | **PASS** |
| Dashboard site password (#38) | **PARTIAL** (opt-in) |

---

## Recommended Fix Priority

1. **Immediate:** C1 (`codingGrade` sandbox), C2 (fuzz `exec` isolation), H1 (XSS), H2 (auth on GET reviews).
2. **Short-term:** H3 (Dockerfile freeze), H4 (URL allowlists), M4–M5 (body/store bounds), M6–M7 (store races / threshold clamp), M9 (deny-path audit).
3. **Hardening polish:** M1, M8, M10–M13, L1–L6, sync §12 docs.

---

*Report generated by Lead Security Auditor coordinating Agents 1–7 (Cursor Grok 4.5 High). False positives filtered; findings verified against source at HEAD.*
