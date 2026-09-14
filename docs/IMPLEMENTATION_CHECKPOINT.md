# Implementation checkpoint

Updated 14 September 2026. Base commit: `e39d7a2` on `main`. Changes are saved in the working tree; no implementation commit or deployment has been made.

## Resume point

Implementation resumed and the remaining local engineering work listed below is now complete. External acceptance gates remain open. Changes are saved locally, without a commit or deployment.

## Completed in this continuation

- Added configuration validation, a complete environment example, operator CLI, and an operator dashboard with its access key held only in memory.
- Added readiness checks, aggregate operational metrics and explicit retention cleanup tooling; rejected public storage buckets during setup.
- Improved progress details with expandable activity and phase timing that excludes time waiting for user decisions; prevented older polling snapshots from replacing newer events.
- Made export names stable per run for retry/upsert behavior and reviewed storage access handling.
- Rewrote setup and deployment instructions, documented the asynchronous API migration, and prepared an honest beta/customer validation protocol.
- Added configuration, storage and operator browser regression coverage, verified dependencies, and preserved desktop/mobile visual evidence.

## Final verification

- Backend: **28 passed, 1 skipped**; PostgreSQL integration requires a dedicated test instance. One upstream Starlette/AnyIO deprecation warning remains.
- Frontend: **lint, TypeScript and production build passed**, including the operator route.
- Browser: **8 passed** across desktop/mobile, covering research, refresh, preparation, PDF download, feedback, citations, cancellation, polling fallback and operator access.
- Dependency consistency: `pip check` passed. `git diff --check` passed.
- Final desktop/mobile dossier screenshots and regenerated two-page PDF were visually inspected. Screenshots are saved under `docs/verification/`.
- Synthetic search scheduling median improved **59.9%**, from 0.5041 s to 0.2024 s. This does not establish live end-to-end latency improvement.

## Still open: external acceptance gates

1. Verify the corrected Gemini schema adapter with successful live company and domain synthesis. The earlier live retry was declined; it was not repeated.
2. Validate PostgreSQL, private cloud storage and deployment behavior in the target environment. CI is configured but has not been run here.
3. Measure real end-to-end latency and factual quality across concrete evaluation cases; verify broad non-Latin PDF coverage if required.
4. Conduct the five-user beta protocol and evaluate retention and willingness to pay. See `BETA_VALIDATION.md` and `DEPLOYMENT.md`.

The earlier baseline below is retained for continuity; its local engineering to-do items are superseded by the completion and verification sections above.

## Implemented before resuming

- Editorial frontend: ivory/forest palette, typography-led company dossier, responsive layouts, saved browser-session research, readable company and preparation briefs, source register, feedback and usage allowance.
- Backend-driven progress through authenticated SSE and status polling; refresh recovery, cancellation, uncertain-company confirmation and retry states.
- Durable queue and node snapshots: SQLite for local development, PostgreSQL private schema for production, leased workers, stale-worker fencing, idempotent submissions, atomic domain selection and restart recovery.
- Scoped anonymous bearer ownership; report access by run ID; unsafe arbitrary-file/redirect endpoints retired; explicit CORS origins; input limits and daily quotas.
- Exa content normalization fix, bounded search concurrency, provider partial failure handling, deadlines, centralized HTTP retries and evidence budgets.
- Structured company synthesis combines analysis, report sections and domain choices. The normal complete research path is five AI calls instead of seven, before retries.
- Source ID validation, clear fact/recommendation distinctions, shared structured data for web/PDF output.
- News/stable search caches, canonical company-brief cache, freshness labels, explicit fresh research and company cache miss coalescing.
- Separate export phase; PDF retry preserves completed research; fresh authorized storage links; source appendix in PDFs.
- Backend tests, browser tests, pinned dependency snapshot, synthetic benchmark, CI definition including a dedicated PostgreSQL test service, opt-in live check and evaluation cases.
- Operator metrics API exists; its visual dashboard and deployment documentation remained unfinished at this resume point.

## Verification at the previous stop

- Backend: **22 passed, 1 skipped**. The skipped integration test requires a dedicated PostgreSQL test instance. One dependency deprecation warning.
- Frontend: **lint, TypeScript and production build passed**.
- Browser: **6 passed**, desktop/mobile: full workflow and PDF download, refresh recovery, cancellation, feedback, citations and polling fallback. These ran before the last schema/cache/metrics changes; final regression still needed.
- Synthetic search benchmark: **59.9% lower median scheduling time**, 0.5041 s to 0.2024 s, ten fixture repetitions. This is not a measured live end-to-end speedup.
- Desktop/mobile welcome screenshots were inspected. A two-page PDF fixture was rendered and visually inspected; the fixture wording was subsequently corrected, so the final PDF should be regenerated.
- Live test: identity and search/relevance processing completed, but company synthesis hit Gemini schema errors. The provider schema adapter was corrected and a regression test added. The latest live retry was declined, so the correction has not yet been verified against the live API. Do not silently repeat the declined request or claim live success.

## Remaining work when resuming

1. Complete configuration validation, environment examples, operator tooling/dashboard and accurate run/deployment documentation.
2. Review transport, persistence, timing, session recovery and export edge cases; add meaningful regression tests for fixes.
3. Update dependency/install instructions and verify lock consistency; ignore transient test output.
4. Re-run final backend and browser checks; inspect final dossier and PDF renderings; preserve verification evidence.
5. PostgreSQL/cloud-storage deployment validation and successful live Gemini synthesis remain unverified until the appropriate environment/access is available.
6. Production latency targets, factual-claim quality evaluation across the full case set, five target-user interviews, retention and willingness-to-pay validation are external acceptance gates. They cannot be marked complete by code or fixture tests.

## Useful commands

Windows runtime repaired locally at `.venv/Scripts/python.exe` (Python 3.12). The old `venv` is not used.

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m tools.evaluation.benchmark
cd frontend
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL='chrome'
npm run test:e2e
```

Browser tests start their own fixture API and frontend servers on ports 8000 and 3000. Do not point this fixture server at production. `tests/demo_api.py` contains clearly fictional company evidence and blocks production mode.

Live-check state is under ignored `outputs/`; credentials remain in the existing ignored environment files. Never copy either into this checkpoint or a commit.
