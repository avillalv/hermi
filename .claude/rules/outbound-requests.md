---
description: Use when writing code that fetches a URL, calls a third party, handles a user-supplied URL or builds a partner link. Airbnb, Vrbo and Booking.com pages are never fetched.
paths:
  - "apps/api/hermi/providers/**"
  - "apps/api/hermi/security/ssrf.py"
  - "apps/api/hermi/modules/imports/**"
  - "apps/api/hermi/modules/ai/policy.py"
  - "apps/api/hermi/modules/affiliate/**"
---

# Outbound request rules

Authority: non-negotiable rules 3 and 4 in `app-buildout/README.md`, `04-api-spec.md` section 5.26 (imports,
limits and the SSRF guard), `02-architecture.md` sections 3 and 5.4, and `06-ai-agents-spec.md` section 2.4
(`BLOCKED_HOSTS`). If you need to break one of these, change the document in the same commit and say why.

## Never fetch Airbnb, Vrbo or Booking.com

- One code constant, `BLOCKED_HOSTS` (`ai/policy.py`), is the only list. It is matched by suffix with
  `blocked_domain(host)`, so subdomains and country domains (`airbnb.co.kr`, `www.airbnb.co.uk`) are covered and a
  lookalike such as `notairbnb.com` is not.
- No admin-editable value: not in `feature_flags`, `kill_switches`, settings or the admin console. The Anthropic
  tool lists and the CLI `WebFetch(domain:...)` deny rules are generated from the constant, never typed twice. The
  CLI matches whole hosts only, so the claude_cli provider also checks each fetched URL with `blocked_domain`
  (see `ai-provider.md`).
- A test covers the bare host, `www`, a subdomain, a country domain, a lookalike and a redirect hop to a blocked
  host.
- This applies to everything that fetches: the feed fetcher, link preview, agent tools, rechecks and redirects. A
  URL found inside an imported calendar event or pasted text stays plain text in a note. It is never followed,
  rewritten or given an affiliate link.
- No scraping or crawling libraries in `apps/api` or `apps/worker` (for example Scrapy, Beautiful Soup used as a
  fetcher, Selenium, Puppeteer or a headless browser). Playwright is for `apps/web/e2e` only.

## User-supplied URLs

- Only `providers/feed_fetcher.py` and `providers/link_preview.py` fetch a URL a user supplied, and both go
  through `security/ssrf.py`. No other code opens a connection to a user-supplied host.
- The claude_cli `recheck` fetcher and any other fetch of an AI-found URL also go through `security/ssrf.py`.
- The guard follows 02 section 5.4 in order: https and port 443 only, no userinfo, a DNS name and not an IP
  literal, at most 2,048 characters; refuse blocked hosts and Hermi's own; resolve DNS ourselves and refuse unless
  every answer is public; connect to the validated address (pinned); at most 3 redirects, each hop revalidated
  from the start.
- The table-driven suite of hostile addresses stays green in CI. The fake feed host is allowed only when
  `ENVIRONMENT` is `local` or `ci`.
- Raw files and pasted text are never stored. A feed address is stored encrypted only while polling is on, and
  never appears in logs or Sentry.

## Limits and records

- Limits come from the table in 04 section 5.26. For a feed fetch: 5 second connect, 15 second total, body at
  most 2 MB (cut while streaming, also after decompression), the body must start with `BEGIN:VCALENDAR`, no
  cookies and no authorization headers, `User-Agent: HermiCalendarImport/1.0`.
- Every other outbound call has an explicit timeout and a response size limit. A client with no timeout is a bug.
- Only `providers/*` import `httpx` or the Anthropic SDK (one exception: `security/jwt.py` fetches our own
  auth provider's JWKS from `SUPABASE_JWKS_URL`, no redirects, 5 second timeout, 256 KB cap), and every outbound call writes a `provider_calls` row
  (provider, endpoint, status, latency; for the feed fetcher the host only, never the path).

## Partner links and evidence

- Outbound partner links reach a user only through `/go/{click_id}`. Only `affiliate.service` builds a partner
  URL, from `affiliate_link_templates`; no other module concatenates one. Nothing is ever ranked by commission.
- Every AI-found fact stores the URL it came from, and the URL passes `source_problem` (a public http(s) page that
  is not on a blocked host). A fare must have been seen on a page during the run.

## What must not change without a decision

- **The blocked-host list being code.** An editable list is a list someone can empty.
- **Revalidating every redirect hop.** A first hop that passes can redirect to a blocked or private host.
- **The pinned address.** Without it, DNS can change between the check and the connection.

## Checkable by grep

```bash
# scraping libraries (prints nothing when clean)
grep -rniE "scrapy|beautifulsoup|bs4|selenium|puppeteer|mechanize" apps/api apps/worker --include=pyproject.toml --include=*.py
# an HTTP client imported outside providers (prints nothing when clean)
grep -rnE "import httpx|from httpx|import requests|from requests" apps --include=*.py | grep -v -e "apps/api/hermi/providers/" -e "apps/api/hermi/security/jwt.py" -e "/tests/"
```
