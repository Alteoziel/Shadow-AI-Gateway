# Research Findings

## Q1: What QRSPI playbook files, agent templates, and artifact docs exist, and how do they define stage sequencing, allowed inputs, autonomous behavior, and context isolation?

### Findings
- `.cursor/qrspi/README.md` is the canonical QRSPI playbook directory for this repository and says it is law via the Ledger. `.cursor/qrspi/README.md:3-6`
- The QRSPI stage sequence is Question -> Research -> Design -> Structure -> Plan -> Worktree -> Implement -> PR. `.cursor/qrspi/README.md:1-19`
- The stage table defines allowed artifact inputs: Research receives only `questions.md` and never `task.md`; Design receives `task.md`, `questions.md`, and `research.md`; Implement uses `plan.md` as primary input. `.cursor/qrspi/README.md:10-19`
- The listed subagent templates are `codebase-locator`, `codebase-analyzer`, `codebase-pattern-finder`, and `web-search-researcher`. `.cursor/qrspi/README.md:21-28`
- The artifact layout is `thoughts/qrspi/<YYYY-MM-DD-brief-description>/` with `task.md`, `questions.md`, `research.md`, `design.md`, `structure.md`, and `plan.md`. `.cursor/qrspi/README.md:39-50`
- `thoughts/qrspi/README.md` repeats the per-task artifact layout and links back to the QRSPI README and Ledger. `thoughts/qrspi/README.md:1-15`
- Every stage playbook header says autonomous agents do not wait for human approval, follow `AUTONOMOUS_MODE.md`, enforce `CONTEXT_ISOLATION.md`, run in a fresh subagent with only README-listed inputs, and treat the Ledger as law. `.cursor/qrspi/1_question.md:6-10`, `.cursor/qrspi/2_research.md:6-10`, `.cursor/qrspi/3_design.md:6-10`
- Question writes `task.md` and `questions.md`, with `questions.md` forbidden from containing the task description, goals, or desired behavior. `.cursor/qrspi/1_question.md:43-57`, `.cursor/qrspi/1_question.md:70-74`
- Research reads only `$ARGUMENTS/questions.md`, must not read `task.md`, spawns locator/analyzer/pattern-finder agents, and writes `research.md`. `.cursor/qrspi/2_research.md:16-20`, `.cursor/qrspi/2_research.md:23-37`, `.cursor/qrspi/2_research.md:39-60`
- Design reads `task.md`, `questions.md`, and `research.md`, lists 3-5 autonomous design questions with chosen answers, and writes `design.md`. `.cursor/qrspi/3_design.md:16-30`, `.cursor/qrspi/3_design.md:34-59`
- Structure reads `design.md` and `research.md`, creates independently testable vertical slices, and writes `structure.md`. `.cursor/qrspi/4_structure.md:16-20`, `.cursor/qrspi/4_structure.md:23-43`
- Plan reads `structure.md`, `design.md`, and `research.md`, requires concrete verification commands, resolves open questions autonomously, and writes `plan.md`. `.cursor/qrspi/5_plan.md:16-19`, `.cursor/qrspi/5_plan.md:22-74`
- Worktree creates an isolated worktree or feature branch and copies QRSPI artifacts; it explicitly does not implement. `.cursor/qrspi/6_worktree.md:17-38`, `.cursor/qrspi/6_worktree.md:47-50`
- Implement reads only `plan.md` first, executes one phase at a time, verifies each phase, updates plan checkboxes, and commits after automated verification. `.cursor/qrspi/7_implement.md:15-39`, `.cursor/qrspi/7_implement.md:55-65`
- PR reads `design.md`, gathers diff/log data, and requires PR body references to the Ledger, `design.md`, `plan.md`, and Autonomous Mode. `.cursor/qrspi/8_pr.md:15-31`
- `AUTONOMOUS_MODE.md` disables QRSPI human approval waits and says the agent chooses grounded options and proceeds, while product Human-in-the-Loop checkpoints remain human-owned. `.cursor/qrspi/AUTONOMOUS_MODE.md:1-17`, `.cursor/qrspi/AUTONOMOUS_MODE.md:62-66`
- `CONTEXT_ISOLATION.md` requires fresh subagents per stage, file-scoped inputs only, forbids Research from receiving `task.md`, and states disk artifacts are the API between stages. `.cursor/qrspi/CONTEXT_ISOLATION.md:1-24`, `.cursor/qrspi/CONTEXT_ISOLATION.md:26-37`
- The locator template is a file-finder that documents where code exists and explicitly avoids analysis or suggestions. `.cursor/qrspi/agents/codebase-locator.md:1-16`
- The analyzer template traces implementation details with `file:line` references and explicitly avoids recommendations. `.cursor/qrspi/agents/codebase-analyzer.md:1-18`, `.cursor/qrspi/agents/codebase-analyzer.md:115-124`
- The pattern-finder template finds concrete examples and existing patterns while avoiding critique or recommendations. `.cursor/qrspi/agents/codebase-pattern-finder.md:1-17`

## Q2: How does `architecture_and_roadmap.md` currently define the operational protocol, agent workflow requirements, and human hands-on checkpoint boundaries?

### Findings
- The Ledger labels itself the single source of truth for agents, humans, and reviewers. `architecture_and_roadmap.md:1-9`
- Current project state is Phase 1 Crawl, with Checkpoint #1 in `app/proxy/interceptor.py` blocked on human work. `architecture_and_roadmap.md:3-9`
- The pre-merge gate is in progress and includes Step 6 comprehension plus Step 7 dashboard human review. `architecture_and_roadmap.md:19-37`
- Step 6 is documented as a study guide plus quiz over vocabulary, flow, dependencies, manual tasks, functions, and security, with an 80% pass bar on the dashboard or local CLI practice. `architecture_and_roadmap.md:39-49`
- The Ledger says branch protection must require `Governance Steps 1-6`; until then, PRs can still merge without that check. `architecture_and_roadmap.md:63-65`, `architecture_and_roadmap.md:352-362`
- The agent hierarchy names Opus as "THE BRAIN", Grok as "SENIOR ENGINEER", Composer/Auto as "THE DOER / ACHIEVER", and GPT-5.6 Sol as "THE SECURITY CHIEF". `architecture_and_roadmap.md:92-101`
- The default cycle is Grok designs, Composer builds, Grok reviews, Human fills checkpoint, validation scripts run. `architecture_and_roadmap.md:101`
- Phase 1's human checkpoint is raw outbound client payload interception before any upstream provider call. `architecture_and_roadmap.md:110-123`
- Phase 2, Phase 3, and Phase 4 each reserve a human-owned checkpoint for scrubbing loop, SQL/schema insertion work, and Docker/Terraform resources respectively. `architecture_and_roadmap.md:148-161`, `architecture_and_roadmap.md:165-178`, `architecture_and_roadmap.md:183-195`
- The operational protocol says agents map file modifications, generate boilerplate, never auto-complete human checkpoint implementations, inject `TODO: Human Hands-On Implementation`, provide a three-bullet cheat sheet, and validate after human completion. `architecture_and_roadmap.md:210-225`
- Checkpoint #1 scope permits validation of `model` and `messages`, attaching `correlation_id` and `received_at`, and returning upstream-ready payload; it forbids scrubbing and DB inserts. `architecture_and_roadmap.md:228-246`
- The active checkpoint call site requirement says `app/api/v1/chat.py` must always invoke `intercept_outbound_request` before provider streaming. `architecture_and_roadmap.md:248`
- `app/proxy/interceptor.py` contains the Human Checkpoint #1 docstring, `TODO: Human Hands-On Implementation`, scope notes, and a `NotImplementedError`. `app/proxy/interceptor.py:5-39`
- `app/api/v1/chat.py` imports the interceptor, calls it before resolving the provider, and converts `NotImplementedError` to HTTP 501. `app/api/v1/chat.py:7-23`, `app/api/v1/chat.py:89-101`
- Tests assert the interceptor is async, still raises `NotImplementedError`, and appears in the route before provider-related usage. `tests/test_interceptor_contract.py:10-19`, `tests/test_interceptor_contract.py:21-44`
- Routing tests assert chat returns 501 while the interceptor is not implemented and forwards to the provider after the interceptor is patched to return a normalized payload. `tests/test_proxy_routing.py:16-23`, `tests/test_proxy_routing.py:26-63`

## Q3: Where do `README.md`, `SETUP_GOVERNANCE.md`, governance docs, and dashboard docs reference the Ledger, setup checklist, and governance gate responsibilities?

### Findings
- Root `README.md` tells readers to read `architecture_and_roadmap.md` first and calls it the single source of truth for phases, checkpoints, and guardrails. `README.md:1-5`
- Root `README.md` lists the pre-merge suite as AST, OWASP, Fuzz, Big-O, Copyright, Comprehension quiz, and Human review/merge. `README.md:7-18`
- Root `README.md` points the human setup checklist to Ledger §11 and `SETUP_GOVERNANCE.md`. `README.md:14-18`
- Root `README.md` documents local governance commands including `ai-guardrail run` and `ai-guardrail quiz`. `README.md:20-22`
- Root `README.md` says Phase 1 status includes the governance suite, CI, and review dashboard scaffold, with Ledger §0 as the reference. `README.md:25-30`
- Root `README.md` points project layout to Ledger §7. `README.md:107-109`
- `SETUP_GOVERNANCE.md` says the seven-step suite will not protect `main` until setup is completed. `SETUP_GOVERNANCE.md:1-7`
- `SETUP_GOVERNANCE.md` tells the human to require the status check named `Governance Steps 1-6` and says the workflow is advisory until that is enabled. `SETUP_GOVERNANCE.md:9-17`
- `SETUP_GOVERNANCE.md` says Step 6 still builds a beginner study guide and quiz without an API key, and LLM credentials make Step 2 and Step 6 richer. `SETUP_GOVERNANCE.md:19-32`
- `SETUP_GOVERNANCE.md` lists dashboard host secrets, GitHub token requirements, and Actions secrets for dashboard POST. `SETUP_GOVERNANCE.md:44-62`
- `SETUP_GOVERNANCE.md` shows the PR flow: Actions runs Steps 1-5, Step 6 generates the quiz, posts report to dashboard, then the reviewer reads the guide and passes at >=80% before Step 7 unlocks. `SETUP_GOVERNANCE.md:75-89`
- `SETUP_GOVERNANCE.md` points full detail to `architecture_and_roadmap.md` §0 and §11. `SETUP_GOVERNANCE.md:97-103`
- `governance/README.md` describes the Python CLI as Steps 1-6 and maps Step 6 to `governance.steps.comprehension_gate`. `governance/README.md:1-14`
- `governance/README.md` says Step 7 lives in `/dashboard` and merge stays locked until the Step 6 quiz passes at >=80%. `governance/README.md:12-14`
- `dashboard/README.md` describes the dashboard as Step 7, receiving reports from the Python governance CLI and merging via GitHub REST API. `dashboard/README.md:1-7`
- `dashboard/README.md` says Step 6 comprehension must pass at >=80% before approve/merge unlocks. `dashboard/README.md:6`
- `.github/workflows/ai-guardrail.yml` defines a pull request workflow to `main` with job name `Governance Steps 1-6`. `.github/workflows/ai-guardrail.yml:1-15`

## Q4: How are Step 6 comprehension quiz requirements represented across the governance CLI or pipeline, dashboard routes or components, and docs?

### Findings
- `comprehension_gate.py` defines Step 6 as a beginner study guide plus understanding quiz before human review/merge, covering vocabulary, how it works, bigger picture, dependencies, manual tasks, functions, and security. `governance/governance/steps/comprehension_gate.py:1-7`, `governance/governance/steps/comprehension_gate.py:86-94`
- The Step 6 pass threshold constant is `0.8`. `governance/governance/steps/comprehension_gate.py:21-24`
- The deterministic pack includes `learner_level`, `pass_threshold`, a `study_guide`, and generated `questions`. `governance/governance/steps/comprehension_gate.py:299-317`
- Quiz questions are tagged with category labels from the category map. `governance/governance/steps/comprehension_gate.py:86-94`, `governance/governance/steps/comprehension_gate.py:320-337`
- Built-in questions include pre-flight, gateway, phases, why the quiz exists, request flow, dependencies, human checkpoint behavior, secrets, and AI-code review risk. `governance/governance/steps/comprehension_gate.py:340-550`
- Optional LLM enrichment uses `GOVERNANCE_LLM_API_KEY` or `OPENAI_API_KEY`, asks for extra glossary and questions, and changes the generator to `deterministic+llm`. `governance/governance/steps/comprehension_gate.py:552-638`
- `grade()` compares submitted answers to `answer_index`, calculates score, and passes if score is at least the pack threshold. `governance/governance/steps/comprehension_gate.py:640-672`
- `run()` returns an info finding telling the reviewer to complete the quiz before Approve & Merge, adds manual-task warnings, and sets `StepResult.passed=True` when generation succeeds. `governance/governance/steps/comprehension_gate.py:680-723`
- The pipeline runs comprehension after AST, security, fuzz, benchmark, and copyright steps, and adds summary fields `comprehension_required=True` and a note that Step 6 must pass on the dashboard before Step 7 merge. `governance/governance/pipeline.py:109-158`
- The CLI `run` command prints that the Step 6 quiz must still pass on the dashboard before merge. `governance/governance/cli.py:73-103`
- The CLI `quiz` command renders the study guide, glossary, manual tasks, security notes, quiz prompts, and grading result locally. `governance/governance/cli.py:154-227`
- Dashboard store types include `ComprehensionPack`, `ComprehensionAttempt`, `comprehension_passed`, and `pending_comprehension` status. `dashboard/src/lib/store.ts:36-96`
- Dashboard ingest extracts the `comprehension_gate` metrics pack, fingerprints quiz material, initializes status as `pending_comprehension`, and resets the pass when the quiz pack changes. `dashboard/src/lib/store.ts:117-134`, `dashboard/src/lib/store.ts:213-287`
- Dashboard client sanitization strips `answer_index` and `explanation` from the public comprehension pack. `dashboard/src/lib/store.ts:136-171`
- Dashboard grading uses the hidden answer keys server-side and sets pass based on score >= threshold. `dashboard/src/lib/store.ts:174-192`
- `POST /api/reviews/:id` action `submit_quiz` grades the quiz, updates `comprehension_passed`, and sets status to `pending_review` or `pending_comprehension`. `dashboard/src/app/api/reviews/[id]/route.ts:25-82`
- The same route blocks approve/merge when no quiz exists or when `comprehension_passed` is false. `dashboard/src/app/api/reviews/[id]/route.ts:96-120`
- The merge action also requires the automated suite to have passed before calling GitHub's merge API. `dashboard/src/app/api/reviews/[id]/route.ts:133-179`
- `ReviewPanel` displays a no-quiz lock message, a passed message, the study guide, quiz form, and submit button. `dashboard/src/components/ReviewPanel.tsx:190-410`
- `ReviewActions` disables Approve when the quiz is locked and disables Approve & Merge when either the quiz is locked or the suite failed. `dashboard/src/components/ReviewPanel.tsx:413-479`
- The dashboard home text says users pass the beginner quiz, then review automated reports before merging to `main`. `dashboard/src/app/page.tsx:24-38`

## Q5: What distinguishes the comprehension quiz gate from GitHub Actions status checks in the existing documentation and implementation?

### Findings
- Documentation names the GitHub check `Governance Steps 1-6`, while Step 7 dashboard handles human review and merge. `.github/workflows/ai-guardrail.yml:1-15`, `dashboard/README.md:1-7`
- The workflow runs unit tests, then `ai-guardrail run --root ..`, writes JSON/Markdown reports, optionally comments on PRs, and optionally posts to the dashboard. `.github/workflows/ai-guardrail.yml:31-80`
- Pipeline pass/fail is computed from `StepResult.passed` or `skipped` across steps, not from a human quiz attempt. `governance/governance/pipeline.py:109-139`
- Step 6 generation returns `passed=True` once the quiz pack is generated; the comment says human pass is enforced on the dashboard. `governance/governance/steps/comprehension_gate.py:716-723`
- The CLI explicitly prints that the Step 6 quiz must still be passed on the dashboard before merge after reporting overall suite pass/fail. `governance/governance/cli.py:90-103`
- Dashboard POST is non-blocking for CI: reporter docs say dashboard outages must not fail an otherwise-green CI job, and exceptions return `{ok: False}` instead of raising. `governance/governance/reporters/github.py:116-137`
- `SETUP_GOVERNANCE.md` describes Actions as running Steps 1-5 and generating Step 6, then POSTing to the dashboard where the reviewer reads the guide and takes the >=80% quiz. `SETUP_GOVERNANCE.md:75-89`
- The Ledger says branch protection requires the Actions check, and separately says even with CI green, the dashboard Step 6 quiz must pass before merge. `architecture_and_roadmap.md:352-362`
- Dashboard route code enforces the human quiz pass before approve/merge, and separately enforces the automated suite pass before merge. `dashboard/src/app/api/reviews/[id]/route.ts:96-145`
- Dashboard UI text distinguishes "Step 7 approve/merge is unlocked" from "suite must also be green to merge." `dashboard/src/components/ReviewPanel.tsx:216-229`
- Dashboard action locks compute `quizLocked` from missing/failed comprehension and `mergeLocked` from quiz lock or suite failure. `dashboard/src/components/ReviewPanel.tsx:443-479`

## Q6: What files on `origin/cursor/architecture-ledger-bf7f` differ from the working branch for QRSPI docs, QRSPI artifacts, Ledger content, README content, and setup governance documentation?

### Findings
- The content differences identified in the scoped tracked comparison are in `README.md`, `SETUP_GOVERNANCE.md`, and `architecture_and_roadmap.md`; the changed line pairs are listed in the findings below. `README.md:5`, `README.md:14-22`, `SETUP_GOVERNANCE.md:64-75`, `architecture_and_roadmap.md:1-9`
- The target branch and current branch both contain the QRSPI playbook README with the same stage table and helper-agent list, and both contain the QRSPI artifact README layout. `origin/cursor/architecture-ledger-bf7f:.cursor/qrspi/README.md:1-51`, `.cursor/qrspi/README.md:1-50`, `origin/cursor/architecture-ledger-bf7f:thoughts/qrspi/README.md:1-15`, `thoughts/qrspi/README.md:1-15`
- On the target branch, `README.md` had both a Ledger read-first line and a Task process line pointing to `.cursor/qrspi/`; current `README.md` has only the Ledger read-first line in that block. `origin/cursor/architecture-ledger-bf7f:README.md:5-6`, `README.md:5`
- On the target branch, the root README's GitHub Action row named the check `Governance Steps 1-6`; current `README.md` lists the workflow path without the check-name phrase. `origin/cursor/architecture-ledger-bf7f:README.md:16-18`, `README.md:14-18`
- On the target branch, the README quiz command comment said the understanding test is not graded inside Actions; current README calls it practice understanding the change. `origin/cursor/architecture-ledger-bf7f:README.md:21-26`, `README.md:20-22`
- On the target branch, `SETUP_GOVERNANCE.md` had an unnumbered "Local dry-run anytime" heading and an explicit note that the GitHub check proves quiz generation but not the human pass. `origin/cursor/architecture-ledger-bf7f:SETUP_GOVERNANCE.md:64-75`
- Current `SETUP_GOVERNANCE.md` numbers that heading as "5. Local dry-run anytime" and keeps only the practice quiz command before the PR-flow section. `SETUP_GOVERNANCE.md:64-75`
- On the target branch, the Ledger opened with "THE LEDGER IS LAW", explicit conflict precedence, mandatory QRSPI, and task workflow status. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:1-17`
- Current Ledger opens with a shorter "THE LEDGER" statement and does not include the target branch's top-level `Task workflow` status line. `architecture_and_roadmap.md:1-9`
- On the target branch, Ledger §0 had a "How Step 6 is tracked" subsection that explicitly said GitHub Actions does not grade the human and described local/dashboard proof of understanding. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:48-64`
- Current Ledger §0 instead documents Step 6 purpose, study guide, quiz categories, pass bar, and Step 7 unlock without the same "Actions does not grade you" heading. `architecture_and_roadmap.md:39-65`
- On the target branch, Ledger §5 was "Operational Protocol - QRSPI Is Mandatory" with stage table, mermaid flow, autonomous mode, context isolation, and product learning checkpoint subsections. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:218-282`
- Current Ledger §5 is "Operational Protocol (Every Developmental Cycle)" and lists design/plan, boilerplate, learning checkpoint TODO, cheat sheet, human implementation, and validation steps. `architecture_and_roadmap.md:210-225`
- On the target branch, Ledger §7 included `SETUP_GOVERNANCE.md`, `.cursor/qrspi/`, and `thoughts/qrspi/` in the target layout; current Ledger §7 does not list those paths in the displayed tree. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:311-318`, `architecture_and_roadmap.md:253-260`
- On the target branch, non-negotiable guardrails included mandatory QRSPI, fresh subagent per stage, autonomous QRSPI gates, the named `Governance Steps 1-6` check, and comprehension pass before human review. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:361-376`
- Current non-negotiable guardrails omit those QRSPI-specific bullets and refer more generally to the AI Guardrail check once branch protection is enabled. `architecture_and_roadmap.md:299-310`
- The current research artifact exists in the QRSPI run directory and is outside the target branch's tracked artifact README layout until tracked. `thoughts/qrspi/2026-07-20-qrspi-ledger-land/research.md:1-140`, `origin/cursor/architecture-ledger-bf7f:thoughts/qrspi/README.md:1-15`

## Cross-Cutting Observations

- QRSPI documentation and Ledger documentation both preserve the same human checkpoint boundary: autonomous QRSPI replaces process approval waits, but not product checkpoint implementation by the human. `.cursor/qrspi/AUTONOMOUS_MODE.md:1-17`, `.cursor/qrspi/AUTONOMOUS_MODE.md:62-66`, `architecture_and_roadmap.md:210-225`
- The code, tests, and Ledger align on Checkpoint #1 being active in `app/proxy/interceptor.py`, with provider forwarding blocked by `NotImplementedError`/501 until the checkpoint is filled. `architecture_and_roadmap.md:228-248`, `app/proxy/interceptor.py:5-39`, `app/api/v1/chat.py:89-101`, `tests/test_proxy_routing.py:16-23`
- The governance implementation treats Step 6 as generated evidence inside the CI suite and as a human pass/fail gate in the dashboard. `governance/governance/steps/comprehension_gate.py:716-723`, `governance/governance/pipeline.py:151-154`, `dashboard/src/app/api/reviews/[id]/route.ts:96-120`
- Documentation consistently places dashboard actions after the comprehension quiz and also keeps automated suite pass as a merge condition. `governance/README.md:12-14`, `dashboard/README.md:1-7`, `dashboard/src/components/ReviewPanel.tsx:443-479`
- The scoped comparison against `origin/cursor/architecture-ledger-bf7f` shows the target branch had more explicit QRSPI-as-Ledger-law language in `architecture_and_roadmap.md` and more explicit Actions-vs-quiz wording in README/setup docs. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:218-282`, `origin/cursor/architecture-ledger-bf7f:README.md:21-26`, `origin/cursor/architecture-ledger-bf7f:SETUP_GOVERNANCE.md:64-75`

## Open Areas

- The scoped tracked comparison did not surface content differences in the QRSPI playbook README or QRSPI artifact README; branch and current line references match for those docs. `origin/cursor/architecture-ledger-bf7f:.cursor/qrspi/README.md:1-51`, `.cursor/qrspi/README.md:1-50`, `origin/cursor/architecture-ledger-bf7f:thoughts/qrspi/README.md:1-15`, `thoughts/qrspi/README.md:1-15`
- Runtime behavior of a deployed dashboard was not inspected; repository findings come from dashboard source routes, components, and docs. `dashboard/src/app/api/reviews/[id]/route.ts:25-145`, `dashboard/src/components/ReviewPanel.tsx:190-479`, `dashboard/README.md:1-30`
