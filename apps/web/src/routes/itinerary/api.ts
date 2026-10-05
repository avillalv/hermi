import { useQuery } from "@tanstack/react-query"
import { env } from "../../lib/env"
import { queryClient } from "../../lib/queryClient"
import { ApiError } from "../../lib/api/client"
import { api } from "../auth/api"
import { authStore } from "../auth/authStore"

// shortcut: hand-written from apps/api/hermi/modules/itinerary/schemas.py until `npm run gen:api` is real.
export type Category = "sights" | "museum" | "food" | "nature" | "nightlife" | "shopping" | "travel" | "other"
export const CATEGORIES: Category[] = ["sights", "museum", "food", "nature", "nightlife", "shopping", "travel", "other"]
export type Item = {
  id: string
  trip_id: string
  title: string
  day: string | null
  start_time: string | null
  end_time: string | null
  category: Category
  status: "idea" | "planned" | "booked"
  notes: string
  address: string | null
  lat: number | null
  lon: number | null
  sort_order: number
  version: number
  added_by: { id: string; display_name: string | null } | null
}
export type Day = { day: string; timezone: string | null; title: string; notes: string; in_trip: boolean; item_count: number; version: number; destination_name: string | null }
export type ItemIn = {
  title: string
  category: Category
  day?: string | null
  start_time?: string | null
  location_name?: string
  address?: string
  lat?: number
  lon?: number
  url?: string
  /** A place from search: `id` is the Geoapify id without the "geoapify:" prefix. */
  place?: { provider: "geoapify"; id: string }
}

const base = (id: string) => `/v1/trips/${encodeURIComponent(id)}`
export const planKey = (id: string, ...rest: string[]) => ["itinerary", id, ...rest]
const POLL_MS = 30_000 // 05 6.12: shared trips poll every 15 to 30 s

export const useDays = (id: string, on: boolean) =>
  useQuery(
    {
      queryKey: planKey(id, "days"),
      enabled: on,
      retry: 1,
      refetchInterval: POLL_MS,
      queryFn: async () => {
        const r = await api.get<Day[]>(`${base(id)}/days`)
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )

const PAGE = 200
const MAX_PAGES = 10 // shortcut: a trip with more than 2000 items shows the first 2000. Upgrade: load per day.

export const useItems = (id: string, on: boolean) =>
  useQuery(
    {
      queryKey: planKey(id, "items"),
      enabled: on,
      retry: 1,
      refetchInterval: POLL_MS,
      queryFn: async () => {
        const all: Item[] = []
        let cursor: string | undefined
        for (let n = 0; n < MAX_PAGES; n++) {
          const r = await api.get<{ items: Item[]; next_cursor: string | null; has_more: boolean }>(`${base(id)}/items`, { query: { limit: PAGE, cursor } })
          if (r.error !== undefined || !r.data) throw new ApiError(r)
          all.push(...r.data.items)
          if (!r.data.has_more || !r.data.next_cursor) break
          cursor = r.data.next_cursor
        }
        return all
      },
    },
    queryClient,
  )

/** 409 carries the latest row in `current` (04 section 5.10). */
export type Write<T = unknown> = { ok: true; data: T } | { ok: false; reason: "conflict"; current: Item | null } | { ok: false; reason: "forbidden" | "invalid" | "failed" }

async function write<T>(id: string, send: () => Promise<{ data?: T; error?: unknown; response: Response }>): Promise<Write<T>> {
  try {
    const r = await send()
    const s = r.response.status
    if (s === 409 || s === 412) {
      await queryClient.invalidateQueries({ queryKey: planKey(id) })
      const cur = (r.error as { current?: Item } | undefined)?.current
      return { ok: false, reason: "conflict", current: cur && !Array.isArray(cur) ? cur : null }
    }
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (s === 422) return { ok: false, reason: "invalid" }
    if (r.error !== undefined) return { ok: false, reason: "failed" }
    await queryClient.invalidateQueries({ queryKey: planKey(id) })
    return { ok: true, data: r.data as T }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

export const createItem = (id: string, body: ItemIn) => write<Item>(id, () => api.post(`${base(id)}/items`, body))

/** POST /items/{id}/move: `before_id` null puts it last on the day; `day` null moves it to Ideas. The item version guards a stale move. */
export const moveItem = (tripId: string, item: Pick<Item, "id" | "version">, to: { day: string | null; before_id: string | null }) =>
  write<Item[]>(tripId, () => api.post(`/v1/items/${encodeURIComponent(item.id)}/move`, { ...to, version: item.version }))

/** The ICS file needs the bearer token, so it is fetched, then saved from a blob link. Returns false on any failure. */
export async function downloadIcs(tripId: string): Promise<boolean> {
  try {
    const res = await fetch(`${env.apiBaseUrl.replace(/\/+$/, "")}${base(tripId)}/itinerary.ics`, {
      headers: { Authorization: `Bearer ${authStore.get().token ?? ""}` },
      credentials: "omit",
    })
    if (!res.ok) return false
    const name = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? "trip.ics"
    const url = URL.createObjectURL(await res.blob())
    const a = document.createElement("a")
    a.href = url
    a.download = name
    document.body.append(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 10_000) // some browsers read the blob after click() returns
    return true
  } catch {
    return false
  }
}

/** PATCH /items/{id}: a day or time change. The item version in the body guards a stale edit; 409 carries the latest row. */
export const updateItem = (tripId: string, item: Pick<Item, "id" | "version">, body: { day: string | null; start_time: string | null; end_time?: string | null }) =>
  write<Item>(tripId, () => api.patch(`/v1/items/${encodeURIComponent(item.id)}`, { ...body, version: item.version }))
