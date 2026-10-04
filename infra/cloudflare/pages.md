# Cloudflare Pages (web build)

The web app ships from Cloudflare Pages, not Render (02 sections 9 and 11). Render holds only the API, worker and Postgres (`infra/render/render.yaml`).

| Setting | Production | Staging |
|---|---|---|
| Pages project | `hermi-web` | `hermi-web` (preview branch `staging`) |
| Custom domains | `app.hermi.world`, `admin.hermi.world` | `app.staging.hermi.world` |
| Build command | `npm ci && npm run build --workspace apps/web` | same |
| Output directory | `apps/web/dist` | same |
| Production branch | `main` (deployed by the release workflow, not by git push) | `main` preview |

The landing page (`hermi.world`, `www`) is a second Pages project built from `apps/landing` (WF-002).

Build variables (public, safe in the bundle; names in 02 section 7.1): `VITE_API_BASE_URL`, `VITE_APP_ENV`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_SENTRY_DSN`, `VITE_POSTHOG_KEY`, `VITE_STATUS_PAGE_URL`. Production and staging use different values. Set them in the Pages project, never in the repo.

Caching: hashed assets `Cache-Control: public, max-age=31536000, immutable`; `index.html` `no-cache`.

TLS: SSL/TLS mode Full (strict), Always Use HTTPS on, minimum TLS 1.2, HSTS on (max-age 6 months, no preload until launch). Render serves a valid certificate for `api` and `go`, so Full (strict) holds.
