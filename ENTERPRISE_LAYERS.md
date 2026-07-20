# Enterprise Layers B–E

Automated supply-chain, SAST, product tests, and ship/runtime scaffolding.
These sit **beside** Governance Steps 1–6 (AI Code Guardrail).

| Layer | What | Where |
|-------|------|-------|
| **B** Supply chain & secrets | Dependabot, Gitleaks, pip-audit, npm audit (high+ soft until deps cleaned) | `.github/dependabot.yml`, `.gitleaks.toml`, CI job |
| **C** Static analysis | Ruff, Mypy, Semgrep, CodeQL, CODEOWNERS | `pyproject.toml`, `.semgrep.yml`, `.github/CODEOWNERS`, CI |
| **D** Product tests | API integration + security contracts + coverage floor (45%) | `tests/`, `pyproject.toml` coverage config |
| **E** Ship & runtime | Egress allowlist, audit schema, Dockerfile→Trivy, Terraform→Checkov | `app/security/`, `infra/terraform/`, CI |

## CI check name (branch protection)

Require this additional status check on `main`:

**`Enterprise Layers B–E`**

(plus existing **`Governance Steps 1–6`**)

CodeQL runs as a sibling job: **`CodeQL (Layer C)`** — also require it when it appears after the first green run.

## Manual follow-ups (cannot automate fully)

1. Branch protection → require `Enterprise Layers B–E` (+ CodeQL when listed)
2. Branch protection → **Require review from Code Owners** (uses `.github/CODEOWNERS`)
3. Repo → Settings → Code security → enable **Secret scanning** / push protection (GitHub UI)
4. Deploy governance dashboard (browser quiz) — see `SETUP_GOVERNANCE.md`

## Learning map

| Skill | Artifact you can explain in interviews |
|-------|----------------------------------------|
| Dependency risk | Dependabot PRs + `pip-audit` / `npm audit` failing CI |
| Secret hygiene | Gitleaks blocking a committed key |
| Lint/types as policy | Ruff + Mypy required on every PR |
| SAST | Semgrep custom rules + CodeQL security-extended |
| Ownership | CODEOWNERS on `/app/proxy` and `/governance` |
| Service tests | `tests/test_api_integration.py` with mocked providers |
| Egress control | `app/security/egress.py` deny-by-default allowlist |
| Audit readiness | `app/security/audit.py` + DDL for Phase 3 Postgres |
| Container risk | Trivy CRITICAL fails the image build job (HIGH tracked via Dependabot) |
| IaC security | Checkov on `infra/terraform` |
