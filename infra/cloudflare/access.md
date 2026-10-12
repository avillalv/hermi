# Cloudflare Access for the admin console

The admin console (`admin.hermi.world`, 08 sections 2 and 9) has two independent gates. Cloudflare Access is the edge gate described here. The second gate is the API's own 2FA session (WebAuthn or TOTP), which no Cloudflare setting replaces. The API checks the Access JWT itself on every `/v1/admin` call, so a request that skips the edge is refused.

## What is protected

One Access application with these destinations:

| Destination | Why |
|---|---|
| `admin.hermi.world` | The console web app (the same Pages project as `app.hermi.world`, served by host, see `pages.md`) |
| `admin.hermi.world/v1/admin/*` | The admin API, reached on the console's own origin (see "Same origin API route") |
| `api.hermi.world/v1/admin/*` | Direct hits on the API host are gated too, so the path is never open from the internet |

Staging has its own application, its own policy and its own team audience: `admin.staging.hermi.world`, `admin.staging.hermi.world/v1/admin/*` and `api.staging.hermi.world/v1/admin/*`. There is no path from staging to production data (08 section 9 rule 12).

## Policy

- **Action:** Allow.
- **Include:** emails (or one Google Workspace group) of the people who may open the console. Keep it equal to the enabled `admin_users` rows. Offboarding removes the person here and sets `admin_users.disabled_at` in the same step.
- **Require:** the company identity provider (Google Workspace SSO) and a device posture or IP rule (WARP posture check, or the founder's fixed addresses). SMS and one-time PINs stay off.
- **Session duration:** 8 hours, matching the app session. The app's own 30 minute idle rule still applies.
- **Cookie settings:** HTTP only on, SameSite lax or strict, binding cookie on.

## Values the API needs

Set these in the Render environment for the API (names in 02 section 7.1; never in the repo):

| Variable | Value |
|---|---|
| `ADMIN_AUTH_MODE` | `cf_access` in staging and production. `dev` only in `local` and `ci`; config refuses it elsewhere |
| `CF_ACCESS_TEAM_DOMAIN` | The team domain, for example `hermi.cloudflareaccess.com`. The API reads the signing keys from `https://<team domain>/cdn-cgi/access/certs` |
| `CF_ACCESS_AUD` | The application's AUD tag (Zero Trust, Access, Applications, the application, Overview). One per application, so staging and production differ |
| `ADMIN_WEB_ORIGIN` | `https://admin.hermi.world` (staging: `https://admin.staging.hermi.world`). It is the WebAuthn origin, and its host is the passkey `rpId` |
| `DATABASE_URL_ADMIN` | The `hermi_admin` login (03 section 6.1) |

The API verifies signature, audience and expiry of the `Cf-Access-Jwt-Assertion` header, then maps the verified email to a `users` row with an enabled `admin_users` row. An identity that passes Access but has no row gets a 403 and an alert, and the console shows "No admin access".

## Same origin API route

The console calls `/v1/admin/*` on its own origin (`apps/web/src/routes/admin/adminClient.ts`). That keeps the Access cookie and the host-only, `SameSite=Strict` admin session cookie first party, needs no CORS and no credentialed cross-origin request, and lets the CSP say `connect-src 'self'`. In production this needs one edge route:

- A Cloudflare Worker route (or Pages Function) on `admin.hermi.world/v1/admin/*` that forwards the request unchanged, with all headers including `Cf-Access-Jwt-Assertion` and `Cookie`, to `https://api.hermi.world`. It must not add caching. The API answers `Cache-Control: no-store` and `X-Robots-Tag: noindex` itself.
- **The user's assertion.** The route sits behind the same Access application as the console, so Access has already put the signed-in admin's `Cf-Access-Jwt-Assertion` on the request. The Worker forwards that header untouched; the API verifies it, and it is the only identity the API trusts. The Worker never mints or edits it.
- **The Worker reaching the API.** `api.hermi.world/v1/admin/*` is its own Access destination (see "What is protected"), so the Worker's subrequest must pass that gate too. Give the Worker an Access service token (Zero Trust, Service Auth) and add a Service Auth policy for it on that destination. Store `CF-Access-Client-Id` and `CF-Access-Client-Secret` as Worker secrets and send them on the subrequest. Access then lets the call through and, because the user's own assertion is still in the request, the API still sees who is calling. A service token alone never opens an admin route: it has no email, so the API's `admin_users` lookup fails.
- Apart from the two token headers, the Worker holds no logic. It is a pass-through.

In local development the Vite dev server proxies `/v1/admin` to `http://localhost:8100` (`apps/web/vite.config.ts`).

## Response headers

`apps/web/public/_headers` gives the two admin hosts a strict policy: `default-src 'none'`, scripts, styles, fonts and images from `'self'` only, `connect-src 'self'`, `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex, nofollow` and `Cache-Control: no-store`. There is no inline script, no `unsafe-eval` and no third party host. The console also loads no Sentry or PostHog. `apps/web/src/routes/admin/csp.test.ts` fails if any of that loosens.

## Origin lock

The origin accepts admin traffic only through Cloudflare (authenticated origin pulls, 08 section 9 rule 1). A request that reaches the API without a valid Access JWT is refused and logged as `admin_assertion_rejected`.

## The first admin

There is no sign-up path to admin. After the person has signed up as a normal user (so a `users` row exists), run on a machine with `DATABASE_URL_SYSTEM` set:

```
hermi admin-grant <email>              # role owner by default; see --help for other roles
```

It writes the `admin_users` row and does nothing on a repeat. Then add the email to the Access policy, open `https://admin.hermi.world`, sign in through Google SSO, register a passkey (or an authenticator app) and save the recovery codes. The owner activates later admins from Admin users in the console.

## Local and CI: the fake-Access signer

With `ADMIN_AUTH_MODE=dev` (only when `ENVIRONMENT` is `local` or `ci`) the API mounts `POST /v1/dev/admin-session`, which mints a JWT of the same shape for a seeded admin. The console shows "Local admin" when the API answers 401 in a local build; picking an email there stores the assertion for the browser session and sends it as `Cf-Access-Jwt-Assertion`. The API runs the real verification code in both modes. 2FA enrolment and step-up work the same. Seed the admin with `hermi admin-grant admin@hermi.test` first.

## Checks before launch

1. Open `https://admin.hermi.world` in a private window: Access must ask for SSO first.
2. `curl -i https://api.hermi.world/v1/admin/auth/session` with no token must not reach the API (an Access redirect or 403 from the edge).
3. The same call through `admin.hermi.world` with a valid Access session but no admin row returns 403 `admin_not_enabled`.
4. Response headers on the console match `apps/web/public/_headers`. A scanner such as securityheaders.com needs an Access bypass or a service token to see them.
5. `robots.txt` is not served to crawlers because Access sits in front. Every response also carries `X-Robots-Tag: noindex`.
