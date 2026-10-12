import { adminRequest, type AdminResult } from "./adminClient"
import { getAssertion, PasskeyCancelled } from "./webauthn"

// shortcut: hand-written shapes for /v1/admin/auth (apps/api/hermi/modules/admin/auth.py). Switch to the generated
// client when `npm run gen:api` emits the admin tag into apps/web/src/lib/api.
export type AdminSession = {
  admin: { user_id: string; email: string; role: string; mfa_enrolled: boolean }
  permissions: Record<string, string>
  two_factor: { enrolled: boolean; fresh: boolean }
  signed_in: boolean
  expires_at: string | null
  fresh_until: string | null
  factors: { passkeys: number; totp: boolean; recovery_codes_left: number }
}

export const SESSION_KEY = ["admin", "session"] as const
export const fetchSession = (): Promise<AdminResult<AdminSession>> => adminRequest<AdminSession>("GET", "/v1/admin/auth/session")

export type Proof =
  | { method: "totp" | "recovery"; code: string }
  | { method: "webauthn"; challenge_id: string; assertion: Awaited<ReturnType<typeof getAssertion>> }

/** The browser half of a passkey check: server challenge in, signed assertion out. `null` when the person closed the prompt. */
export async function passkeyProof(purpose: "signin" | "stepup"): Promise<AdminResult<Proof> | null> {
  const opts = await adminRequest<{ challenge_id: string; public_key: Record<string, unknown> }>("POST", "/v1/admin/auth/webauthn/options", { purpose })
  if (!opts.ok) return opts
  try {
    const assertion = await getAssertion(opts.data.public_key)
    return { ok: true, status: 200, data: { method: "webauthn", challenge_id: opts.data.challenge_id, assertion } }
  } catch (e) {
    if (e instanceof PasskeyCancelled) return null
    throw e
  }
}
