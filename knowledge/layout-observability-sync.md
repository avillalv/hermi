# Layout, states, observability and sync

Read it when you add a screen state, a breakpoint, an analytics event, Sentry or log fields, the sync indicator or a backup step.

## States and layout (web)
- `components/EmptyState.tsx`, `ErrorState.tsx` (also `QueryError`, `ERROR_COPY`), `Skeleton.tsx`, `states.css`, `routes/errors.tsx` (`NotFound`). The API client maps offline, 401, out of credits, 429, maintenance and forced update in `lib/api/client.ts`.
- `shell/AppShell.tsx` and `shell.css` hold the tab bar, icon rail and sidebar breakpoints.
- Kit e2e helpers in `apps/web/e2e/kit/layout.ts` (`MAIN_ROUTES`, `visit`, `noHScroll`); `npm run test:kit` runs the width sweep, axe (light and dark) and the iPhone 15 project. The iPhone 15 profile runs on Chromium (`shortcut:`), not WebKit.

## Sync indicator
- `lib/sync.ts` (`useSyncState`, `startPolling`, `syncNow`, `markAccepted`, `setQueued`, `reportConflict`) and `components/sync-indicator/SyncIndicator.tsx` (`tripId`, `variant` line or chip). Smoke flow 18 is `e2e/smoke/sync.spec.ts`.
- The API ignores `If-None-Match`, so every poll is a full 200. `setQueued` reads 0 until WF-089 calls it and removes the dev hook `window.__hermiSetQueued`.

## Analytics
- Catalogue: `packages/shared/src/events.ts`, mirrored to `apps/api/hermi/analytics_catalogue.json` by `npm run gen:shared`. Server `hermi/analytics.py` (`capture` rejects unknown names and properties). Web `lib/analytics.ts` (`capture`, `captureOnce`, `setAnalyticsOptOut`, `setAnalyticsUser`) under `lib/track.ts`.
- Opt-out is localStorage `hermi.analytics.optout` plus Global Privacy Control. No `posthog-js`, so no replay. Web host is fixed US; the API default is EU (align when the project exists).

## Sentry and logs
- API `sentry_setup.py` and `logging_setup.py`; worker `hermi_worker/observability.py` (`job_context`); web `lib/sentry.ts`. All scrub PII. Request logs use the route template only.

## Backups
- `infra/scripts/backup-dump.sh` (weekly, encrypted with `BACKUP_ENCRYPTION_KEY`, kept 35 days), `restore-drill.sh [--local]`, runbook `docs/runbooks/restore.md`. The `db_dump_offsite` job is prompt 12 and needs the Postgres 18 client in the worker.
