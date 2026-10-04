import { describe, expect, test, vi } from "vitest"
import { AuthError, createSupabaseIdentity, selectIdentity, unconfiguredIdentity } from "./identity"

const client = (auth: Record<string, unknown>) => ({ auth }) as never
const ok = (extra: object = {}) => ({ data: { session: { access_token: "jwt" }, ...extra }, error: null })
const fail = (e: object) => ({ data: { session: null }, error: e })
const code = async (p: Promise<unknown>) => p.then(() => "none", (e) => (e instanceof AuthError ? e.code : "other"))

describe("createSupabaseIdentity", () => {
  test("sendCode asks for an email code and creates the user if new", async () => {
    const signInWithOtp = vi.fn(async () => ({ data: {}, error: null }))
    await createSupabaseIdentity(client({ signInWithOtp })).sendCode("a@b.co")
    expect(signInWithOtp).toHaveBeenCalledWith({ email: "a@b.co", options: { shouldCreateUser: true } })
  })

  test("verifyCode returns the access token", async () => {
    const verifyOtp = vi.fn(async () => ok())
    expect(await createSupabaseIdentity(client({ verifyOtp })).verifyCode("a@b.co", "123456")).toBe("jwt")
    expect(verifyOtp).toHaveBeenCalledWith({ email: "a@b.co", token: "123456", type: "email" })
  })

  test("oauth starts the redirect for apple and google", async () => {
    const signInWithOAuth = vi.fn(async () => ({ data: {}, error: null }))
    const id = createSupabaseIdentity(client({ signInWithOAuth }), "https://app.test/sign-in")
    void id.oauth("apple")
    void id.oauth("google")
    await Promise.resolve()
    expect(signInWithOAuth).toHaveBeenNthCalledWith(1, { provider: "apple", options: { redirectTo: "https://app.test/sign-in" } })
    expect(signInWithOAuth).toHaveBeenNthCalledWith(2, { provider: "google", options: { redirectTo: "https://app.test/sign-in" } })
  })

  test("restore returns the stored session token or null; signOut ends the session", async () => {
    const getSession = vi.fn(async () => ({ data: { session: { access_token: "jwt" } }, error: null }))
    const signOut = vi.fn(async () => ({ error: null }))
    const id = createSupabaseIdentity(client({ getSession, signOut }))
    expect(await id.restore?.()).toBe("jwt")
    getSession.mockResolvedValueOnce({ data: { session: null as never }, error: null })
    expect(await id.restore?.()).toBeNull()
    await id.signOut?.()
    expect(signOut).toHaveBeenCalled()
  })

  test.each([
    [{ status: 429, code: "over_email_send_rate_limit", message: "x" }, "rate_limited"],
    [{ status: 400, code: "otp_expired", message: "Token has expired or is invalid" }, "wrong_code"],
    [{ status: 403, code: "otp_expired", message: "Email link is expired" }, "expired"],
    [{ name: "AuthRetryableFetchError", status: 0, message: "Failed to fetch" }, "offline"],
    [{ status: 500, code: "unexpected_failure", message: "boom" }, "unavailable"],
    [{ status: 400, code: "provider_disabled", message: "Unsupported provider" }, "unavailable"],
  ])("maps %j to %s", async (err, expected) => {
    const verifyOtp = vi.fn(async () => fail(err))
    expect(await code(createSupabaseIdentity(client({ verifyOtp })).verifyCode("a@b.co", "000000"))).toBe(expected)
  })

  test("a thrown network error maps to offline", async () => {
    const signInWithOtp = vi.fn(async () => {
      throw new TypeError("Failed to fetch")
    })
    expect(await code(createSupabaseIdentity(client({ signInWithOtp })).sendCode("a@b.co"))).toBe("offline")
  })

  test("a verify result without a session is unavailable", async () => {
    const verifyOtp = vi.fn(async () => ({ data: { session: null }, error: null }))
    expect(await code(createSupabaseIdentity(client({ verifyOtp })).verifyCode("a@b.co", "123456"))).toBe("unavailable")
  })
})

describe("selectIdentity", () => {
  const create = vi.fn(() => client({}))
  test("uses Supabase only when both the URL and the anon key are set", () => {
    expect(selectIdentity({ supabaseUrl: "https://x.supabase.co", supabaseAnonKey: "k" }, create)).not.toBe(unconfiguredIdentity)
    expect(create).toHaveBeenCalledWith("https://x.supabase.co", "k")
  })
  test.each([[{}], [{ supabaseUrl: "https://x" }], [{ supabaseAnonKey: "k" }]])("falls back to unconfigured for %j", (e) => {
    create.mockClear()
    expect(selectIdentity(e, create)).toBe(unconfiguredIdentity)
    expect(create).not.toHaveBeenCalled()
  })
})
