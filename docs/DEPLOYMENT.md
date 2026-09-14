# Deploying the durable research desk

## Configuration and startup

Use Python 3.12 and Node.js 22. Install backend dependencies with `pip install -r requirements.lock.txt`, and frontend dependencies with `npm ci` in `frontend/`. The lock includes the test dependencies used by CI. Do not install from the old `venv` directory; create your own virtual environment.

Set backend environment values from `.env.example`. Production must set `APP_ENV=production`, a PostgreSQL `RUN_DATABASE_URL`, exact HTTPS `FRONTEND_URL` origins, `GOOGLE_API_KEY`, at least one search key, and the Supabase Storage URL/service-role key. Private storage must be provisioned before taking traffic:

```text
python -m tools.operator check-config
python -m tools.operator setup-storage
```

The database account must be able to create the `kyc_private` schema and its tables on first startup. The schema is excluded from Supabase's public API and access is revoked from PUBLIC, anon and authenticated roles. Never add it to Supabase's exposed schemas. Credentials remain backend-only. Database snapshots contain public source text and private user selections; apply your normal backup controls.

Run an initial private beta with one API process and the embedded worker:

```text
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

For a separate worker, set `EMBEDDED_WORKER=false` on the API and run `python -m backend.worker` as a separate long-lived process with the same database and provider configuration. The standalone command runs one worker loop. Each API process with embedded workers creates up to WORKER_CONCURRENCY workers. Search limits are per process: total provider concurrency grows with the number of processes. Keep this small until load measurements justify increasing it.

Use `/` for liveness and `/ready` for database readiness. Readiness does not verify provider credits or Storage availability. Run the opt-in live check in a staging environment for that. Do not deploy `tests.demo_api:app`: it serves fictional data and is for local browser tests only.

## Frontend and transport

Set `NEXT_PUBLIC_API_URL` before `npm run build`; this value is compiled into the frontend. Publish the Next.js build through the existing hosting setup. Set the backend's FRONTEND_URL to the exact frontend origin. Browser requests use an Authorization bearer credential, not cross-site cookies. HTTPS is required for the production frontend and API.

SSE clients send authorization headers and have a status-polling fallback. Disable reverse-proxy response buffering for `/runs/*/events`; allow long-lived responses and periodic heartbeats. Configure Uvicorn to trust forwarded client addresses only from your known reverse proxy. Blindly trusting arbitrary forwarded addresses defeats IP quotas.

The current queue uses short serialized database transactions. This is appropriate for a small beta, not an unlimited throughput claim. Watch database latency as concurrent clients grow. Storage URLs expire after five minutes and are generated only after ownership checks.

## Migration from the original API

Deploy the new frontend and backend as a coordinated version change, preferably through staging first. The `/research` and `/select-domain` route names remain as authenticated aliases but return the new asynchronous run contract. The original synchronous response shape is not backward compatible. Old unauthenticated clients must be updated.

The arbitrary-path `/view-pdf` and `/download-pdf` routes intentionally return 410; restoring them would reopen file-access vulnerabilities. Use `/reports/{run_id}/view` or `/download` with the browser's bearer credential. Legacy anonymous LangGraph checkpoints have no trustworthy owner and are not automatically imported. Preserve old storage/backups according to your retention policy; never assign old research to a new user based on a guessed company name.

The new worker persists completed-node state in research_runs. It does not depend on the old PostgresSaver tables. A worker crash can repeat the in-flight node; completed nodes are skipped. PDF uploads and external API calls cannot be made exactly-once across a process crash. Monitor costs and remove orphaned exports through an explicit storage retention policy.

## Operations

Generate an ADMIN_API_KEY with at least 32 random characters and open `/operator` in the frontend for aggregate 30-day statistics. Keep the key out of frontend environment variables and public logs. The dashboard does not display private report contents.

Configure MODEL_PRICES_JSON per model with input/output prices per million tokens, and SEARCH_PRICES_JSON per provider with a request price. These are estimates; model failures without returned usage, search retry billing and hosting costs require reconciliation against provider invoices. Unknown prices are shown as unavailable.

Quotas count submissions over a rolling 24 hours, including failed and cancelled runs, because those can still consume provider resources. New runs permit three manual retries per phase (company, domain and export). Legacy runs without phase counters retain their original shared three-retry budget; no history is reset. Automatic response correction is separate from manual retries and shares a two-call ceiling with model fallback per structured step and manual attempt. These reservations persist across worker restarts. Shared-IP limits can affect campuses behind NAT: tune IP_DAILY_RUN_LIMIT using beta feedback while retaining a global daily budget.

The browser credential provides anonymous scoped ownership, not an account or cross-device login. Clearing local storage loses access. Do not advertise persistent personal accounts until an account flow is added.

Use `python -m tools.operator cleanup --retention-days 30` for a non-mutating explanation, and add `--apply` only when you intend to remove expired database records. Active runs are retained. This does not delete PDFs; configure and document a separate Storage/local-file retention policy. No cleanup schedule is created automatically.

## Release and rollback gates

Run backend tests, lint, production build and browser tests. CI provisions a dedicated PostgreSQL database for the persistence test. Locally the PostgreSQL test is skipped unless TEST_POSTGRES_URL points to a dedicated test database. Never point it at production.

Staging checks still needed: successful live synthesis, cloud export and authorized link refresh, process restart during research, two concurrent users, and proxy/SSE behavior. Compare warm, cold-start, cache-hit and uncached latency separately. The saved 59.9% benchmark measures synthetic search scheduling only.

SEARCH_QUERY_CONCURRENCY=1 restores sequential query batches. Set RESEARCH_CACHE_ENABLED=false and SEARCH_CACHE_ENABLED=false independently to disable caches. Structured synthesis is part of the v2 report contract; rolling that back requires restoring a compatible application release, not a configuration toggle. Take a database backup before release changes. Do not revert the report ownership boundary.

## Focused response/retry update compatibility

The response update adds retry_allowed, retries_remaining, retry_scope and failure_category to run snapshots without removing existing fields or endpoints. Retry exhaustion retains HTTP 429, with X-Failure-Category: manual_retries_exhausted and no Retry-After header; this is an application budget, not a provider rate limit. The frontend consumes snapshot fields, so it does not need access to the diagnostic header. Deploy backend before or together with frontend: the updated frontend hides retry controls when metadata is absent.

No database migration, cache flush, dependency upgrade or new production setting is required. JSON run records receive counters only for new runs; legacy research and checkpoints are retained. Durable automatic attempt bookkeeping is added on execution. Existing provider-call/token caps and phase deadlines remain, with one repair sharing the two-call ceiling rather than adding calls beyond it. Invalid output and its repair input are never saved as completed research or logged. INFO-level agent.services.gemini diagnostics contain only run/phase/model, safe categories, schema paths, finish reason and recovery outcome.

Validation was offline; actual provider finish-reason behavior and successful production synthesis still require verification by the operator. See RESPONSE_RETRY_CHECKPOINT.md for fixture results.
