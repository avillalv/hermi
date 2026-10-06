import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"
import { markOnboarded } from "../onboarding/trips"

const PENDING = "hermi.claim"
/** A signed-out person who opens a claim link signs in first; the sign-in screens send them back to the link. */
export const pendingClaim = {
  set: (token: string) => sessionStorage.setItem(PENDING, token),
  clear: () => sessionStorage.removeItem(PENDING),
  target: () => {
    const t = sessionStorage.getItem(PENDING)
    return t ? `/claim/${encodeURIComponent(t)}` : null
  },
}

export type ClaimResult = { ok: true } | { ok: false; reason: "expired" | "has_account" | "failed" }

/** POST /me/legacy-claim (04 section 5.1). 410 is a used or expired link, 409 a sign-in that already has its own account. */
export async function redeemClaim(token: string): Promise<ClaimResult> {
  try {
    const r = await api.post("/v1/me/legacy-claim", { token })
    if (r.response.status === 410) return { ok: false, reason: "expired" }
    if (r.response.status === 409) return { ok: false, reason: "has_account" }
    if (r.error !== undefined) return { ok: false, reason: "failed" }
  } catch {
    return { ok: false, reason: "failed" }
  }
  markOnboarded()
  await queryClient.invalidateQueries()
  return { ok: true }
}
