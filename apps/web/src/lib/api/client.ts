// shortcut: untyped thin fetch wrapper. Upgrade when gen:api lands to openapi-fetch with the 04 section 13
// extras (X-Hermi-Client, X-Client-Version, X-Request-Id, Idempotency-Key, typed ApiError, If-Match/ETag).
import { env } from "../env"

/** Auth state lives in the sign-in module (WF-018); the client only needs these three hooks. */
export type AuthHooks = {
  /** The current access token, or null when signed out. */
  getAccessToken: () => string | null | Promise<string | null>
  /** Get a new access token, or null when the session cannot be renewed. */
  refresh: () => Promise<string | null>
  /** Called once when a 401 survives a refresh. */
  onSignedOut: () => void
}

export type ApiResult<T = unknown> = {
  data?: T
  /** The problem+json body of a non-2xx response. */
  error?: unknown
  response: Response
}

/** Thrown by a query function so the screen can map the failure with `errorKind`. */
export class ApiError extends Error {
  constructor(readonly result: ApiResult) {
    super(`api ${result.response.status}`)
  }
}

export type ApiClientOptions = {
  baseUrl?: string
  auth: AuthHooks
  fetch?: typeof fetch
}

type Opts = { query?: Record<string, string | number | boolean | undefined>; headers?: HeadersInit; signal?: AbortSignal }

export function createApiClient({ baseUrl = env.apiBaseUrl, auth, fetch: f }: ApiClientOptions) {
  const base = baseUrl.replace(/\/+$/, "")
  const doFetch: typeof fetch = f ?? ((...a) => fetch(...a))
  let refreshing: Promise<string | null> | null = null
  let signedOutFor: Promise<string | null> | null = null

  // One refresh at a time, so concurrent 401s do not each burn a refresh token.
  const refreshOnce = () => {
    refreshing ??= auth.refresh().finally(() => (refreshing = null))
    return refreshing
  }
  // Sign-out fires once per refresh cycle, however many concurrent requests failed with it.
  const signOutOnce = (cycle: Promise<string | null>) => {
    if (signedOutFor === cycle) return
    signedOutFor = cycle
    auth.onSignedOut()
  }

  async function send(method: string, path: string, body: unknown, o: Opts): Promise<ApiResult> {
    const qs = o.query
      ? "?" +
        new URLSearchParams(
          Object.entries(o.query).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]),
        )
      : ""
    const url = `${base}${path}${qs}`
    const attempt = async (token: string | null) => {
      const headers = new Headers(o.headers)
      if (token) headers.set("Authorization", `Bearer ${token}`)
      if (body !== undefined) headers.set("Content-Type", "application/json")
      return doFetch(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: "omit", // bearer only, never cookies
        signal: o.signal,
      })
    }

    let res = await attempt(await auth.getAccessToken())
    if (res.status === 401) {
      const cycle = refreshOnce()
      const token = await cycle.catch(() => null)
      if (token) res = await attempt(token)
      if (!token || res.status === 401) signOutOnce(cycle)
    }
    const text = await res.text().catch(() => "")
    let parsed: unknown
    try {
      parsed = text ? JSON.parse(text) : undefined
    } catch {
      // A 2xx with a body that is not JSON is a broken response, so it is an error.
      return { error: text, response: res }
    }
    return res.ok ? { data: parsed, response: res } : { error: parsed, response: res }
  }

  return {
    get: <T = unknown>(path: string, o: Opts = {}) => send("GET", path, undefined, o) as Promise<ApiResult<T>>,
    post: <T = unknown>(path: string, body?: unknown, o: Opts = {}) => send("POST", path, body, o) as Promise<ApiResult<T>>,
    put: <T = unknown>(path: string, body?: unknown, o: Opts = {}) => send("PUT", path, body, o) as Promise<ApiResult<T>>,
    patch: <T = unknown>(path: string, body?: unknown, o: Opts = {}) => send("PATCH", path, body, o) as Promise<ApiResult<T>>,
    delete: <T = unknown>(path: string, o: Opts = {}) => send("DELETE", path, undefined, o) as Promise<ApiResult<T>>,
  }
}

export type ApiClient = ReturnType<typeof createApiClient>

export type ErrorKind =
  | "offline" | "unauthorized" | "limit" | "rateLimited" | "maintenance"
  | "forcedUpdate" | "notFound" | "permission" | "conflict" | "server"

export type ErrorInfo = { kind: ErrorKind; requestId?: string; /** Seconds from Retry-After. */ retryAfter?: number }

/**
 * Map a failed ApiResult, or a thrown fetch error, to the error state to show (05 4.17). Codes are 04 section 3.
 * Pass `online` in tests; it defaults to the browser.
 */
export function errorKind(failure: unknown, online: boolean = typeof navigator === "undefined" || navigator.onLine): ErrorInfo {
  if (!online) return { kind: "offline" }
  if (failure instanceof ApiError) failure = failure.result
  if (!(typeof failure === "object" && failure && "response" in failure)) {
    // fetch rejects with a TypeError when the network fails.
    return { kind: failure instanceof TypeError ? "offline" : "server" }
  }
  const { error, response } = failure as ApiResult
  const code = typeof (error as { code?: unknown } | undefined)?.code === "string" ? (error as { code: string }).code : ""
  const body = (error as { request_id?: unknown } | undefined)?.request_id
  const requestId = response.headers.get("X-Request-Id") ?? (typeof body === "string" ? body : undefined)
  const bodyRetry = (error as { retry_after_seconds?: unknown } | undefined)?.retry_after_seconds
  const ra = Number(response.headers.get("Retry-After") ?? bodyRetry)
  const retryAfter = ra > 0 && Number.isFinite(ra) ? ra : undefined
  const s = response.status
  const kind: ErrorKind =
    s === 426 || code === "client_upgrade_required" ? "forcedUpdate"
    : s === 503 && code === "feature_disabled" ? "maintenance"
    : s === 401 ? "unauthorized"
    : s === 402 || (s === 429 && (code === "provider_budget_exhausted" || code === "quota_exceeded")) ? "limit"
    : s === 403 && code === "insufficient_role" ? "permission"
    : s === 404 || s === 410 ? "notFound"
    : s === 409 ? "conflict"
    : s === 429 ? "rateLimited"
    : "server"
  return { kind, requestId, retryAfter }
}
