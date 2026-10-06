import { describe, expect, it, vi } from "vitest"
import type { ErrorEvent } from "@sentry/react"
import { initSentry, scrubEvent } from "./sentry"

const EMAIL = "ana.perez+trip@example.com"
const FEED = "https://calendar.example.com/ical/abcSECRETtoken123/basic.ics"

describe("scrubEvent", () => {
  it("keeps only the opaque user id and drops query, cookies and body", () => {
    const out = scrubEvent(({
      user: { id: "0190", email: EMAIL, ip_address: "1.2.3.4", username: "ana" },
      request: {
        url: "https://app.hermi.world/trips/1?token=zzz",
        query_string: "token=zzz",
        cookies: { s: "1" },
        data: { prompt: "hi" },
        headers: { Authorization: "Bearer abc123tok", "x-api-key": "k", accept: "*/*" },
      },
      message: `failed for ${EMAIL} at ${FEED}`,
      extra: { prompt: "Plan Lisbon", feed_url: FEED },
      breadcrumbs: [{ message: `GET ${FEED}` }],
    }) as never) as ErrorEvent
    const blob = JSON.stringify(out)
    for (const bad of [EMAIL, "1.2.3.4", "zzz", "abc123tok", "Plan Lisbon", "abcSECRETtoken123", '"ana"']) {
      expect(blob).not.toContain(bad)
    }
    expect(out.user).toEqual({ id: "0190" })
    expect(out.request?.headers?.accept).toBe("*/*")
  })
})

describe("token paths and feeds", () => {
  it("masks invite and shared segments and webcal or iCloud feeds in events and breadcrumbs", () => {
    const WEBCAL = "webcal://h.example/cal/SECRETwebcal77"
    const ICLOUD = "https://p12-caldav.icloud.com/published/2/SECRETicloud88"
    const out = scrubEvent(({
      request: { url: "https://app.hermi.world/invite/INVTOKEN55?x=1" },
      transaction: "/shared/SHRTOKEN66",
      contexts: { page: { url: "https://app.hermi.world/claim/CLAIMURL22" } },
      message: `GET /v1/invites/APITOKEN77 /v1/shared/APISHR88 /claim/CLAIMMSG11 ${WEBCAL} ${ICLOUD}`,
      breadcrumbs: [{ data: { url: "/invite/CRUMBTOKEN99" } }, { data: { url: "/claim/CLAIMCRUMB33" } }],
    }) as never) as ErrorEvent
    const blob = JSON.stringify(out)
    for (const bad of ["INVTOKEN55", "SHRTOKEN66", "APITOKEN77", "APISHR88", "SECRETwebcal77", "SECRETicloud88", "CRUMBTOKEN99", "CLAIMMSG11", "CLAIMURL22", "CLAIMCRUMB33"]) {
      expect(blob).not.toContain(bad)
    }
  })

  it("masks a token path in a breadcrumb through beforeBreadcrumb", () => {
    const init = vi.fn()
    initSentry({ sentryDsn: "https://k@o1.ingest.sentry.io/1", releaseSha: "r", appEnv: "e" }, init)
    const b = init.mock.calls[0][0].beforeBreadcrumb({ data: { url: "/shared/CRUMBTOKEN99" } })
    expect(JSON.stringify(b)).not.toContain("CRUMBTOKEN99")
  })
})

describe("initSentry", () => {
  it("is a no-op without a DSN", () => {
    const init = vi.fn()
    expect(initSentry({ sentryDsn: undefined, releaseSha: "r", appEnv: "e" }, init)).toBe(false)
    expect(init).not.toHaveBeenCalled()
  })

  it("sends release and environment, with the scrubber", () => {
    const init = vi.fn()
    expect(initSentry({ sentryDsn: "https://k@o1.ingest.sentry.io/1", releaseSha: "abc123d", appEnv: "staging" }, init)).toBe(true)
    const o = init.mock.calls[0][0]
    expect(o).toMatchObject({ release: "abc123d", environment: "staging", beforeSend: scrubEvent })
  })
})
