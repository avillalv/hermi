import { queryClient } from "../../lib/queryClient"
import { api } from "../../routes/auth/api"
import { TRIPS_KEY } from "../../routes/onboarding/trips"
import { claimPayload, type GuestDoc } from "./store"

export type ClaimOutcome =
  | { kind: "ok"; archived: boolean; tripId: string | null }
  | { kind: "choose"; trips: number; people: number }
  | { kind: "failed" }

/**
 * POST /me/claim (04 section 5.1). `claim_id` was generated with the trip and is reused by every retry, so a double submit
 * or a retry after a lost response returns the first result and imports nothing twice. A 409 `state_conflict` carries the
 * counts for the Merge or Keep separate choice; `merge` answers it. The local trip is the caller's to clear on "ok".
 */
export async function claimGuestTrip(doc: GuestDoc, merge?: boolean): Promise<ClaimOutcome> {
  try {
    const r = await api.post<{ trip_id: string | null; archived?: boolean }>("/v1/me/claim", {
      trip: claimPayload(doc),
      claim_id: doc.claim_id,
      ...(merge === undefined ? {} : { merge }),
    })
    if (r.response.status === 409) {
      const e = r.error as { code?: string; counts?: { trips?: number; people?: number } } | undefined
      if (e?.code === "state_conflict") return { kind: "choose", trips: e.counts?.trips ?? 0, people: e.counts?.people ?? 0 }
      return { kind: "failed" }
    }
    if (r.error !== undefined || !r.data) return { kind: "failed" }
    await queryClient.invalidateQueries({ queryKey: TRIPS_KEY })
    return { kind: "ok", archived: r.data.archived === true, tripId: r.data.trip_id }
  } catch {
    return { kind: "failed" }
  }
}
