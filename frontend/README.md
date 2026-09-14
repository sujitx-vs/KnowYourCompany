# KnowYourCompany frontend

The Next.js dossier interface uses the durable research API.

## Run locally

1. Start the API from the repository root (see the root README).
2. Copy .env.example to .env.local and set NEXT_PUBLIC_API_URL.
3. Run npm ci, then npm run dev.

The UI saves a random bearer credential and selected run ID in browser local storage.
Research data is stored on the backend. Clearing browser data removes access to that
anonymous session. No API provider or database credentials belong in this directory.

## Verification

- npm run lint
- npm run build
- npm run test:e2e

Browser tests start a local fixture API and production frontend on ports 8000/3000.
Build first. Install Chromium with npx playwright install chromium, or set
PLAYWRIGHT_CHANNEL=chrome to use installed Chrome locally.

## Structure

- app/page.tsx: research desk and dossier composition
- components/dossier.tsx: search, identity, progress, briefs, domains, sources, export, feedback
- hooks/useResearchRun.ts: session recovery, SSE plus polling, mutations
- lib/api.ts: typed API contract and credential handling
- app/operator/page.tsx: aggregate operator dashboard; operator key is kept only in memory

Metadata is noindex for the private beta. Remove that restriction only when public launch is intended.
