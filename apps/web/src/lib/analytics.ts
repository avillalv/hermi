/**
 * Typed product analytics (10-quality-security-launch.md section 4). The catalogue in packages/shared is the only
 * source of event names and properties. No PostHog SDK is installed, so session replay, autocapture and pageview
 * autocapture are off by construction; events are POSTed to `${host}/capture/` like the API's PostHogSink.
 * No PII: a string property is a code or bucket (max 64 chars, no "@"). Identify with users.id only, never email or name.
 * Opt-out (Global Privacy Control, or the user's setting via `setAnalyticsOptOut`) drops every event. Events are sent at once, so nothing is queued to drop.
 */
import { COMMON_PROPERTIES, EVENT_CATALOGUE, isEventName, type EventName, type EventProps } from "../../../../packages/shared/src/events"
import { env } from "./env"

const MAX_STR = 64
const OPT_OUT_KEY = "hermi.analytics.optout"
const SESSION_KEY = "hermi.analytics.session"
const ONCE_PREFIX = "hermi.analytics.once."
const POSTHOG_HOST = "https://us.i.posthog.com" // shortcut: fixed US host; add VITE_POSTHOG_HOST when the project moves region.

type Wire = { event: string; distinct_id: string; properties: Record<string, unknown>; timestamp: string }
type Kind = string | readonly string[]

const ok = (kind: Kind, v: unknown): boolean => {
  const str = (x: unknown) => typeof x === "string" && x.length <= MAX_STR && !x.includes("@")
  if (kind === "bool") return typeof v === "boolean"
  if (kind === "int") return Number.isInteger(v)
  if (kind === "str") return str(v)
  if (kind === "strs") return Array.isArray(v) && v.every(str)
  return (kind as readonly unknown[]).includes(v)
}

/** Throws on a catalogue breach. */
export function validate(name: string, props: Record<string, unknown> = {}): void {
  if (!isEventName(name)) throw new Error(`analytics: unknown event ${name}`)
  const spec = EVENT_CATALOGUE[name] as Record<string, Kind>
  for (const [k, v] of Object.entries(props)) {
    const kind = spec[k] ?? (COMMON_PROPERTIES as Record<string, Kind>)[k]
    if (kind === undefined) throw new Error(`analytics: ${name} has no property ${k}`)
    if (!ok(kind, v)) throw new Error(`analytics: ${name}.${k} value not allowed`)
  }
}

const store = (): Storage | null => {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

let optOutPref = store()?.getItem(OPT_OUT_KEY) === "1"
let userId: string | null = null
const sink: Wire[] = [] // in-memory when PostHog is not configured (tests, local)

export const isOptedOut = (): boolean =>
  optOutPref || (typeof navigator !== "undefined" && (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl === true)

/** The user's analytics choice (Settings, Privacy). */
export function setAnalyticsOptOut(value: boolean): void {
  optOutPref = value
  try {
    if (value) store()?.setItem(OPT_OUT_KEY, "1")
    else store()?.removeItem(OPT_OUT_KEY)
  } catch {
    /* storage blocked: the in-memory choice still holds for this page */
  }
}

/** users.id only. Call after sign-in; never pass an email or a name. */
export const setAnalyticsUser = (id: string | null): void => void (userId = id)

const sessionId = (): string => {
  try {
    let s = window.sessionStorage.getItem(SESSION_KEY)
    if (!s) window.sessionStorage.setItem(SESSION_KEY, (s = crypto.randomUUID()))
    return s
  } catch {
    return "unknown"
  }
}

const send = (e: Wire): void => {
  const key = env.posthogKey
  if (!key || env.appEnv === "ci" || env.appEnv === "test") return void sink.push(e)
  const body = JSON.stringify({ api_key: key, ...e })
  const url = `${POSTHOG_HOST}/capture/`
  // sendBeacon survives page unload; fetch is the fallback. Failures are dropped, never thrown.
  if (typeof navigator.sendBeacon === "function" && navigator.sendBeacon(url, new Blob([body], { type: "text/plain" }))) return
  void fetch(url, { method: "POST", body, keepalive: true }).catch(() => {})
}

function capture<N extends EventName>(name: N, props?: EventProps<N>): boolean {
  try {
    validate(name, props as Record<string, unknown>)
  } catch (err) {
    if (import.meta.env.PROD) return false // drop in production, never send
    throw err
  }
  if (isOptedOut()) return false
  const common = { app_version: env.releaseSha, platform: "web", locale: navigator.language, env: env.appEnv, session_id: sessionId() }
  const properties = { ...common, ...props }
  // Window event kept for tests and any in-page listener (the "hermi:event" contract predates the sink).
  window.dispatchEvent(new CustomEvent("hermi:event", { detail: { event: name, props } }))
  send({ event: name, distinct_id: userId ?? properties.session_id, properties, timestamp: new Date().toISOString() })
  return true
}

/** Fire once per browser and user for a flag key (StrictMode double effects, repeat visits). shortcut: per browser, not per account; server-side count if it must be per user. */
function captureOnce<N extends EventName>(key: string, name: N, props?: EventProps<N>): boolean {
  const s = store()
  const flag = `${ONCE_PREFIX}${key}.${userId ?? "anonymous"}`
  if (s?.getItem(flag)) return false
  const sent = capture(name, props)
  if (sent) s?.setItem(flag, "1")
  return sent
}

export const analytics = { capture, captureOnce }
/** Test helpers. */
export const __sink = sink
export const __resetAnalytics = (): void => {
  sink.length = 0
  optOutPref = false
  userId = null
}
