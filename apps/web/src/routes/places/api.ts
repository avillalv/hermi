import { useQuery } from "@tanstack/react-query"
import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"
import type { Category } from "../itinerary/api"

// shortcut: hand-written from apps/api/hermi/modules/places/schemas.py until `npm run gen:api` is real.
export type Place = {
  provider: "geoapify"
  id: string
  name: string
  category: Category
  address: string | null
  lat: number
  lon: number
  website: string | null
  opening_hours: string | null
  has_details: boolean
}
export type Wiki = { title: string; extract: string; url: string | null; image_url: string | null; attribution: string }
export type PlaceDetails = Place & { wiki: Wiki | null; attribution: string }
export type SearchResult = { places: Place[]; cached: boolean; sorted_by: "relevance" | "distance"; attribution: string }
export type SavedPlace = {
  id: string
  note: string | null
  created_at: string
  place: { provider: string; id: string; name: string; category: Category; address: string | null; lat: number | null; lon: number | null; website: string | null; opening_hours?: string | null }
}

/** A place the sheet can show and add: a search result, or a saved idea (a manual one can lack coordinates). */
export type Candidate = { id: string; provider: string; name: string; category: Category; address: string | null; lat: number | null; lon: number | null; website: string | null; opening_hours: string | null; savedId?: string }
export const fromPlace = (p: Place): Candidate => ({ ...p })
export const fromSaved = (s: SavedPlace): Candidate => ({ ...s.place, opening_hours: s.place.opening_hours ?? null, savedId: s.id })

export type SearchOutcome = { ok: true; data: SearchResult } | { ok: false; reason: "rate_limited" | "quota" | "unavailable" | "failed" }

/** GET /places/search. The 429s are told apart by code: `rate_limited` (30 a minute) and `quota_exceeded` (the daily cap). */
export async function searchPlaces(p: { tripId: string; destinationId: string; q?: string; category?: string }): Promise<SearchOutcome> {
  try {
    const r = await api.get<SearchResult>("/v1/places/search", { query: { q: p.q || undefined, category: p.category, destination_id: p.destinationId, trip_id: p.tripId } })
    if (r.data) return { ok: true, data: r.data }
    const code = (r.error as { code?: string } | undefined)?.code
    if (r.response.status === 429) return { ok: false, reason: code === "quota_exceeded" ? "quota" : "rate_limited" }
    return { ok: false, reason: r.response.status === 503 ? "unavailable" : "failed" }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

export const placeDetailsKey = (id: string) => ["places", "details", id]
/** Details and the Wikipedia summary. Optional: the sheet already has the basics, so an error just leaves them. */
export const usePlaceDetails = (id: string | null) =>
  useQuery(
    {
      queryKey: placeDetailsKey(id ?? ""),
      enabled: !!id && id.startsWith("geoapify:"),
      retry: 0,
      staleTime: 5 * 60_000,
      queryFn: async () => {
        const r = await api.get<PlaceDetails>(`/v1/places/${encodeURIComponent(id ?? "")}`)
        if (r.error !== undefined || !r.data) throw new Error(`place ${r.response.status}`)
        return r.data
      },
    },
    queryClient,
  )

const savedKey = (tripId: string) => ["places", "saved", tripId]
export const useSavedPlaces = (tripId: string) =>
  useQuery(
    {
      queryKey: savedKey(tripId),
      retry: 1,
      queryFn: async () => {
        const r = await api.get<{ items: SavedPlace[] }>(`/v1/trips/${encodeURIComponent(tripId)}/saved-places`, { query: { limit: 100 } })
        if (r.error !== undefined || !r.data) throw new Error(`saved ${r.response.status}`)
        return r.data.items
      },
    },
    queryClient,
  )

export async function savePlace(tripId: string, placeId: string): Promise<boolean> {
  try {
    const r = await api.post(`/v1/trips/${encodeURIComponent(tripId)}/saved-places`, { place_id: placeId })
    if (r.error !== undefined) return false
    await queryClient.invalidateQueries({ queryKey: savedKey(tripId) })
    return true
  } catch {
    return false
  }
}

export async function removeSaved(tripId: string, savedId: string): Promise<boolean> {
  try {
    const r = await api.delete(`/v1/trips/${encodeURIComponent(tripId)}/saved-places/${encodeURIComponent(savedId)}`)
    if (r.error !== undefined) return false
    await queryClient.invalidateQueries({ queryKey: savedKey(tripId) })
    return true
  } catch {
    return false
  }
}
