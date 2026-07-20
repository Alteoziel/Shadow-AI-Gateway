# Task

Harden the Step 7 dashboard so it is deployable and operationally clear without moving beyond the Ledger's current phase. The work keeps `.data/reviews.json` as the default store, preserves the Step 6 quiz pass requirement for approve/merge, improves auth unlock and ingest failure visibility, and aligns `dashboard/.env.example` plus `dashboard/README.md` with Ledger §11.C.

## Scope Boundaries

- Do not implement `app/proxy/interceptor.py`.
- Do not migrate the dashboard to Supabase or Postgres.
- Do not add a request interceptor, middleware, or proxy layer.
- Optional deploy metadata is allowed only for the dashboard.

## Rejected Alternate Framings

- "Add production database now" was rejected because Ledger §0 says the dashboard starts on `.data/reviews.json` and Supabase belongs to Phase 3.
- "Use Vercel middleware for auth" was rejected because the task explicitly says not to implement an interceptor and the existing route handlers already gate mutations.

## Stage Isolation Note

Artifacts in this directory are the context handoff between QRSPI stages. No extra subagents were spawned because this run is itself a subagent and the parent-agent reminder forbids spawning additional subagents unless requested by the user or by higher-priority instructions.
