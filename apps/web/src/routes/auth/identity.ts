import { createClient, type SupabaseClient } from "@supabase/supabase-js"
import { env } from "../../lib/env"

export type AuthErrorCode = "wrong_code" | "expired" | "rate_limited" | "offline" | "unavailable"

export class AuthError extends Error {
  constructor(public code: AuthErrorCode) {
    super(code)
  }
}

/**
 * The real sign-in providers (Supabase Auth: Apple, Google, email code). Each call returns the Supabase access token
 * or throws `AuthError`. Tests inject a fake.
 */
export type IdentityAdapter = {
  oauth(provider: "apple" | "google"): Promise<string>
  sendCode(email: string): Promise<void>
  verifyCode(email: string, code: string): Promise<string>
  /** The token of a session the provider already holds (after an OAuth redirect or a reload), or null. */
  restore?(): Promise<string | null>
  /** Ends the provider session so a signed-out user is not signed straight back in. */
  signOut?(): Promise<void>
}

const unavailable = async (): Promise<never> => {
  throw new AuthError("unavailable")
}

/** Default until Supabase keys are set: every provider reports "not available right now". */
export const unconfiguredIdentity: IdentityAdapter = { oauth: unavailable, sendCode: unavailable, verifyCode: unavailable }

type SbError = { name?: string; status?: number; code?: string; message?: string }

/** Supabase error to our codes. shortcut: Supabase answers a wrong and an expired code alike ("expired or is invalid"), so that text maps to wrong_code; only a bare "expired" maps to expired. */
export function mapSupabaseError(e: unknown): AuthError {
  const { name, status, code, message = "" } = (e ?? {}) as SbError
  if (status === 429 || code?.startsWith("over_")) return new AuthError("rate_limited")
  if (name === "AuthRetryableFetchError" || status === 0 || (e instanceof TypeError && /fetch|network/i.test(message)))
    return new AuthError("offline")
  if (code === "otp_expired" || /otp|token|code/i.test(message))
    return new AuthError(/invalid/i.test(message) || !/expired/i.test(message) ? "wrong_code" : "expired")
  return new AuthError("unavailable")
}

const guard = async <R extends { data: unknown; error: unknown }>(fn: () => Promise<R>): Promise<R["data"]> => {
  let r
  try {
    r = await fn()
  } catch (e) {
    throw mapSupabaseError(e)
  }
  if (r.error) throw mapSupabaseError(r.error)
  return r.data
}

/** Supabase Auth behind `IdentityAdapter`. The client is injected so tests can pass a mock. */
export function createSupabaseIdentity(
  client: Pick<SupabaseClient, "auth">,
  redirectTo = typeof window === "undefined" ? "" : `${window.location.origin}/sign-in`,
): IdentityAdapter {
  const { auth } = client
  return {
    async oauth(provider) {
      await guard(() => auth.signInWithOAuth({ provider, options: { redirectTo } }))
      // The browser leaves for the provider; `restore` picks the session up when it returns. Never settles on purpose.
      return new Promise<string>(() => {})
    },
    async sendCode(email) {
      await guard(() => auth.signInWithOtp({ email, options: { shouldCreateUser: true } }))
    },
    async verifyCode(email, token) {
      const d = await guard(() => auth.verifyOtp({ email, token, type: "email" }))
      if (!d.session) throw new AuthError("unavailable")
      return d.session.access_token
    },
    async restore() {
      return (await guard(() => auth.getSession())).session?.access_token ?? null
    },
    async signOut() {
      await auth.signOut().catch(() => {})
    },
  }
}

/** Supabase when both public values are set, otherwise the unconfigured stand-in. */
export function selectIdentity(
  e: { supabaseUrl?: string; supabaseAnonKey?: string },
  create: (url: string, key: string) => Pick<SupabaseClient, "auth"> = createClient,
): IdentityAdapter {
  return e.supabaseUrl && e.supabaseAnonKey ? createSupabaseIdentity(create(e.supabaseUrl, e.supabaseAnonKey)) : unconfiguredIdentity
}

export const identity: IdentityAdapter = selectIdentity(env)
