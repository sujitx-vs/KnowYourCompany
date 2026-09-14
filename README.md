# KnowYourCompany

An evidence-backed career research desk. Research a company, inspect its sources,
choose a career focus and build a preparation dossier you can read or download.

The interface uses a warm editorial design. The workflow runs independently of the
browser, with live activity, saved progress, confirmation for uncertain company
matches and explicit insufficient-evidence outcomes.

## What is implemented

- Structured company and preparation briefs with source IDs and a clickable source register.
- Five normal-path AI calls instead of seven: company synthesis also creates report sections and career choices.
- Bounded parallel search queries, normalized Tavily/Exa evidence, partial-provider recovery, deadlines and retries.
- Public evidence caching with shorter news freshness and a canonical company-brief cache.
- Authenticated run ownership through an anonymous browser credential; quotas and idempotent submissions.
- Durable run queue, leased workers and completed-node snapshots in SQLite (local) or PostgreSQL (production).
- Server-sent progress events with polling fallback, refresh recovery, cancellation and saved-step retries.
- A separate PDF export phase using the same brief and sources; export retry does not redo research.
- Saved browser-session history, usefulness feedback, usage allowance and a protected operator dashboard.

## Local setup

Use Python 3.12 and Node.js 22. From the repository root:

~~~powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
Copy-Item .env.example .env
~~~

Fill in the provider keys in .env. For local development leave
RUN_DATABASE_URL=outputs/research.sqlite3. An existing SUPABASE_DB_URL is also
accepted when RUN_DATABASE_URL is empty; set the local path explicitly if you want
to avoid connecting to a remote database.

~~~powershell
.venv\Scripts\python.exe -m tools.operator check-config
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
~~~

In a second terminal:

~~~powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
~~~

Open http://localhost:3000. The API defaults to http://127.0.0.1:8000.
On macOS/Linux, replace .venv\Scripts\python.exe with .venv/bin/python.

The repository's old venv folder is not used by this version. Do not overwrite an
existing .env when updating a configured checkout; merge the new example settings.

## Research flow

~~~text
Create run -> verify identity -> confirm if uncertain
           -> parallel company searches -> filter evidence -> company synthesis
           -> read company brief / choose domain
           -> parallel domain searches -> filter evidence -> preparation synthesis
           -> read web dossier -> render/upload PDF -> download
~~~

The worker saves each completed node before proceeding. If a process stops, another
worker can reclaim its expired lease and skip completed nodes. A currently running
external call can repeat after a crash; this is not an exactly-once provider guarantee.

## API

All research/report routes require Authorization: Bearer <browser-session-token>.
The frontend creates a random 32-byte credential and stores it locally; only its hash
is stored with backend ownership records.

| Route | Purpose |
|---|---|
| POST /runs | Accept research promptly; supports Idempotency-Key |
| GET /runs | Saved briefs belonging to the current browser credential |
| GET /runs/{id} | Sanitized status, identity, briefs and source metadata |
| GET /runs/{id}/events | Authorized SSE activity with replay IDs |
| POST /runs/{id}/confirm | Confirm an uncertain company match |
| POST /runs/{id}/domain | Choose one of the offered career areas |
| POST /runs/{id}/cancel | Cancel future work; in-flight work observes deadlines |
| POST /runs/{id}/retry | Retry a failed phase from saved nodes |
| POST /runs/{id}/feedback | Save usefulness feedback |
| GET /reports/{id}/view | Authorized PDF preview |
| GET /reports/{id}/download | Authorized PDF download |
| GET /usage | Session usage and computed metrics |
| GET /admin/metrics | Aggregate metrics; requires X-Admin-Key |
| GET /ready | Database readiness |

The old /research and /select-domain names are authenticated asynchronous aliases.
They do not retain the old synchronous response shape. The insecure arbitrary-path
PDF endpoints return 410. Coordinate backend/frontend upgrades; see docs/DEPLOYMENT.md.

## Tests and evidence

~~~powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m tools.evaluation.benchmark
cd frontend
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
~~~

For installed Chrome on Windows, set PLAYWRIGHT_CHANNEL=chrome instead of installing
Chromium. Browser tests launch their own fictional fixture API and frontend on ports
8000 and 3000; those ports must be free. Tests do not call paid providers.

The PostgreSQL integration test runs when TEST_POSTGRES_URL points to a dedicated
test database. CI provisions that service. Never use a production database for tests.

The saved synthetic benchmark shows 59.9% lower median search scheduling time using
fixed-delay providers. It does not establish live end-to-end performance.
A successful live synthesis recheck is still pending after the schema compatibility
fix. Current verification status is in docs/IMPLEMENTATION_CHECKPOINT.md.

An opt-in live smoke command is available for an approved staging check:

~~~text
python -m tools.evaluation.live_check --company "Tata Consultancy Services" --hint "tcs.com" --include-domain
~~~

It uses configured provider credits, saves its result locally and does not upload a
PDF. Do not run it as part of ordinary offline CI.

## Deployment and operation

Read docs/DEPLOYMENT.md for required configuration, private PostgreSQL schema,
storage provisioning, worker topology, proxy settings, migration and rollback.

Production requires PostgreSQL and private Supabase Storage. There is no silent
fallback to in-memory state. Set ADMIN_API_KEY to a random secret of at least
32 characters and open /operator for aggregate usage/reliability/cost metrics.
Prices must be configured from your actual provider plans; unknown costs remain unknown.

This is a private-beta implementation, not a completed market validation. Browser
credentials are not personal accounts: clearing browser data loses access. Deployment,
cloud-storage verification, complete live quality/performance evaluation and target-user
feedback remain launch gates. The application has not been deployed by this implementation work.

Company facts require evidence; preparation recommendations are explicitly labelled.
Always verify current hiring details through official sources.
