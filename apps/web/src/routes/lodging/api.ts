import { useQuery } from "@tanstack/react-query"
import { queryClient } from "../../lib/queryClient"
import { setAnalyticsUser } from "../../lib/analytics"
import { ApiError } from "../../lib/api/client"
import { api } from "../auth/api"

// shortcut: hand-written from apps/api/hermi/modules/lodging/schemas.py until `npm run gen:api` is real.
export type Money = { amount_minor: number; currency: string }
export type Status = "candidate" | "shortlisted" | "booked" | "rejected"
export type Sort = "votes" | "price" | "created" | "rating"
export const SORTS: Sort[] = ["votes", "price", "created", "rating"]
export type Vote = { user_id: string | null; person_id: string | null }
export type Stay = {
  id: string
  trip_id: string
  title: string
  url: string | null
  site: string | null
  check_in: string | null
  check_out: string | null
  nights: number | null
  price_total: Money | null
  price_per_night: Money | null
  bedrooms: number | null
  rating: number | null
  notes: string
  status: Status
  added_via: string
  version: number
  votes: Vote[]
  vote_summary: { hearts: number }
}
export type StayPage = { items: Stay[]; has_more: boolean; sorted_by: Sort }
export type CompareRow = { key: string; label: string; values: (string | number | null)[] }
export type Compare = { columns: string[]; rows: CompareRow[]; home_currency: string }
export type StayIn = {
  title: string
  url?: string
  added_via: "paste" | "bookmarklet" | "manual"
  price_per_night?: Money
  notes?: string
  check_in?: string | null
  check_out?: string | null
  guests?: number | null
}
export type LinkParse = { site: string | null; check_in: string | null; check_out: string | null; guests: number | null; note: string }

const trip = (id: string) => `/v1/trips/${encodeURIComponent(id)}`
export const stayKey = (id: string, ...rest: string[]) => ["lodging", id, ...rest]
const POLL_MS = 15_000 // 10 section 1.6 flow 5: a heart shows for the others within 30 s, so poll at half that

export const useMe = (on: boolean) =>
  useQuery(
    {
      queryKey: ["me"],
      enabled: on,
      staleTime: 5 * 60_000,
      retry: 1,
      queryFn: async () => {
        const r = await api.get<{ id: string }>("/v1/me")
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        setAnalyticsUser(r.data.id)
        return r.data
      },
    },
    queryClient,
  )

export const useStays = (id: string, sort: Sort, on: boolean) =>
  useQuery(
    {
      queryKey: stayKey(id, "list", sort),
      enabled: on,
      retry: 1,
      refetchInterval: POLL_MS,
      queryFn: async () => {
        const r = await api.get<StayPage>(`${trip(id)}/lodging`, { query: { sort, limit: 200 } })
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )

export type Outcome<T = unknown> = { ok: true; data: T } | { ok: false; reason: "conflict" | "forbidden" | "invalid" | "limit" | "failed"; detail?: string }

async function send<T>(call: () => Promise<{ data?: T; error?: unknown; response: Response }>, id: string, refresh = true): Promise<Outcome<T>> {
  try {
    const r = await call()
    const s = r.response.status
    const detail = (r.error as { detail?: string } | undefined)?.detail
    if (s === 409 || s === 412) return { ok: false, reason: "conflict", detail }
    if (s === 402) return { ok: false, reason: "limit", detail }
    if (s === 403) return { ok: false, reason: "forbidden", detail }
    if (s === 422) return { ok: false, reason: "invalid", detail }
    if (r.error !== undefined) return { ok: false, reason: "failed", detail }
    if (refresh) await queryClient.invalidateQueries({ queryKey: stayKey(id) })
    return { ok: true, data: r.data as T }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

/** PUT /lodging/{id}/votes/me. The answer is the stay with its hearts, so the cached lists take it in place and the next poll re-sorts. */
export async function setHeart(tripId: string, stayId: string, voted: boolean) {
  const r = await send<Stay>(() => api.put<Stay>(`/v1/lodging/${encodeURIComponent(stayId)}/votes/me`, { voted }), tripId, false)
  if (r.ok) queryClient.setQueriesData<StayPage>({ queryKey: stayKey(tripId, "list") }, (p) => p && { ...p, items: p.items.map((s) => (s.id === stayId ? r.data : s)) })
  return r
}
export const setStatus = (tripId: string, stay: Pick<Stay, "id" | "version">, status: Status) =>
  send<Stay>(() => api.patch<Stay>(`/v1/lodging/${encodeURIComponent(stay.id)}`, { status, version: stay.version }), tripId)
export const createStay = (tripId: string, body: StayIn) => send<Stay>(() => api.post<Stay>(`${trip(tripId)}/lodging`, body), tripId)
/** POST /lodging/parse-link reads the URL text only; the server makes no request to the host. */
export const parseLink = (url: string) => send<LinkParse>(() => api.post<LinkParse>("/v1/lodging/parse-link", { url }), "", false)
export const fetchCompare = (tripId: string, ids: string[]) => send<Compare>(() => api.get<Compare>(`${trip(tripId)}/lodging/compare`, { query: { ids: ids.join(",") } }), tripId, false)
