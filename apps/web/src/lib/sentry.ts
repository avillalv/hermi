import * as Sentry from "@sentry/react"
import type { ErrorEvent } from "@sentry/react"
import { env, type WebEnv } from "./env"

// Same shapes as apps/api/hermi/logging_setup.py: emails, bearer tokens, JWTs, key=value secrets
// and calendar feed URLs (the token sits in the path).
const SECRET = new RegExp(
  [
    String.raw`Bearer\s+[\w.~+/=-]+`,
    String.raw`eyJ[\w-]+\.eyJ[\w-]+\.[\w-]*`,
    String.raw`(?<!\w)sk[-_][\w-]{6,}`,
    String.raw`[\w-]*(?:key|token|secret|password)[\w-]*=[^&\s"',;]+`,
    String.raw`[\w.+-]+@[\w-]+(?:\.[\w-]+)+`,
    String.raw`(?:(?:webcal|https?)://|/v1/calendar/)[^\s"',;]*\.ics[^\s"',;]*`,
    String.raw`/(?:v1/)?(?:invites?|shared)/[^\s/{}"',;?#]+`,
    String.raw`webcal://[^\s"',;]+`,
    String.raw`https?://[^/\s]*icloud\.com/published/[^\s"',;]+`,
  ].join("|"),
  "gi",
)
const KEY = /key|secret|token|password|authorization|cookie|dsn|prompt|feed_?url/i
const DROP_REQUEST = ["query_string", "cookies", "data", "env"] as const

function mask(v: unknown, key = ""): unknown {
  if (KEY.test(key)) return "[redacted]"
  if (typeof v === "string") return v.replace(SECRET, "[redacted]")
  if (Array.isArray(v)) return v.map((x) => mask(x))
  if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, mask(x, k)]))
  return v
}

/** before_send: opaque user id only, no query string, cookies or body, secrets masked everywhere else. */
export function scrubEvent<T extends ErrorEvent>(event: T): T {
  if (event.user) event.user = event.user.id ? { id: event.user.id } : {}
  const req = event.request
  if (req) {
    for (const k of DROP_REQUEST) delete (req as Record<string, unknown>)[k]
    if (req.url) req.url = req.url.split("?")[0]
  }
  return mask(event) as T
}

/** Starts Sentry when VITE_SENTRY_DSN is set. `init` is injectable for tests. */
export function initSentry(
  e: Pick<WebEnv, "sentryDsn" | "releaseSha" | "appEnv"> = env,
  init: (o: Sentry.BrowserOptions) => unknown = Sentry.init,
): boolean {
  if (!e.sentryDsn) return false
  init({
    dsn: e.sentryDsn,
    release: e.releaseSha,
    environment: e.appEnv,
    tracesSampleRate: 0,
    beforeSend: scrubEvent,
    beforeBreadcrumb: (b) => mask(b) as typeof b,
  })
  return true
}
