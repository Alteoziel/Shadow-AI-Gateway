# Task

Add Gateway-specific AST governance coverage for Ledger §11.E.1 by extending the existing governance AST guardrail and tests. The change must flag synchronous `httpx` / `requests` usage under `app/`, optionally verify the chat route calls the interceptor before provider dispatch, keep `ai-guardrail --skip-llm` green, preserve `.github/workflows/ai-guardrail.yml`, and leave `app/proxy/interceptor.py` untouched.

## Constraints

- Base branch: `origin/cursor/qrspi-ledger-land-5e0d`.
- Implementation branch: `cursor/gov-ast-gateway-rules-5e0d`.
- Artifact directory: `thoughts/qrspi/2026-07-20-gov-ast-gateway-rules/`.
- Do not implement or edit `app/proxy/interceptor.py`.
- Do not disable `.github/workflows/ai-guardrail.yml`.
- Task tool is unavailable in this environment, so QRSPI is preserved by strict stage order and file-boundary artifacts.

## Rejected Alternate Framings

- Rejected framing the work as runtime gateway behavior because the requested scope is governance/static analysis.
- Rejected framing the work as an interceptor implementation because the Ledger keeps that file human-owned.
- Rejected broad dependency-policy enforcement outside `app/` because the task is gateway-specific.
