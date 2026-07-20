# Research Questions

## Context

Focus on the Step 7 dashboard, its route handlers, local store, deployment docs, and the repository guardrails that constrain storage and human-owned checkpoint work. Describe existing behavior and contracts without proposing implementation details.

## Questions

1. How does the dashboard currently authenticate CI ingest requests and reviewer mutation requests?
2. How does the dashboard currently display reviewer unlock state, quiz status, and approve/merge locking?
3. How does the dashboard ingest, persist, sanitize, and update review records?
4. What deployment and environment variable instructions already exist for the dashboard in repository docs?
5. What repository guardrails constrain database work, Vercel usage, and the human-owned interceptor checkpoint?
