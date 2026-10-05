import { useQuery } from "@tanstack/react-query"
import { env } from "../../lib/env"
import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"

// shortcut: hand-written shapes from 04 section 5.4. `npm run gen:api` is still a stub script (no OpenAPI client yet); switch to the generated types when it lands.
export type TripSummary = {
  id: string
  version?: number
  name: string
  status: "planning" | "booked" | "done" | "archived"
  start_date: string | null
  end_date: string | null
  destinations_label: string
  member_count: number
  my_role: "owner" | "editor" | "viewer"
}
export type DestinationIn = { name: string; region?: string | null; country?: string | null; country_code?: string | null; lat: number; lon: number; timezone?: string | null }
export type TripCreate = { name: string; start_date?: string; end_date?: string; destinations?: DestinationIn[] }

export const TRIPS_KEY = ["trips"]

export function useTrips(enabled: boolean) {
  return useQuery(
    {
      queryKey: TRIPS_KEY,
      enabled,
      retry: 1, // one quiet retry, then the error state with Try again
      queryFn: async () => {
        const r = await api.get<{ items: TripSummary[] }>("/v1/trips")
        if (r.error !== undefined || !r.data) throw new Error(`trips ${r.response.status}`)
        return r.data.items
      },
    },
    queryClient,
  )
}

export type CreateResult = { ok: true } | { ok: false; reason: "limit" | "failed" }

/** POST /trips. A 402 is the Free active trip limit (04 section 5.4). Refreshes the list on success. */
export async function createTrip(body: TripCreate): Promise<CreateResult> {
  try {
    const r = await api.post("/v1/trips", body)
    if (r.response.status === 402) return { ok: false, reason: "limit" }
    if (r.error !== undefined) return { ok: false, reason: "failed" }
  } catch {
    return { ok: false, reason: "failed" }
  }
  await queryClient.invalidateQueries({ queryKey: TRIPS_KEY })
  return { ok: true }
}

export const ONBOARDED_KEY = "hermi.onboarded" // authStore.signOut clears it
export const markOnboarded = () => sessionStorage.setItem(ONBOARDED_KEY, "1")
export const isOnboarded = () => sessionStorage.getItem(ONBOARDED_KEY) === "1"

/**
 * Does this sign-in already have a users row? GET /me answers 200, or 401 when there is none (04 section 4). A raw
 * fetch, because the API client treats a 401 as an expired session and signs the person out.
 */
export function useMe(token: string | null, enabled: boolean) {
  return useQuery(
    {
      queryKey: ["me"],
      enabled: enabled && !!token,
      retry: 1,
      queryFn: async () => {
        const r = await fetch(`${env.apiBaseUrl}/v1/me`, { headers: { Authorization: `Bearer ${token}` }, credentials: "omit" })
        if (r.ok) {
          markOnboarded()
          return true
        }
        if (r.status === 401) return false
        throw new Error(`me ${r.status}`)
      },
    },
    queryClient,
  )
}
