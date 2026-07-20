# Task

Add observability scaffolding outside Human Checkpoint #1 for the Phase 1 gateway. The change should introduce correlation ID helpers and request logging that covers health checks and the existing chat route while preserving the `app/proxy/interceptor.py` `NotImplementedError` contract for the human-owned checkpoint.

Scope boundaries: do not attach `correlation_id` or `received_at` inside `intercept_outbound_request`, do not implement the Human Hands-On TODO body, and keep contract tests expecting `NotImplementedError`.

## Rejected Alternate Framings

- Framing this as completing the interceptor was rejected because The Ledger marks Checkpoint #1 as human-owned and blocked on human implementation.
- Framing this as audit persistence was rejected because Phase 3 database work is out of scope.
