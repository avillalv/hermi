# Infra

- `render/render.yaml`: Render blueprint. `cloudflare/`: Pages and WAF settings.
- `scripts/deploy.mjs`, `smoke.mjs`, `rollback.mjs`: used by the deploy workflows. Tests: `smoke.test.mjs`, `deploy-workflows.test.mjs` (run by the `scripts` job of `ci`, with `render/render.test.mjs`).

## Deploy workflows (WF-009.2)

`deploy-staging` runs on push to main. `deploy-prod` is manual: give it the image digest that staging deployed (shown in the staging run summary) and its commit sha. Approval is the `production` GitHub environment, so add required reviewers there. The prod job runs only from `main`, and also set the `production` environment branch policy to `main` (Settings, Environments, production, Deployment branches). It checks that the digest equals the digest of `ghcr.io/avillalv/hermi:staging-<sha>` before it deploys.

Render deploys go API first, then worker, one at a time; a failure stops the run. A failed smoke rolls production back to the previous successful Render deploy. If a deploy or the web upload fails, the services that already went live are rolled back. Cloudflare Pages is not rolled back automatically: redeploy the previous commit from the Cloudflare dashboard (Pages, hermi-web, Deployments, Rollback).

Both skip with a message (and stay green) until `DEPLOY_ENABLED` is `true` and every item below is set.

| Where | Name | Used by |
| --- | --- | --- |
| Variable | `DEPLOY_ENABLED` (`true`) | both |
| Variable | `STAGING_API_URL`, `STAGING_WEB_URL` | staging |
| Variable | `PROD_API_URL`, `PROD_WEB_URL` | prod |
| Secret | `RENDER_API_KEY` | both |
| Secret | `RENDER_STAGING_API_SERVICE_ID`, `RENDER_STAGING_WORKER_SERVICE_ID` | staging |
| Secret | `RENDER_PROD_API_SERVICE_ID`, `RENDER_PROD_WORKER_SERVICE_ID` (environment `production`) | prod |
| Secret | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | both |

Render env groups (set in the Render dashboard, referenced by `render/render.yaml`): `hermi-staging`, `hermi-prod-shared`, `hermi-prod-api`, `hermi-prod-worker`. Their keys are listed in 02 section 7.2 and `.env.example`.

Secrets are set per step, never at job level. Snapshot before migration is left to Render point-in-time recovery.

The image is `ghcr.io/avillalv/hermi`, pushed with the built-in `GITHUB_TOKEN`. Render needs a registry credential to pull it if the package is private.

## Backups and restore drill (WF-039)

PITR (7 days) and daily snapshots are Render database settings, noted in `render/render.yaml`. `scripts/backup-dump.sh` makes the weekly encrypted `pg_dump` for R2 (second Cloudflare account, key in `BACKUP_ENCRYPTION_KEY`, held outside Render). `scripts/restore-drill.sh` restores a dump into a scratch `hermi_*` database, smoke tests it and checks the 1 hour RTO; `--local` runs it with no R2 or Render. Procedure, restores and the drill log: `docs/runbooks/restore.md`. Test: `scripts/restore-drill.test.mjs`.
