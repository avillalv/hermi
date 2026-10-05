import { useQuery } from "@tanstack/react-query"
import { queryClient } from "../../lib/queryClient"
import { ApiError } from "../../lib/api/client"
import { api } from "../auth/api"
import { TRIPS_KEY, type DestinationIn, type TripSummary } from "../onboarding/trips"

// shortcut: hand-written from the Trip read model in apps/api/hermi/modules/trips/schemas.py until `npm run gen:api` is real.
export type TripDestination = {
  id: string
  position: number
  name: string
  region: string | null
  country: string | null
  timezone: string | null
}
/** 04 section 5.7: a traveler is a name, a color and home airports. No birthdate, no email. */
export type Person = { id: string; name: string; color: string; home_airports: string[]; linked_user_id: string | null; is_me: boolean }
export type Trip = Pick<TripSummary, "id" | "version" | "name" | "status" | "start_date" | "end_date" | "my_role"> & {
  home_currency: string
  editors_can_invite?: boolean
  limited?: boolean
  travelers: Person[]
  destinations: (TripDestination & { lat?: number; lon?: number; country_code?: string | null })[]
}

export class NotFound extends ApiError {}

/** GET /trips/{id}. A 404 (deleted, or not yours) is a `NotFound`, which the screen shows without a retry. */
export function useTrip(id: string | undefined, enabled: boolean) {
  return useQuery(
    {
      queryKey: ["trip", id],
      enabled: enabled && !!id,
      retry: (n, e) => !(e instanceof NotFound) && n < 1,
      queryFn: async () => {
        const r = await api.get<Trip>(`/v1/trips/${encodeURIComponent(id ?? "")}`)
        if (r.response.status === 404) throw new NotFound(r)
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )
}

export type ActionResult<T = unknown> = { ok: true; data: T } | { ok: false; reason: "limit" | "conflict" | "forbidden" | "failed" }

/** One write to the trips API. 402 is the Free active trip limit, 409 and 412 a stale version, 403 a role refusal (04 section 5.4). Refreshes the lists on success. */
async function write<T>(id: string, send: () => Promise<{ data?: T; error?: unknown; response: Response }>): Promise<ActionResult<T>> {
  try {
    const r = await send()
    const s = r.response.status
    if (s === 402) return { ok: false, reason: "limit" }
    if (s === 409 || s === 412) return { ok: false, reason: "conflict" }
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (r.error !== undefined) return { ok: false, reason: "failed" }
    await Promise.all([queryClient.invalidateQueries({ queryKey: TRIPS_KEY }), queryClient.invalidateQueries({ queryKey: ["trip", id] })])
    return { ok: true, data: r.data as T }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

const url = (id: string, tail = "") => `/v1/trips/${encodeURIComponent(id)}${tail}`
export type TripPatch = { name?: string; start_date?: string | null; end_date?: string | null; home_currency?: string; status?: Trip["status"]; destinations?: (DestinationIn & { id?: string })[] }

export const patchTrip = (id: string, version: number | undefined, body: TripPatch) => write<Trip>(id, () => api.patch<Trip>(url(id), { ...body, version }))
export const duplicateTrip = (id: string) => write<Trip>(id, () => api.post<Trip>(url(id, "/duplicate"), {}))
export const trashTrip = (id: string) => write<null>(id, () => api.delete<null>(url(id)))
export const restoreTrip = (id: string) => write<Trip>(id, () => api.post<Trip>(url(id, "/restore")))
