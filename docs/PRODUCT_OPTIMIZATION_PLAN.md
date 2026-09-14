# KnowYourCompany: product optimization and implementation plan

Prepared 14 September 2026. This document preserves the original audit and implementation plan. See [the implementation checkpoint](IMPLEMENTATION_CHECKPOINT.md) for current changes, verification and outstanding launch gates.

## Product direction

Build an evidence-backed interview preparation workspace for students and early-career candidates. Interpret “entrepreneur kind of project” as making the existing product commercially usable, rather than changing its audience to entrepreneurs.

Core promise: understand a company, choose a relevant career direction, and leave with a credible preparation brief. The differentiator should be traceable company facts plus useful preparation guidance. A new visual identity supports that promise; it does not replace it.

Keep Next.js, FastAPI, LangGraph and Supabase. A framework rewrite is unnecessary. Start with a focused private beta, then validate repeat usage and willingness to pay before building subscriptions or institution administration.

## Audit findings

| Priority | Finding and repository evidence | Consequence / action |
|---|---|---|
| P0 | `backend/main.py`: PDF routes accept arbitrary existing filesystem paths and external redirect URLs. Storage URLs are signed from caller-supplied paths with a privileged client. | Local readable files can be served through these routes; report access has no ownership boundary. Replace paths with opaque report IDs, authorize access, and constrain development fallback to the report directory. Remove arbitrary redirects. |
| P0 | `backend/main.py`: no authentication, ownership checks, rate limits or selected-domain membership checks. | Public requests can consume paid provider capacity; knowledge of a thread ID enables resume attempts. Add scoped anonymous sessions or accounts, quotas, validation and per-run mutation locking. |
| P1 | `tools/exa_search.py` returns `content`; `agent/services/search.py` reads `text` for Exa. | Exa content becomes empty before evidence filtering. Fix the normalized contract before comparing quality or reducing source volume. |
| P1 | `company.py` and `domain.py` each loop over five queries sequentially. Only the two providers inside each query run concurrently. | Eleven query rounds across identity, company and domain mean 22 provider requests before retries on the normal full path. Use bounded concurrency across queries and a process-wide provider budget. |
| P1 | The normal path contains five company-stage AI calls and two domain-stage AI calls, including the two relevance filters. | Seven sequential AI calls add latency and expense. Company report and domain generation both depend on analysis, not each other. Consolidate structured output or execute independent work concurrently after evaluating quality. |
| P1 | Exa requests full page text; filtering and analysis include uncapped content. | Context size grows with retrieved pages. Select relevant excerpts and enforce a measured token budget while preserving source diversity. |
| P1 | Exa uses a 30-second timeout with three attempts; Gemini permits SDK retries and traverses four fallback models for certain failures. | Slow providers can create long tails. Introduce explicit stage/run deadlines and one coordinated retry policy. Verify configured model availability in the deployment account. |
| P1 | `parallel_search` requires both futures to succeed. | One provider failure discards the useful outcome of the other. Preserve partial evidence with a warning and quality gate. |
| P1 | Both research endpoints call `graph.invoke` and return only after a phase finishes. | The browser cannot show actual work in progress; a long HTTP request is the entire user experience. Add durable runs, status events and reconnect support. These are synchronous FastAPI routes; the problem is occupied request-worker capacity, not direct blocking of an async event loop. |
| P1 | `page.tsx` has one `loading` flag and local-only session state. | No stage visibility, refresh recovery, cancellation or robust retry flow. Replace with explicit run states and a session-aware research hook. |
| P1 | Insufficient company evidence routes to END but the endpoint reports `completed`; the frontend says research completed. | No useful distinction between successful research and insufficient evidence. Return a distinct terminal outcome with a recovery suggestion. |
| P1 | Citation IDs are requested in analysis prompts, but final report rewriting does not explicitly preserve them; PDF generation receives no source registry. | Readers cannot reliably resolve citations. Render web and PDF reports from a shared structured brief and source registry. |
| P1 | Identity is free-form text and the graph does not gate on identity ambiguity. | A weak or ambiguous match can proceed. Parse identity into a schema and ask users to choose a match when evidence does not resolve it. |
| P2 | Postgres initialization happens at import and silently falls back to memory after failure. | Persistence can disappear in production; checkpoints alone do not restart interrupted execution. Require persistent storage in production and introduce worker recovery. |
| P2 | Exceptions are returned to clients; broad Vercel-origin CORS matching is enabled. | Exposes internal details and permits more browser origins than intended. Use safe errors with correlation IDs and explicit origins; CORS is not authorization. |
| P2 | PDF upload checks buckets on every report; both browser actions prefer the same signed URL. | Avoidable storage work; download behavior is not explicitly enforced and links expire. Provision storage once and refresh authorized download/view links separately. |
| P2 | Tests are provider smoke scripts; `test_search.py` calls a live API at import. Python dependencies are unpinned. | Tests cannot reliably run offline and installs are not reproducible. Add isolated regression tests, dependency locking and CI. |
| P2 | UI is a centered dark hero, gradient text, glow and repeated cards. Metadata remains “Create Next App”; the input has no explicit label and outline is removed. | Weak brand identity, accessibility and product polish. Introduce the dossier design below, proper metadata and accessible controls. |

The existing strengths are worth preserving: identity-first research, URL deduplication, batched relevance filtering, insufficient-evidence routing, checkpointed domain selection and private storage intent.

## 1. Make waiting understandable

Use backend events to drive progress. Do not cycle invented stages on a timer or display fabricated percentage completion.

| Actual event | User-facing copy |
|---|---|
| Run accepted | “Your research is queued.” |
| Identity search starts | “Finding the right company and its official website.” |
| Company queries start | “Checking products, business areas and recent developments.” |
| A query finishes | “Completed 3 of 5 research searches.” Only show real counts. |
| Relevance filtering starts | “Separating relevant sources from companies with similar names.” |
| Analysis starts | “Connecting the evidence into your company brief.” |
| Domain choices ready | “Your company brief is ready. Choose where you want to focus.” |
| Domain queries start | “Checking how this career area connects to the company.” |
| Domain analysis starts | “Building your preparation priorities from the evidence.” |
| PDF rendering starts | “Preparing your downloadable report.” |
| One provider fails | “One source service is unavailable. Research is continuing with the available sources.” |
| No recent progress | “This step is taking longer than usual.” Show last real update and recovery controls. |

Display the current stage, elapsed time, completed milestones, actual source counts and the next expected step. Heartbeats establish connection health, not work completion. Only claim a finding after its evidence has been checked. Allow optional educational tips clearly separate from live status.

Use `aria-live="polite"` for stage changes, avoid announcing the elapsed timer every second, preserve keyboard focus, and respect reduced motion. Provide explicit insufficient-evidence, retryable-error, cancelled and expired-session screens.

## 2. Reduce real latency and cost

First instrument provider duration, node duration, queue delay, retry counts, input/output tokens, cache hits, time to first useful brief, total duration and cost per successful brief. Record warm and cold starts separately. No measured baseline currently exists in this audit; README timing is not benchmark evidence.

Apply optimizations in this order:

1. Fix Exa normalization and lock the evidence contract with a regression test.
2. Run independent query/provider work through a bounded shared executor or verified async clients. Start conservatively with three query slots and provider-specific global limits; avoid nested unbounded pools. Preserve deterministic source ordering after completion.
3. Enforce provider timeouts and stage/run budgets. A future timeout alone does not stop a network call, and executor shutdown can still wait; deadlines must reach the HTTP clients. Retry only transient failures within the remaining budget, with backoff and jitter. Do not repeatedly retry invalid credentials or unavailable model IDs.
4. Accept one-provider success with transparent degradation. Both-provider failure produces a actionable failure, not a fabricated analysis.
5. Rank sources, retain official sources and conflicting evidence, remove repeated content, and cap selected excerpts and total prompt tokens. Preserve original URLs and timestamps. Fix URL normalization to lowercase scheme/host without corrupting case-sensitive paths.
6. Produce validated structured company analysis, domains and report sections in one synthesis call where quality permits. Keep identity and relevance gates. A lower-risk intermediate option runs report and domains concurrently after analysis with an explicit join before the HITL pause. Do not parallelize identity-dependent filtering prematurely.
7. Cache public company research by canonical company identity, freshness policy, query configuration and model/prompt/schema version. Use separate freshness for news and stable company facts. Label cache age and permit refresh. Never share user-specific content through a public cache; coalesce simultaneous misses.
8. Show the web brief before PDF rendering/upload finishes. Retry export without rerunning research. Provision the storage bucket outside the report hot path.

Initial goals, subject to the baseline: first status within one second on a warm service; at least 40% lower median uncached research time on a fixed evaluation set; no p95 latency regression; reduced cost per successful report with no material evidence-quality regression. These are acceptance targets, not speed promises. Cache-hit and cold-start performance must be reported separately.

## 3. A distinctive interface: the company dossier

Recommended visual direction: an editorial research desk. Warm ivory canvas (`#F4F0E8`), near-black ink (`#20251F`), forest-green primary actions (`#234D3C`), restrained amber warnings, serif display headings and a legible sans-serif reading face. Validate contrast before finalizing tokens. Use generous margins, numbered sections, thin rules, restrained corner radii and a small original wordmark. Typography and source presentation provide identity.

Desktop layout: compact masthead; left research navigation; central readable brief; a secondary progress/source rail. On mobile, stack the brief and an expandable activity section. Keep the search action visible near the top rather than below a large hero.

The key interaction is a dossier that fills in as validated results arrive:

1. Start: company field, optional official website/location for ambiguity, concise value proposition, clearly labeled sample brief.
2. Research: company identity, real progress and checked source entries appear progressively.
3. Company brief: readable overview, technologies, developments, evidence limitations and citation links available before domain selection.
4. Domain choice: focused options with evidence-backed relevance explanations.
5. Preparation brief: separate confirmed company facts from recommended study topics; make the next study action clear.
6. Completion: web brief, source appendix, freshness date and PDF download. Saved history follows once session ownership is implemented.

Break `page.tsx` into `CompanySearchForm`, `ResearchProgress`, `CompanyIdentity`, `CompanyBrief`, `DomainPicker`, `PreparationBrief`, `SourceList` and `ReportActions`; use a typed `useResearchRun` hook and API client. Keep state transitions explicit instead of inferring phases from domain-array length. Read the installed Next.js guides required by `frontend/AGENTS.md` before implementation.

Design research: [Linear’s March 2026 interface refresh](https://linear.app/now/behind-the-latest-design-refresh) supports quieter navigation and stronger attention on working content. [Pentagram’s typography work](https://www.pentagram.com/typography) provides a reference for typography-led identity. The ivory/forest dossier treatment is an original proposal, not a claim that either reference uses this exact design. Test it with five target users on starting research, understanding delays, choosing a domain and locating evidence.

## 4. Execution architecture and API contract

Use a durable run record and worker execution rather than treating an open browser connection as the job owner. For this scale, a Postgres-backed queue with leases is a reasonable starting point; avoid adding Redis solely for status delivery. Persist run creation and enqueue intent atomically. Workers need lease expiry, recovery, idempotent transitions and bounded concurrency.

Proposed endpoints:

- `POST /runs`: validate company input and session quota; idempotency key; return 202 with run ID promptly.
- `GET /runs/{id}`: authorized current state and sanitized partial/final brief.
- `GET /runs/{id}/events`: authorized SSE stream with event IDs, heartbeat and replay cursor; polling fallback.
- `POST /runs/{id}/domain`: validate offered-domain membership and paused state, then enqueue resume atomically.
- `POST /runs/{id}/cancel`: cooperative cancellation between stages, with provider deadlines bounding in-flight calls.
- `GET /reports/{id}/view` and `/download`: authorize ownership and create fresh scoped links or safe local responses.

States: queued, researching_company, needs_company_confirmation, awaiting_domain_selection, researching_domain, preparing_export, completed, insufficient_evidence, failed, cancelled. Treat research success and export failure separately.

Event fields: schema version, run ID, monotonically increasing event ID, timestamp, phase, stage, event type, safe message and optional real counters. Do not stream raw prompts, secrets, internal stack traces or full checkpoint state. The frontend must ignore duplicate events and recover from refresh/disconnect without starting a second job. Signed URLs are temporary delivery credentials and should not be the canonical report identifier.

LangGraph supports node updates and custom progress events; choose the API supported by the pinned installed version. See [official streaming documentation](https://docs.langchain.com/oss/python/langgraph/streaming). The transport must not expose raw graph state indiscriminately. Checkpoint persistence and durable worker recovery solve different problems and both are needed.

## 5. Implementation sequence and acceptance gates

| Slice | Work | Completion evidence |
|---|---|---|
| A: correctness and launch boundaries | Exa fix, normalized evidence tests, report access restrictions, scoped session ownership, safe error responses, domain validation, initial timing instrumentation | Offline tests cover content preservation, unauthorized report/run access, traversal, invalid domain and insufficient evidence. Capture baseline from controlled runs. |
| B: faster research | Shared bounded scheduling, partial-provider handling, deadlines, retry policy and token budgets | Injected provider delays/failures demonstrate bounded concurrency and recovery. Paired benchmark shows improvement without evidence loss. |
| C: resumable progress | Durable run model, worker, event log, SSE/status API, frontend state machine | Refresh, stream disconnect, duplicate submission, concurrent resume, worker restart and cancellation tests pass. |
| D: dossier experience | Design tokens, responsive components, partial web brief, source registry, accessibility, metadata and export actions | Desktop/mobile visual review, keyboard flow, screen-reader status behavior and end-to-end research journey pass. |
| E: efficiency and beta | Structured synthesis, freshness-aware cache, independent export retries, quotas, telemetry and user feedback | Quality evaluation passes; cache isolation and invalidation tests pass; usage and cost dashboard available. |
| F: commercial validation | Saved briefs, feedback, usage limits; later paid offering based on demonstrated demand | Observe completion, return usage, reported usefulness and cost per completed brief before choosing pricing. |

Ship slices behind configuration flags where practical. Preserve existing routes during migration until the new frontend is deployed. Roll back synthesis, concurrency and caching independently. Do not advertise speed guarantees before production measurements support them.

## Verification and release plan

Build a fixed set covering well-known companies, ambiguous names, small companies, sparse domains, non-English names and conflicting evidence. Compare baseline and candidate on the same inputs and source fixtures. Run repeated controlled live evaluations for latency, separate from deterministic CI. Include modest concurrent-user tests within provider quotas.

Evaluate correct identity, factual claim support, resolvable source IDs, domain relevance, uncertainty disclosure and usefulness of preparation advice. A valid citation ID alone does not prove that a source supports a claim; manually review sampled claims. Treat retrieved pages as untrusted input and test that embedded instructions cannot redirect the research workflow.

CI should run backend unit/API tests without credentials or network, frontend lint/type checks, production build, and mocked end-to-end flows. Live provider tests must be explicitly opt-in. Pin Python dependencies and verify a clean installation. Render and inspect PDFs when export changes land.

Track activation (brief opened plus domain selected), completion and abandonment by stage, repeat usage, feedback, export success, p50/p95 latency and cost per successful brief. Use feedback to validate whether users want repeat company research or continuing preparation tools before expanding scope.

Audit verification: `npm run lint` completed successfully. Findings above are based on repository inspection and external design/technical references. No paid research runs, production load tests, deployed visual inspection or vulnerability exploitation were performed. An attempted isolated Python reproduction could not execute because the repository virtual environment points to an inaccessible Windows Python executable. Repair the local runtime before backend verification. Application code has not been changed by this planning pass.
