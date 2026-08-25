# Distributed Job Scheduler — Frontend

React + TypeScript + Tailwind CSS dashboard for the job scheduler backend.

## Pages

1. Login / Register
2. Dashboard Overview — system metrics, worker summary
3. Projects — organizations and projects
4. Queue Management — per-project queue list, create/pause/resume
5. Job Explorer — per-queue job list with status filters and submission form
6. Job Details — single job, payload, and full execution history
7. Worker Monitoring — live worker fleet health
8. Dead Letter Queue — failed jobs across all queues, with manual retry
9. Metrics & System Health — throughput chart and reliability stats

All data-driven pages use polling (4-6s intervals) rather than a fixed
one-time fetch, per the project spec. WebSockets are noted as a
possible future upgrade but aren't implemented here.

## Running

```bash
cp .env.example .env   # adjust VITE_API_BASE_URL if your API isn't on localhost:8000
npm install
npm run dev             # http://localhost:5173
```

Requires the backend API (see ../backend/README.md) running and reachable
at the URL in `.env`.

## Building

```bash
npm run build      # type-checks with tsc -b, then bundles with vite build
npm run preview    # serve the production build locally
```

## Architecture notes

- **Auth**: JWT stored in `localStorage`. `src/services/api.ts` attaches it
  to every request and clears it on a 401 response. There's no `GET /me`
  endpoint on the backend yet, so the logged-in user's display info is
  cached locally at login/register time rather than fetched fresh.
- **Polling, not one-shot fetches**: `src/hooks/usePolling.ts` is used by
  every page that shows live data, so the dashboard reflects worker/job
  state changes without a manual refresh.
- **No global state library**: each page owns its own polling queries.
  At this project's scope (a handful of pages, no deeply shared state)
  React Context (just for auth) plus per-page hooks is simpler than
  wiring up Redux/Zustand/React Query, though React Query in particular
  would be a reasonable upgrade if this grew.
- **Dead Letter Queue page** has no dedicated backend endpoint that
  aggregates DLQ jobs across all queues, so it walks projects -> queues
  -> per-queue DLQ jobs client-side. Fine for this project's scale; a
  real aggregate endpoint would be worth adding if the number of queues
  grew large.
