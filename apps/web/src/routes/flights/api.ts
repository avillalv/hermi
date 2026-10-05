import { useQuery } from "@tanstack/react-query"
import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"

// shortcut: hand-written from apps/api/hermi/modules/flights/schemas.py until `npm run gen:api` is real.
export type Money = { amount_minor: number; currency: string }
export type Route = {
  id: string
  trip_id: string
  label: string | null
  origin_codes: string[]
  destination_codes: string[]
  trip_type: "round_trip" | "one_way"
  depart_from: string
  depart_to: string
  return_from: string | null
  return_to: string | null
  adults: number
  children: number
  cabin?: string
  mode: "cached" | "live"
  version: number
  last_checked_at: string | null
}
export type Fare = {
  id: string
  route_id: string
  source: string
  confidence: string
  origin: string
  destination: string
  depart_date: string
  return_date: string | null
  price: Money
  airlines: string[]
  stops_out: number | null
  stops_back: number | null
  duration_out_min: number | null
  depart_at_local: string | null
  passengers?: number
  source_url: string | null
  airline_search_url?: string | null
  hidden?: boolean
  suspect?: boolean
  observed_at: string
  age_label: string
}
export type RouteSummary = { route_id: string; cheapest: Fare | null; last_checked_at: string | null; fare_count: number; chosen: Fare | null }
export type PriceHistory = { currency: string; points: { day: string; source: string; price: Money }[] }
export type GridCell = { fare_id: string; depart_date: string; return_date: string | null; price: Money; source: string; observed_at: string }
export type FareSort = "price" | "duration" | "stops"
export type RouteIn = {
  origin_codes: string[]
  destination_codes: string[]
  trip_type: "round_trip" | "one_way"
  depart_from: string
  depart_to: string
  return_from: string | null
  return_to: string | null
  adults: number
  mode: "cached"
}

const base = (id: string) => `/v1/trips/${encodeURIComponent(id)}`
const key = (id: string, ...rest: unknown[]) => ["flights", id, ...rest]

function useRead<T>(queryKey: unknown[], path: string, enabled = true, query?: Record<string, string>) {
  return useQuery(
    {
      queryKey,
      enabled,
      retry: 1,
      queryFn: async () => {
        const r = await api.get<T>(path, { query })
        if (r.error !== undefined || r.data === undefined) throw new Error(`flights ${r.response.status}`)
        return r.data
      },
    },
    queryClient,
  )
}

export const useRoutes = (id: string, on: boolean) => useRead<Route[]>(key(id, "routes"), `${base(id)}/routes`, on)
export const useSummary = (id: string, on: boolean) => useRead<RouteSummary[]>(key(id, "summary"), `${base(id)}/flights/summary`, on)
export const useHistory = (id: string, route: string, on = true) => useRead<PriceHistory>(key(id, route, "history"), `${base(id)}/routes/${route}/price-history`, on)
export const useGrid = (id: string, route: string, on: boolean) => useRead<GridCell[]>(key(id, route, "grid"), `${base(id)}/routes/${route}/date-grid`, on)
export const useOptions = (id: string, route: string, sort: FareSort, on: boolean) =>
  useRead<Fare[]>(key(id, route, "options", sort), `${base(id)}/flights/best`, on, { route_id: route, sort, limit: "20" })

/** A 402 carries the server's message and its paywall trigger so the screen can tell an upgrade from a plain limit. */
export type Result = { ok: true } | { ok: false; reason: "limit" | "forbidden" | "invalid" | "unavailable" | "rate" | "conflict" | "failed"; message?: string; trigger?: string }

async function write(id: string, send: () => ReturnType<typeof api.post>): Promise<Result> {
  try {
    const r = await send()
    const s = r.response.status
    if (s === 402) {
      const e = r.error as { detail?: string; paywall?: { trigger?: string } } | undefined
      return { ok: false, reason: "limit", message: e?.detail, trigger: e?.paywall?.trigger }
    }
    if (s === 409) return { ok: false, reason: "conflict" }
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (s === 422) return { ok: false, reason: "invalid" }
    if (s === 503) return { ok: false, reason: "unavailable" }
    if (s === 429) return { ok: false, reason: "rate" }
    if (r.error !== undefined) return { ok: false, reason: "failed" }
    await queryClient.invalidateQueries({ queryKey: key(id) })
    await queryClient.invalidateQueries({ queryKey: ["trip", id] })
    return (r.data as { status?: string } | undefined)?.status === "failed" ? { ok: false, reason: "failed" } : { ok: true }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

export const addRoute = async (id: string, body: RouteIn) => {
  const made = await write(id, () => api.post(`${base(id)}/routes`, body))
  // A new route has no fares until a refresh runs. Its failure is ignored: the daily job fills it in.
  if (made.ok) void refreshRoute(id, undefined)
  return made
}
/** `paid` or `booked_at` also marks the flight booked (the API treats either as a booking). */
export const chooseFare = (id: string, route: string, fare: string, booking?: { paid?: Money; booked_at?: string }) =>
  write(id, () => api.put(`${base(id)}/routes/${route}/choice`, { fare_id: fare, ...booking }))
/** One fare: the route's fare list is cheapest first, so the detail screen finds its fare in the first 100 (no single-fare read exists yet). */
export const useRouteFares = (id: string, route: string, on: boolean) =>
  useRead<{ items: Fare[] }>(key(id, route, "fares"), `${base(id)}/routes/${route}/fares`, on, { limit: "100" })
/** Cached refresh: free, never spends credits (01 section 5.8). */
export const refreshRoute = (id: string, route?: string) => write(id, () => api.post(`${base(id)}/flights/refresh`, route ? { route_ids: [route] } : {}))

export const useEntitlements = (on: boolean) =>
  useQuery(
    {
      queryKey: ["entitlements", "airports"],
      enabled: on,
      queryFn: async () => {
        const r = await api.get<{ tier?: string; limits: { airports_per_side?: number } }>("/v1/me/entitlements")
        if (r.error !== undefined || !r.data) throw new Error("entitlements")
        return r.data
      },
    },
    queryClient,
  ).data

/** airports_per_side from the plan, or 2 (the Free cap) until it loads. */
export const useAirportsPerSide = (on: boolean): number => useEntitlements(on)?.limits.airports_per_side ?? 2

/** "3 h ago", the same wording as the API's age_label. */
export function ageText(iso: string, now = Date.now()): string {
  const sec = Math.max(0, Math.floor((now - Date.parse(iso)) / 1000))
  return sec < 60 ? "just now" : sec < 3600 ? `${Math.floor(sec / 60)} min ago` : sec < 172800 ? `${Math.floor(sec / 3600)} h ago` : `${Math.floor(sec / 86400)} d ago`
}

export type Alert = { id: string; route_id: string; target_price: Money; notify: { push: boolean; email: boolean }; active: boolean; last_notified_at: string | null; last_notified_price: Money | null }
export type AlertIn = { target_price: Money; notify: { push: boolean; email: boolean } }
/** The caller's own alerts on this trip (alerts are personal, 04 section 5.8). */
export const useAlerts = (id: string, on: boolean) => useRead<Alert[]>(key(id, "alerts"), `${base(id)}/price-alerts`, on)
export const createAlert = (id: string, route: string, body: AlertIn) => write(id, () => api.post(`/v1/routes/${encodeURIComponent(route)}/price-alerts`, body))
export const updateAlert = (id: string, alert: string, body: Partial<AlertIn> & { active?: boolean }) => write(id, () => api.patch(`/v1/price-alerts/${encodeURIComponent(alert)}`, body))
export const deleteAlert = (id: string, alert: string) => write(id, () => api.delete(`/v1/price-alerts/${encodeURIComponent(alert)}`))
