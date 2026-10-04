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
