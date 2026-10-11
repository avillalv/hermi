# Scheduler, live fares, breakers and evals

Built in prompt 14 (WF-051, 052, 056, 057). Decisions are in `app-buildout/prompts/DECISIONS.md` (rows dated 2026-10-10 and 2026-10-11 for prompt 14).

- **Scheduler.** `hermi scheduler` elects one leader with `pg_try_advisory_lock(0x57415946)`. The leader runs `scan_due_routes` every 30 s (limit 500, `SKIP LOCKED`, jitter by route id) and the cron tasks in `app.scheduled_registry`. Lane workers run no periodic tasks. Eligibility is decided in `check_fare_route.skip_reason`.
- **Live fares.** `modules/flights/live.py` caches in `provider_calls` plus `fare_observations` for 6 hours, single flight through `ai.cache.Lease`. Gate: flag `serpapi_live_fares`, kill switch `provider.serpapi`, monthly quota, per account ceiling. The route answers inline (200, no job).
- **Breakers.** `modules/ai/breakers.py` trips at 80 and 95 percent of the Anthropic budget, 90 percent of the SerpApi quota, and on provider error rate with a half-open probe. Trips write `audit_log` as system.
- **Reconciliation.** `modules/ai/reconcile.py` compares `ai_usage` with the Anthropic admin API daily, alerts at a 3 percent gap, skipped under `claude_cli` or without `ANTHROPIC_ADMIN_API_KEY`.
- **Evals.** `npm run evals` (fake client, seed fixtures, self test). Live runs need `EVALS_LIVE=1`, `--provider anthropic_api` and `--max-usd`. Cost report: `infra/scripts/run_cost_report.py`. Results and method: `docs/evals/README.md`.
