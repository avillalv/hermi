import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"
import type { ActionResult, Person } from "./api"

export type PersonIn = Pick<Person, "name" | "color" | "home_airports">

const refresh = (id: string) => queryClient.invalidateQueries({ queryKey: ["trip", id] })

/** One write to the people API. 402 is the traveler cap (04 section 5.7), 403 a role refusal. Refreshes the trip on success. */
async function write<T>(id: string, send: () => Promise<{ data?: T; error?: unknown; response: Response }>): Promise<ActionResult<T>> {
  try {
    const r = await send()
    const s = r.response.status
    if (s === 402) return { ok: false, reason: "limit" }
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (r.error !== undefined) return { ok: false, reason: "failed" }
    await refresh(id)
    return { ok: true, data: r.data as T }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

const trip = (id: string, tail: string) => `/v1/trips/${encodeURIComponent(id)}${tail}`

/** Creates the person, then replaces the trip's travelers with `current` plus them. */
export async function addTraveler(id: string, current: string[], body: PersonIn): Promise<ActionResult> {
  // shortcut: when the cap refuses the second call, the new person stays in the caller's own people unused. A later add can reuse them.
  const made = await write<Person>(id, () => api.post<Person>("/v1/people", body))
  if (!made.ok) return made
  return write(id, () => api.put(trip(id, "/travelers"), { person_ids: [...current, made.data.id] }))
}
export const editTraveler = (id: string, personId: string, body: PersonIn) => write(id, () => api.put(`/v1/people/${encodeURIComponent(personId)}`, body))
/** Takes the traveler off this trip. The person, their other trips and their history stay (04 section 5.7). */
export const setTravelers = (id: string, personIds: string[]) => write(id, () => api.put(trip(id, "/travelers"), { person_ids: personIds }))
export const linkMe = (id: string, personId: string) => write(id, () => api.put(trip(id, "/members/me/traveler"), { person_id: personId }))
export const unlinkMe = (id: string) => write(id, () => api.delete(trip(id, "/members/me/traveler")))
