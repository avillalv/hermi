import { describe, expect, it, vi } from "vitest"
import { ApiError, errorKind } from "./client"

const res = (status: number, headers: Record<string, string> = {}) => new Response(null, { status, headers })
const r = (status: number, error?: unknown, headers?: Record<string, string>) => ({ error, response: res(status, headers) })

describe("errorKind", () => {
  it("maps a thrown network failure to offline", () => {
    expect(errorKind(new TypeError("Failed to fetch")).kind).toBe("offline")
  })
  it("maps any failure to offline while the browser reports no connection", () => {
    const spy = vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
    expect(errorKind(r(500)).kind).toBe("offline")
    spy.mockRestore()
  })
  it.each([
    [401, "unauthorized"],
    [402, "limit"],
    [403, "server"],
    [410, "notFound"],
    [404, "notFound"],
    [409, "conflict"],
    [426, "forcedUpdate"],
    [429, "rateLimited"],
    [500, "server"],
    [502, "server"],
    [503, "server"],
    [504, "server"],
  ])("maps %i to %s", (status, kind) => {
    expect(errorKind(r(status)).kind).toBe(kind)
  })
  it("uses the problem code when the status is ambiguous", () => {
    expect(errorKind(r(402, { code: "insufficient_credits" })).kind).toBe("limit")
    expect(errorKind(r(402, { code: "limit_reached" })).kind).toBe("limit")
    expect(errorKind(r(503, { code: "feature_disabled" })).kind).toBe("maintenance")
    expect(errorKind(r(403, { code: "insufficient_role" })).kind).toBe("permission")
    expect(errorKind(r(403, { code: "ai_consent_required" })).kind).toBe("server")
    expect(errorKind(r(429, { code: "provider_budget_exhausted" })).kind).toBe("limit")
    expect(errorKind(r(503, { code: "provider_unavailable" })).kind).toBe("server")
    expect(errorKind(r(400, { code: "client_upgrade_required" })).kind).toBe("forcedUpdate")
    expect(errorKind(r(429, { code: "quota_exceeded" })).kind).toBe("limit")
  })
  it("reads Retry-After in seconds and ignores junk", () => {
    expect(errorKind(r(429, undefined, { "Retry-After": "30" })).retryAfter).toBe(30)
    expect(errorKind(r(429, undefined, { "Retry-After": "soon" })).retryAfter).toBeUndefined()
  })
  it("ignores a zero Retry-After and reads retry_after_seconds from the body", () => {
    expect(errorKind(r(429, undefined, { "Retry-After": "0" })).retryAfter).toBeUndefined()
    expect(errorKind(r(503, { code: "feature_disabled", retry_after_seconds: 90 })).retryAfter).toBe(90)
  })
  it("surfaces the request id from the header, then the problem body", () => {
    expect(errorKind(r(500, { request_id: "b" }, { "X-Request-Id": "a" })).requestId).toBe("a")
    expect(errorKind(r(500, { request_id: "b" })).requestId).toBe("b")
    expect(errorKind(r(500)).requestId).toBeUndefined()
  })
  it("treats a thrown non-network value as a server error", () => {
    expect(errorKind(new Error("boom")).kind).toBe("server")
  })
})

describe("errorKind with a thrown ApiError", () => {
  it("maps the wrapped result", () => {
    expect(errorKind(new ApiError(r(401) as never), true).kind).toBe("unauthorized")
    expect(errorKind(new ApiError(r(429, undefined, { "Retry-After": "7" }) as never), true)).toMatchObject({ kind: "rateLimited", retryAfter: 7 })
  })
})
