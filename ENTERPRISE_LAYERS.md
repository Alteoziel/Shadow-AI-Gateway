# Enterprise Layers B–E

Automated supply-chain, SAST, product tests, and ship/runtime scaffolding.
These sit **beside** Governance Steps 1–6 (AI Code Guardrail).

| Layer | What | Where |
|-------|------|-------|
| **B** Supply chain & secrets | Dependabot (alerts + security updates **enabled**), checksummed Gitleaks, pip-audit, npm audit (high+) | `.github/dependabot.yml`, `.gitleaks.toml`, CI job |
| **C** Static analysis | Ruff, Mypy, Semgrep (custom + packs hard-fail), CodeQL (**Code scanning enabled**, upload on), CODEOWNERS | `pyproject.toml`, `.semgrep.yml`, `.github/CODEOWNERS`, CI |
| **D** Product tests | API integration + security contracts + coverage floor (**≥60%**) | `tests/`, `pyproject.toml` coverage config |
| **E** Ship & runtime | Egress-checked HTTP client, audit schema, Dockerfile (non-root)→Trivy CRITICAL+HIGH, SBOM, Terraform→Checkov | `app/security/`, `infra/terraform/`, CI |

## Required CI checks (Protect Main ruleset)

These must stay required on `main`:

1. **`Governance Steps 1–6`**
2. **`Enterprise Layers B–E`**
3. **`CodeQL (Layer C)`**

Also required on Protect Main: Code Owner review, dismiss stale reviews, up-to-date branch, approval of most recent push, signed commits, CodeQL code-scanning gate, Preview deployment.

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

## Operator checklist

### Done (repo settings + Protect Main — keep these on)

- [x] Require status checks: Governance Steps 1–6, Enterprise Layers B–E, CodeQL (Layer C)
- [x] Require a pull request before merging
- [x] Require Code Owner review
- [x] Dismiss stale pull request approvals when new commits are pushed
- [x] Require approval of the most recent reviewable push
- [x] Require branches to be up to date before merging (strict status checks)
- [x] Block force-pushes / branch deletion on default branch
- [x] Require signed commits
- [x] Code scanning rule in ruleset (CodeQL high_or_higher / errors)
- [x] **Code scanning enabled** (repo Code security) — CodeQL workflow uploads SARIF
- [x] **Dependabot alerts + security updates enabled** (repo Code security; `.github/dependabot.yml` present)
- [x] Required Preview deployment (`Preview – shadow-ai-gateway`)

### Still optional / later

1. **Secret scanning + push protection**  
   Repo → **Settings** → **Code security** → enable **Secret scanning** and **Push protection** (if not already on).

2. **Restrict who can push / bypass**  
   Ruleset → set bypass actors to **none** (or only a break-glass admin).

3. **Private vulnerability reporting** (optional)  
   Code security → **Private vulnerability reporting**.

4. **Second human reviewer**  
   When you add a collaborator/team, put them in `.github/CODEOWNERS` for `/app/security/`, `/app/proxy/`, and `/.github/workflows/`. Solo CODEOWNER self-approval is the biggest remaining process gap.

5. **Governance dashboard deploy**  
   Browser quiz gate — see `SETUP_GOVERNANCE.md`.
