# Enterprise Layers B–E

Automated supply-chain, SAST, product tests, and ship/runtime scaffolding.
These sit **beside** Governance Steps 1–6 (AI Code Guardrail).

| Layer | What | Where |
|-------|------|-------|
| **B** Supply chain & secrets | Dependabot, checksummed Gitleaks, pip-audit, npm audit (high+) | `.github/dependabot.yml`, `.gitleaks.toml`, CI job |
| **C** Static analysis | Ruff, Mypy, Semgrep (custom + packs hard-fail), CodeQL upload, CODEOWNERS | `pyproject.toml`, `.semgrep.yml`, `.github/CODEOWNERS`, CI |
| **D** Product tests | API integration + security contracts + coverage floor (**≥60%**) | `tests/`, `pyproject.toml` coverage config |
| **E** Ship & runtime | Egress-checked HTTP client, audit schema, Dockerfile (non-root)→Trivy CRITICAL+HIGH, SBOM, Terraform→Checkov | `app/security/`, `infra/terraform/`, CI |

## Required CI checks (Protect Main ruleset)

These must stay required on `main`:

1. **`Governance Steps 1–6`**
2. **`Enterprise Layers B–E`**
3. **`CodeQL (Layer C)`**

Also required: **Require review from Code Owners**, **Dismiss stale reviews**.

## Manual follow-ups (GitHub / org settings — you must do)

See the checklist at the bottom of this file. Workflows alone cannot turn on secret push protection, signed commits, or multi-person review.

## Learning map

| Skill | Artifact you can explain in interviews |
|-------|----------------------------------------|
| Dependency risk | Dependabot PRs + `pip-audit` / `npm audit` failing CI |
| Secret hygiene | Gitleaks (checksum-verified) blocking a committed key |
| Lint/types as policy | Ruff + Mypy required on every PR |
| SAST | Semgrep custom + registry ERROR packs + CodeQL security-extended |
| Ownership | CODEOWNERS on `/app/proxy`, `/governance`, workflows |
| Service tests | `tests/test_api_integration.py` with mocked providers |
| Egress control | `EgressCheckedAsyncClient` + deny-by-default allowlist |
| Audit readiness | `app/security/audit.py` + DDL for Phase 3 Postgres |
| Container risk | Non-root image; Trivy CRITICAL+HIGH fails CI; SPDX SBOM artifact |
| IaC security | Checkov on `infra/terraform` |
| Supply-chain CI | Actions pinned to commit SHAs |

---

## Operator checklist — what YOU still configure

### Already done in repo / ruleset (verify stays on)

- [x] Require status checks: Governance Steps 1–6, Enterprise Layers B–E, CodeQL (Layer C)
- [x] Require a pull request before merging
- [x] Require Code Owner review
- [x] Dismiss stale pull request approvals when new commits are pushed
- [x] Block force-pushes / branch deletion on default branch
- [x] Code scanning rule in ruleset (CodeQL high_or_higher / errors)

### Do these in GitHub UI (cannot fully automate)

1. **Secret scanning + push protection**  
   Repo → **Settings** → **Code security** → enable **Secret scanning** and **Push protection**.

2. **Dependabot alerts + security updates**  
   Same page → enable **Dependabot alerts** and **Dependabot security updates** (config file already exists).

3. **Strict status checks (recommended)**  
   Ruleset **Protect Main** → required status checks → enable **Require branches to be up to date before merging**.

4. **Require approval of the most recent push (recommended)**  
   Ruleset → pull request → enable **Require approval of the most recent reviewable push** (stops last-minute malicious commits after approval).

5. **Restrict who can push / bypass**  
   Ruleset → set bypass actors to **none** (or only a break-glass admin). Confirm you cannot bypass as a normal merge path.

6. **Private vulnerability reporting** (optional)  
   Code security → **Private vulnerability reporting**.

7. **Signed commits (org/user)**  
   Enable **Require signed commits** on the ruleset once you have GPG/SSH signing set up locally.

8. **Second human reviewer**  
   When you add a collaborator/team, put them in `.github/CODEOWNERS` for `/app/security/`, `/app/proxy/`, and `/.github/workflows/`. Solo CODEOWNER self-approval is the biggest remaining process gap.

9. **Governance dashboard deploy**  
   Browser quiz gate — see `SETUP_GOVERNANCE.md`.

10. **After merge: confirm CodeQL alerts appear**  
    Repo → **Security** → **Code scanning**. If upload fails on first run, ensure Code scanning is enabled for the private repo (GitHub Advanced Security may be required on some plans).
