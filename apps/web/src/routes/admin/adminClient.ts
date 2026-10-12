// The console's own API client. It is not the customer client (`lib/api/client.ts`): the admin identity is the
// Cloudflare Access assertion plus the host-only 2FA session cookie, never a bearer token (08 section 2.2).
// Calls are same-origin under /v1/admin (infra/cloudflare/access.md), so the cookie and the Access JWT travel with no CORS.

export type AdminOk<T> = { ok: true; status: number; data: T }
export type AdminFail = { ok: false; status: number; code: string; message: string; requestId?: string; offline?: boolean }
export type AdminResult<T = unknown> = AdminOk<T> | AdminFail

const ASSERTION_KEY = "hermi.admin.dev-assertion"
let assertion: string | null = null

/** Local and CI only: the fake-Access signer's assertion, sent as `Cf-Access-Jwt-Assertion`. In production Access adds it at the edge. */
export function setDevAssertion(value: string) {
  assertion = value
  sessionStorage.setItem(ASSERTION_KEY, value)
}
const currentAssertion = () => (assertion ??= sessionStorage.getItem(ASSERTION_KEY) ?? "")

let stepUpHandler: (() => Promise<boolean>) | null = null
let stepUpInFlight: Promise<boolean> | null = null
const endedListeners = new Set<() => void>()

/** The step-up dialog registers here; it resolves true after a fresh check passes, false when cancelled. */
export function setStepUpHandler(h: (() => Promise<boolean>) | null) {
  stepUpHandler = h
}
/** Called when a call finds the 2FA session or the Access assertion gone (401). */
export function onSessionEnded(fn: () => void) {
  endedListeners.add(fn)
  return () => void endedListeners.delete(fn)
}
export function resetAdminClient() {
  assertion = null
  stepUpHandler = null
  stepUpInFlight = null
  endedListeners.clear()
}

// One dialog at a time, however many calls got a 428 together.
const askStepUp = () => {
  if (!stepUpHandler) return Promise.resolve(false)
  stepUpInFlight ??= stepUpHandler().finally(() => (stepUpInFlight = null))
  return stepUpInFlight
}

const uuid = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
const SESSION_PATH = "/v1/admin/auth/session"
// A failed second factor is a 401 too, but it answers the person typing; it is not an ended session.
const NOT_ENDED = new Set(["two_factor_failed"])

/**
 * One admin call. Writes carry an Idempotency-Key. A 428 `stepup_required` opens the step-up dialog and, after a good
 * check, repeats the call once; a cancelled dialog hands the 428 back. A 401 other than a wrong code tells the shell
 * the session ended.
 */
export async function adminRequest<T = unknown>(method: string, path: string, body?: unknown, retried = false): Promise<AdminResult<T>> {
  const headers = new Headers({ Accept: "application/json" })
  const a = currentAssertion()
  if (a) headers.set("Cf-Access-Jwt-Assertion", a)
  if (body !== undefined) headers.set("Content-Type", "application/json")
  if (method !== "GET") headers.set("Idempotency-Key", uuid())
  let res: Response
  try {
    res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), credentials: "include" })
  } catch {
    return { ok: false, status: 0, code: "offline", message: "", offline: true }
  }
  const text = await res.text().catch(() => "")
  let parsed: Record<string, unknown> | undefined
  try {
    parsed = text ? (JSON.parse(text) as Record<string, unknown>) : undefined
  } catch {
    parsed = undefined
  }
  if (res.ok) return { ok: true, status: res.status, data: parsed as T }
  const fail: AdminFail = {
    ok: false,
    status: res.status,
    code: typeof parsed?.code === "string" ? parsed.code : "error",
    message: typeof parsed?.detail === "string" ? parsed.detail : "",
    requestId: res.headers.get("X-Request-Id") ?? (typeof parsed?.request_id === "string" ? parsed.request_id : undefined),
  }
  if (res.status === 428 && !retried && (await askStepUp())) return adminRequest<T>(method, path, body, true)
  if (res.status === 401 && path !== SESSION_PATH && !NOT_ENDED.has(fail.code)) endedListeners.forEach((fn) => fn())
  return fail
}
