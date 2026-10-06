import { useQuery } from "@tanstack/react-query"
import { ApiError } from "../../lib/api/client"
import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"
import { TRIPS_KEY } from "../onboarding/trips"
import type { Trip } from "../trips/api"

// shortcut: hand-written from 04 section 5.28 and the Presentation model until `npm run gen:api` is real.
export type SampleSummary = { slug: string; title: string; destination_name: string; days: number; summary: string; tags: string[]; suits: string }
export type SampleItem = {
  id: string
  start_time: string | null
  title: string
  category: string
  location_name: string | null
  estimated_cost_minor: number | null
  cost_currency: string | null
  check_url: string | null
  checked_at: string | null
}
export type SampleDay = { day: string; title: string; destination_name: string | null; items: SampleItem[] }
export type SampleStay = { id: string; title: string; price_total_minor: number | null; currency: string | null }
export type Sample = {
  slug: string
  title: string
  summary: string
  updated_at: string
  presentation: { trip: { name: string; destinations: { name: string }[] }; days: SampleDay[]; stays: SampleStay[] }
}

const get = async <T,>(path: string, query?: Record<string, string | undefined>) => {
  const r = await api.get<T>(path, { query })
  if (r.error !== undefined || !r.data) throw new ApiError(r)
  return r.data
}

/** GET /public/sample-trips: no sign-in, a fixed list (05 6.23). `tag` is a chip filter. */
export const useSamples = (tag?: string) =>
  useQuery({ queryKey: ["samples", tag ?? ""], queryFn: async () => (await get<{ items: SampleSummary[] }>("/v1/public/sample-trips", { tag })).items }, queryClient)

export const useSample = (slug: string | undefined) =>
  useQuery({ queryKey: ["sample", slug], enabled: !!slug, queryFn: () => get<Sample>(`/v1/public/sample-trips/${encodeURIComponent(slug ?? "")}`) }, queryClient)

export type CopyResult = { ok: true; trip: Trip } | { ok: false; reason: "limit" | "failed" }

/** POST /public/sample-trips/{slug}/copy: days, items and saved places, never flights or prices. 402 is the Free active-trip limit. */
export async function copySample(slug: string): Promise<CopyResult> {
  try {
    const r = await api.post<Trip>(`/v1/public/sample-trips/${encodeURIComponent(slug)}/copy`, {}, { headers: { "Idempotency-Key": crypto.randomUUID() } })
    if (r.response.status === 402) return { ok: false, reason: "limit" }
    if (r.error !== undefined || !r.data) return { ok: false, reason: "failed" }
    await queryClient.invalidateQueries({ queryKey: TRIPS_KEY })
    return { ok: true, trip: r.data }
  } catch {
    return { ok: false, reason: "failed" }
  }
}
