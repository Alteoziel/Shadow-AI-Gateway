# Security operator checklist (human steps)

This list is for a **non-expert human operator**. Code and CI can automate a lot; these items need **you** (clicks, accounts, or secrets that must never be committed).

**Legend**

- **DONE IN REPO** — already wired in this repository; you only confirm or maintain.
- **YOU MUST DO THIS** — cannot be finished by code alone; you take the action.

## Master status (every hardening item)

| Item | Status | Where / what you do |
|------|--------|---------------------|
| Python lockfile (`uv.lock`) + frozen CI | **DONE IN REPO** | Confirm with §9 below; after changing deps run `uv lock` |
| Gateway authz (API key) | **DONE IN REPO** | **YOU** must set `GATEWAY_API_KEY` in `.env` / hosting secrets (§4) |
| Rate limiting | **DONE IN REPO** | Tune `GATEWAY_RATE_LIMIT_PER_MINUTE` if needed |
| Coverage floor (98% now; ~99% measured) | **DONE IN REPO** | Maintain ≥98%; see §8 |
| Streaming / provider failure tests | **DONE IN REPO** | Nothing |
| Audit trail on request path (in-memory → Phase 3 DB) | **DONE IN REPO** | Nothing until Phase 3 Postgres |
| Copyright signature DB expanded | **DONE IN REPO** | Optionally add more snippets later |
| Mypy `--strict` | **DONE IN REPO** | Nothing |
| Secret scanning + push protection | **YOU MUST DO THIS** | §1 (confirm enabled) |
| Hypothesis property tests | **DONE IN REPO** | Nothing |
| Pre-commit (ruff + gitleaks) | **DONE IN REPO** | Optional local install §5 |
| Locust load tests | **DONE IN REPO** | Optional local run §6 |
| `PYTHONASYNCIODEBUG=1` CI smoke | **DONE IN REPO** | Nothing |
| FOSSA license SCA workflow | **DONE IN REPO** (needs secret) | **YOU** create FOSSA account + `FOSSA_API_KEY` (§2) |
| Authz PR checklist template | **DONE IN REPO** | Fill checkboxes on every PR |
| QRSPI secure prompt rules | **DONE IN REPO** | Nothing |
| Semgrep authz/rate-limit rules | **DONE IN REPO** | Nothing |

Work top to bottom. Check boxes as you finish.

---

## 1. Verify GitHub Secret scanning + Push protection

**YOU MUST DO THIS** (confirm — it may already be on).

Secret scanning watches for accidental keys in commits. Push protection **blocks** a push that contains a known secret pattern.

1. Open your GitHub repository in a browser.
2. Click **Settings** (repo settings, not your personal settings).
3. In the left sidebar, click **Code security** (sometimes labeled **Code security and analysis**).
4. Find **Secret scanning**.
   - If it shows **Enabled**, leave it on.
   - If it shows a button like **Enable**, click **Enable**.
5. Find **Push protection** (under Secret scanning / secret protection).
   - Confirm it is **Enabled**.
   - If not, click **Enable**.
6. Optional but useful: under the same page, note whether **Dependabot alerts** are enabled (this repo already expects them — see `ENTERPRISE_LAYERS.md`).

**Confirm it worked:** Settings → Code security still shows Secret scanning **and** Push protection as enabled after you refresh the page.

- [ ] Secret scanning confirmed enabled
- [ ] Push protection confirmed enabled

---

## 2. FOSSA account + `FOSSA_API_KEY` GitHub secret (or Snyk alternative)

**YOU MUST DO THIS** for the account/token/secret.  
**DONE IN REPO:** workflow [`.github/workflows/fossa-license.yml`](.github/workflows/fossa-license.yml) (job name **FOSSA License Scan**). It only runs when `FOSSA_API_KEY` is set.

License/dependency scanning needs a **cloud account API key** that GitHub Actions can use. That key is a secret — never put it in code or commit it.

### Option A — FOSSA (preferred; matches this repo)

1. Go to [https://fossa.com](https://fossa.com) and create an account (or sign in).
2. In the FOSSA UI, open your **Account** / **Settings** / **Integrations** area and create or copy an **API token** (sometimes called “API key”).
3. In GitHub: open the repo → **Settings** → **Secrets and variables** → **Actions**.
4. Click **New repository secret**.
5. Name (exact): `FOSSA_API_KEY`
6. Value: paste the FOSSA token → **Add secret**.
7. Open `.github/workflows/fossa-license.yml` and confirm it uses `${{ secrets.FOSSA_API_KEY }}`.

### Option B — Snyk (alternative)

1. Create a [Snyk](https://snyk.io) account and get an API token.
2. GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
3. Name: `SNYK_TOKEN` (or the name your workflow expects — match the workflow YAML exactly).
4. Paste the token → **Add secret**.
5. You would also need a Snyk workflow under `.github/workflows/` (this repo ships FOSSA by default).

**Confirm it worked:** open a PR to `main` → **Actions** → workflow **FOSSA License Scan** should run (not skip) and succeed.

- [ ] FOSSA or Snyk account created
- [ ] `FOSSA_API_KEY` (or Snyk token) stored as a GitHub Actions secret (never committed)
- [ ] PR Actions run shows FOSSA License Scan succeeding

---

## 3. Confirm Protect Main still requires Enterprise Layers / Governance / CodeQL

**DONE IN REPO:** the checks and workflows exist.  
**YOU MUST DO THIS:** confirm GitHub **branch protection / ruleset** still requires them.

Protect Main is the GitHub rule that blocks merging to `main` unless required checks pass.

1. GitHub repo → **Settings** → **Rules** → **Rulesets** (or **Branches** → branch protection, depending on UI).
2. Open the ruleset that protects **`main`** (often named something like **Protect Main**).
3. Under **Require status checks to pass** (or similar), confirm **all** of these are listed as required:
   - **`Governance Steps 1–6`** — workflow: `.github/workflows/ai-guardrail.yml`
   - **`Enterprise Layers B–E`** — workflow: `.github/workflows/enterprise-hygiene.yml`
   - **`CodeQL (Layer C)`** — workflow: `.github/workflows/codeql.yml`
4. Do **not** remove these requirements “to make merging easier.”
5. Also keep (if already set): require a pull request, Code Owner review, signed commits, up-to-date branch — see `ENTERPRISE_LAYERS.md`.

**Confirm it worked:** open (or imagine) a PR to `main` — the merge box should list those three checks as required.

- [ ] Protect Main still requires `Governance Steps 1–6`
- [ ] Protect Main still requires `Enterprise Layers B–E`
- [ ] Protect Main still requires `CodeQL (Layer C)`

---

## 4. Generate a strong `GATEWAY_API_KEY` and set it everywhere (never commit)

**YOU MUST DO THIS.**

This key is a shared secret clients send so strangers cannot call your gateway. Treat it like a password.

1. Generate a strong random value on your machine, for example:
   ```bash
   openssl rand -hex 32
   ```
2. **Local:** copy `.env.example` to `.env` if you have not already. Add or set:
   ```bash
   GATEWAY_API_KEY=<paste-the-value>
   ```
   Never commit `.env` (it should stay in `.gitignore`).
3. **Fly.io** (if you deploy there): set the secret in the Fly dashboard or CLI (`fly secrets set GATEWAY_API_KEY=...`) — do not put it in `fly.toml` as plain text committed to git.
4. **Render** (if you deploy there): Dashboard → your web service → **Environment** → add `GATEWAY_API_KEY` → save/redeploy.
5. **Any other production host:** set the same variable in that host’s secret store / environment UI.
6. Double-check `git status` — `.env` must **not** appear as a file you are about to commit.

**Confirm it worked:** local/production process can read `GATEWAY_API_KEY`; searching the git history for the raw key finds nothing.

- [ ] Strong key generated
- [ ] Set in local `.env`
- [ ] Set in Fly / Render / production secrets
- [ ] Confirmed it was never committed

---

## 5. Optional: install pre-commit locally

**YOU MUST DO THIS** only if you want hooks on your laptop.  
**DONE IN REPO:** [`.pre-commit-config.yaml`](.pre-commit-config.yaml) at the repo root.

Pre-commit runs quick checks (lint/secrets style) **before** each commit on your machine.

1. From the repo root, with Python available:
   ```bash
   pip install pre-commit && pre-commit install
   ```
2. Optionally run once on all files:
   ```bash
   pre-commit run --all-files
   ```

- [ ] (Optional) `pre-commit` installed and `pre-commit install` completed

---

## 6. Optional: run Locust load test locally

**YOU MUST DO THIS** only when you want a manual load test.  
**DONE IN REPO:** [`perf/README.md`](perf/README.md) + [`perf/locustfile.py`](perf/locustfile.py).

Locust is a tool that sends many fake requests to see if the gateway stays healthy under load.

1. Start the gateway locally (see README Quickstart).
2. From the repo root, follow [`perf/README.md`](perf/README.md):
   ```bash
   pip install locust
   export GATEWAY_API_KEY=test-gateway-key
   locust -f perf/locustfile.py --host http://127.0.0.1:8000
   ```
3. Point Locust at your local URL (`http://127.0.0.1:8000`), not production, unless you intentionally mean to load-test production.

- [ ] (Optional) Locust run completed using commands under `perf/`

---

## 7. Optional: second CODEOWNER collaborator

**DONE IN REPO:** `.github/CODEOWNERS` exists (currently a solo owner).  
**YOU MUST DO THIS** when a second human can review.

Code owners are people GitHub requires to approve changes to sensitive folders.

1. Invite the collaborator to the GitHub repo (**Settings** → **Collaborators** → **Add people**) with at least write access.
2. Edit `.github/CODEOWNERS` and add their `@username` next to (or instead of solo-only) paths such as `/app/security/`, `/app/proxy/`, `/governance/`, and `/.github/workflows/`.
3. Open a small PR that touches one of those paths and confirm GitHub requests their review.

- [ ] (Optional) Second collaborator invited
- [ ] (Optional) Listed in `.github/CODEOWNERS`

---

## 8. Coverage floor (98%)

**DONE IN REPO:** pytest coverage floor is `--cov-fail-under=98` in `pyproject.toml` (OSS bar was 95%; measured `app/` coverage is typically **~99%** with branch coverage on).

Coverage floor = “CI fails if too little of `app/` is tested.” Do not lower the floor to “make CI green.”

1. Keep adding or improving tests under `tests/` when you add `app/` code.
2. Run `GATEWAY_API_KEY=test-gateway-key python3 -m pytest tests -q --cov=app --cov-report=term-missing`.
3. Only raise `--cov-fail-under` further after coverage is stably above that number.

- [x] Coverage improved with real tests
- [x] `--cov-fail-under` raised to **98** (above the 95% OSS bar)

---

## 9. How to confirm the uv lockfile workflow works

**DONE IN REPO** when `uv.lock` (and uv-based install docs/CI) are present.  
**YOU MUST DO THIS:** run the frozen install once on your machine to confirm it works.

`uv` is a fast Python package installer. `--frozen` means “install exactly what the lockfile says — do not quietly change versions.”

1. Install [uv](https://github.com/astral-sh/uv) if needed (`curl -LsSf https://astral.sh/uv/install.sh | sh` or your OS package manager).
2. From the repo root (with `uv.lock` present):
   ```bash
   uv sync --frozen
   ```
3. Success = it finishes without resolving/changing the lockfile and without error.
4. If it fails, fix the lockfile/environment in a PR — do not bypass by deleting the lockfile.

- [ ] `uv sync --frozen` succeeds locally

---

## 10. Dashboard Governance Quiz deploy reminder

**YOU MUST DO THIS** if the Step 7 quiz dashboard is not already live.  
**DONE IN REPO:** dashboard app + setup guide exist.

CI can generate the quiz, but **you** take the quiz in a browser after the dashboard is deployed.

1. Follow the full click-path in [`SETUP_GOVERNANCE.md`](SETUP_GOVERNANCE.md) (Vercel project for `dashboard/`, secrets, and GitHub status token).
2. After deploy, open a PR and confirm you can load the study guide / take the quiz in the dashboard UI.
3. Keep Protect Main aligned with governance checks as described in that guide and in section 3 above.

- [ ] Dashboard deployed per `SETUP_GOVERNANCE.md` (or confirmed already deployed)
- [ ] You can open and complete a Governance Quiz for a real PR

---

## Quick links

| Topic | Where |
|-------|--------|
| Enterprise layers overview | [`ENTERPRISE_LAYERS.md`](ENTERPRISE_LAYERS.md) |
| Governance dashboard setup | [`SETUP_GOVERNANCE.md`](SETUP_GOVERNANCE.md) |
| Architecture / roadmap | [`architecture_and_roadmap.md`](architecture_and_roadmap.md) |
| CODEOWNERS | [`.github/CODEOWNERS`](.github/CODEOWNERS) |
| Coverage floor | [`pyproject.toml`](pyproject.toml) (`--cov-fail-under`) |
| Hygiene CI | [`.github/workflows/enterprise-hygiene.yml`](.github/workflows/enterprise-hygiene.yml) |
| FOSSA license scan | [`.github/workflows/fossa-license.yml`](.github/workflows/fossa-license.yml) |
| Locust load smoke | [`perf/README.md`](perf/README.md) |
| Pre-commit config | [`.pre-commit-config.yaml`](.pre-commit-config.yaml) |
