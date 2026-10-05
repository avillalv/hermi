# Cloudflare records and rules

Records for `hermi.world`. Values marked `<...>` come from the provider dashboard. Check mail records with `infra/scripts/check-mail-auth hermi.world`.

## DNS

| Type | Name | Value | Notes |
|---|---|---|---|
| CNAME | `app` | Cloudflare Pages project | Web app |
| CNAME | `api` | Render service host | API, proxied off if Render needs direct TLS |
| CNAME | `api.staging` | Render staging service host | Staging API (04 section 1.1) |
| CNAME | `go` | Render service host (same service as `api`) | Affiliate redirect host `https://go.hermi.world/go/{click_id}` (04 section 1.1) |
| CNAME | `admin` | Cloudflare Pages project (same web build as `app`) | Admin console. Put Cloudflare Access in front of it and of `/v1/admin/*` (08 sections 1 and 2, 10 section 4) |
| CNAME | `@` and `www` | Cloudflare Pages project for the landing page | Landing page (WF-002). `www` redirects to the apex |
| CNAME | `status` | Better Stack status page host | Hosted outside Render and Pages |
| MX | `@` | `<inbound mail host>` priority 10 | Receives `support@`. Provider or Cloudflare Email Routing |
| TXT | `@` | `v=spf1 include:<inbound provider> include:amazonses.com ~all` | SPF. Resend sends through Amazon SES; use the exact include Resend shows |
| TXT | `resend._domainkey` | `p=<public key from Resend>` | DKIM, selector `resend` |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:support@hermi.world` | DMARC. Start at `none`, move to `quarantine` after two clean weeks |

Resend may ask for its return-path records (MX and SPF on a `send` subdomain). Add them exactly as shown.

## Mailboxes

- `support@hermi.world`: inbound, forwarded to the owner. Also the Wikimedia contact (`WIKIMEDIA_CONTACT`).
- `no-reply@hermi.world`: send only, through Resend. No inbox.
- `hello@hermi.world`: the `EMAIL_FROM` address (`Hermi <hello@hermi.world>`).

## Resend sending domain

Add `hermi.world` as a sending domain in Resend, copy the DKIM and SPF values into the table above, wait for "Verified", then run the check script.

## Redirect

`heyhermi.com` and `www.heyhermi.com`: proxied, with a Redirect Rule to `https://hermi.world` (301, preserve path and query).

## Auth and public route rate rules (WF-028)

The per-IP rate limiting rules live in `waf.md` ("Rate limiting rules"). WF-028 adds these on top, in the same Cloudflare dashboard. For the signup and share view rows the app enforces the same numbers in `apps/api/hermi/security/rate_limit.py` (10 section 2.3), and the app limits are changeable without a deploy or restart in the `setting_rate_limits` row (admin console, 08 section 6.16). Change the dashboard value by hand when you change that row, because Cloudflare does not read it. The `/go` and webhook signature failure limits get Cloudflare rules here; the referral open limit stays app only (`waf.md`).

| Name | Match | Limit | Action |
|---|---|---|---|
| Account bootstrap | `POST /v1/me/bootstrap` | 30 per 10 minutes per IP | Block 10 minutes. Same numbers as the session bootstrap row in `waf.md` (10 section 2.3); the app counts new accounts per IP (5 a day) on top |
| Share link views | `GET /v1/shared/*` | 120 per minute per IP | Block 1 minute |
| Affiliate redirect | `GET /go/*` on host `go` | 120 per minute per IP | Block 1 minute |
| Webhook signature failures | `POST /v1/webhooks/*` with a 4xx response | 30 per minute per IP | Block 1 hour |

Log-only for one week on staging before turning each rule on. Turnstile stays on signup (`waf.md`).
