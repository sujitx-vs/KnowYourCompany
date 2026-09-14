# Focused validation and retry checkpoint

## Step 1 — response validation and bounded recovery implemented

Claims deduplicate IDs before enforcing 15 unique IDs. Prompts prefer 1–3 citations (maximum 10). Schema and citation checks run inside the recovery boundary before graph checkpoints or cache writes. One repair/truncation recovery shares the existing two provider-call ceiling; provider metadata confirms truncation. Required fields receive no defaults; domain output explicitly requires domains: []. Diagnostics contain metadata and validation paths only.

## Step 2 — durable retry policy implemented

New runs receive three manual retries per phase. The aggregate retries field remains additive for compatibility. Existing runs without phase counters keep their original shared allowance without migration or resets. Automatic call/repair reservations persist separately per phase, manual attempt and schema, including worker restart. API exposes additive safe failure/retry fields; exhaustion retains the existing 429 contract but has an explicit application category header and no misleading Retry-After. Phase deadlines and existing checkpoint resume behavior remain.

Verification and frontend changes are pending. No live APIs, commit, push, deployment or production configuration changes.

## Step 3 — focused frontend changes implemented

Existing progress UI labels correction. Research and PDF retry controls require explicit server permission and show remaining attempts or permanent exhaustion. Provider rate limiting is described separately. Missing metadata fails closed. No styling or workflow redesign. Regression verification is next.

## Step 4 — initial verification saved

43 backend tests passed, one PostgreSQL integration test skipped. Frontend production build/TypeScript passed. The first check caught a fixture wrapper that needed the new validator keyword and a missed frontend retry-control replacement; both were fixed before this passing run. Focused browser checks and three additional deadline/truncation tests are in progress.

## Step 5 — final verification and handoff

- Backend: 46 passed, 1 skipped (dedicated PostgreSQL integration), 1 existing Starlette/AnyIO deprecation warning.
- Frontend: lint clean; production build and TypeScript passed.
- Focused browser assertions: all six desktop/mobile company, domain and export retry scenarios passed; the runner then stalled during teardown and was interrupted. The six assertions passed, but this browser command did not exit cleanly.
- Fixture coverage includes 13 citations, deduplication before bounds, over-15 bounded repair, unknown and missing citations, required fields, explicit empty domain field, confirmed versus unknown truncation, shared recovery allowance, expired deadlines, unchanged checkpoints on failed repair, persisted automatic budgets, independent phase budgets, legacy shared exhaustion, redacted diagnostics and retry UI.
- No paid/live API was invoked. Fixtures do not establish live provider correctness. PostgreSQL integration was not run locally.
- No commit, push, deployment, dependency upgrade or production setting change. All changes remain locally reviewable.

Files: agent/schemas.py; agent/services/gemini.py and runtime.py; company/domain synthesis nodes; backend/retries.py, main.py, store.py and worker.py; existing frontend progress/retry components and API types; focused regression fixtures/tests; DEPLOYMENT.md. Existing research, cache, authorization, storage and PDF behavior are preserved.

Compatibility: additive snapshot fields and stored JSON bookkeeping, unchanged endpoints and retry-exhaustion HTTP status. New runs use per-phase counters; legacy runs keep shared counters without backfilling or resetting research data. Deploy backend before/together with frontend. No migration or new environment variable is needed.

Final checkpoint: `git diff --check` passed. Browser teardown inspection was unavailable in the sandbox; the stalled test command was interrupted. This is a local test-runner limitation, not evidence of a production browser failure.
