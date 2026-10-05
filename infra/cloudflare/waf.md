# Cloudflare WAF and rate rules

Configured in the dashboard for the `hermi.world` zone. Limits mirror 10 section 2.3 and are starting values. The app enforces the same limits; these are the second layer. Every limited response is 429.

## Origin lock

- Authenticated Origin Pulls on for `api`, `api.staging` and `go`. Render accepts only Cloudflare traffic.
- `TRUSTED_PROXY_CIDRS` (Render env group) holds Cloudflare's published ranges (https://www.cloudflare.com/ips/). Refresh when they change. Render's internal proxy range must be trusted there too, or the app sees one shared peer address. Before the signup limits (5 new accounts per IP a day) go live, check on staging that the app sees the real client address (two requests from different networks must land in different buckets).

## Managed protection

- Cloudflare Managed Ruleset and OWASP Core Ruleset: on, action Block, paranoia level 1.
- Bot Fight Mode: on. Turnstile on signup (10 section 2.4).

## Custom rules

| Name | Expression | Action |
|---|---|---|
| Admin behind Access | `http.host eq "admin.hermi.world" or starts_with(http.request.uri.path, "/v1/admin/")` | Cloudflare Access application (policy: named admins plus 2FA, 08 section 2) |
| Non-API paths on the API host | `http.host in {"api.hermi.world" "api.staging.hermi.world"} and not (starts_with(http.request.uri.path, "/v1/") or starts_with(http.request.uri.path, "/health/") or starts_with(http.request.uri.path, "/.well-known/") or starts_with(http.request.uri.path, "/go/") or http.request.uri.path in {"/docs" "/openapi.json"})` | Block |

## Rate limiting rules (per IP)

| Name | Match | Limit | Action |
|---|---|---|---|
| Email code send | `POST /v1/auth/` paths that send a code | 20 per hour | Block 1 hour |
| Session bootstrap | `POST /v1/auth/session` and `POST /v1/me/bootstrap` | 30 per 10 minutes | Block 10 minutes |
| Read API | `GET /v1/*` | 1200 per minute | Block 1 minute |
| Write API | `POST, PUT, PATCH, DELETE /v1/*` | 600 per minute | Block 1 minute |
| Public and share pages | `/p/*`, `/s/*` | 120 per minute | Block 1 minute |
| Calendar feeds | `GET /v1/calendar/*` | 600 per hour | Block 1 hour |

Check the path prefixes against the shipped routes (WF-042 onward) before turning a rule on. Staging mirrors production rules in log-only mode first.

The referral open limit (30 per hour) is enforced by the app only. The `/go/{click_id}` (120 per minute) and webhook signature failure limits also have Cloudflare rules, listed in `rules.md` ("Auth and public route rate rules").
