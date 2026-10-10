import { useSyncExternalStore } from "react"
import type { Sample } from "../../routes/discover/api"
import { track } from "../../lib/track"

/**
 * The one guest trip (05 6.2), kept on this device only. Nothing here touches the network: a guest holds no server
 * credential, and `POST /me/claim` (04 section 5.1) is the first time the trip leaves the device.
 */
export const GUEST_KEY = "hermi.guest.v2"
const LEGACY_KEY = "hermi.guestTrip" // v1: a read-only copy of a sample (WF-133.3), migrated on first read

export const CATEGORIES = ["sights", "museum", "food", "nature", "nightlife", "shopping", "travel", "other"] as const
export type Category = (typeof CATEGORIES)[number]

export type GuestItem = {
  id: string // local only, the server ignores it
  title: string
  day: string | null
  start_time: string | null
  category: Category
  location_name: string | null
}
export type GuestTrip = {
  name: string
  destinations: string[]
  start_date: string | null
  end_date: string | null
  items: GuestItem[]
}
export type GuestDoc = {
  v: 2
  /** Generated once with the trip and reused by every retry, so the server imports it at most once. */
  claim_id: string
  created_at: string
  /** "Keep separate" was chosen after sign-in: the trip stays on this phone and is not offered again until Save is tapped. */
  kept_separate?: boolean
  trip: GuestTrip
}

const isDoc = (v: unknown): v is GuestDoc => {
  const d = v as GuestDoc | null
  return !!d && d.v === 2 && typeof d.claim_id === "string" && !!d.trip && typeof d.trip.name === "string" && Array.isArray(d.trip.items) && Array.isArray(d.trip.destinations)
}

const category = (c: string): Category => ((CATEGORIES as readonly string[]).includes(c) ? (c as Category) : "other")

function fromSample(s: Sample, createdAt: string): GuestDoc {
  const days = s.presentation.days
  const items: GuestItem[] = days.flatMap((d) =>
    d.items.map((i) => ({
      id: crypto.randomUUID(),
      title: i.title,
      day: d.day,
      start_time: i.start_time ? i.start_time.slice(0, 5) : null,
      category: category(i.category),
      location_name: i.location_name,
    })),
  )
  const dates = days.map((d) => d.day).sort()
  return {
    v: 2,
    claim_id: crypto.randomUUID(),
    created_at: createdAt,
    trip: {
      name: s.presentation.trip.name || s.title,
      destinations: s.presentation.trip.destinations.map((d) => d.name),
      start_date: dates[0] ?? null,
      end_date: dates[dates.length - 1] ?? null,
      items,
    },
  }
}

const storage = (): Storage | null => {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function load(): GuestDoc | null {
  const s = storage()
  if (!s) return null
  try {
    const cur = JSON.parse(s.getItem(GUEST_KEY) ?? "null") as unknown
    if (isDoc(cur)) return cur
    const old = JSON.parse(s.getItem(LEGACY_KEY) ?? "null") as { saved_at?: string; sample?: Sample } | null
    if (old && Array.isArray(old.sample?.presentation?.days)) {
      const doc = fromSample(old.sample as Sample, typeof old.saved_at === "string" ? old.saved_at : new Date().toISOString())
      s.setItem(GUEST_KEY, JSON.stringify(doc))
      s.removeItem(LEGACY_KEY)
      return doc
    }
  } catch {
    /* a damaged value reads as no guest trip */
  }
  return null
}

let doc: GuestDoc | null = load()
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((l) => l())
const persist = (next: GuestDoc | null) => {
  doc = next
  try {
    if (next) storage()?.setItem(GUEST_KEY, JSON.stringify(next))
    else storage()?.removeItem(GUEST_KEY)
  } catch {
    /* storage full or blocked: the in-memory trip still holds for this page */
  }
  emit()
}

// Another tab changed or cleared the trip.
if (typeof window !== "undefined")
  window.addEventListener("storage", (e) => {
    if (e.key === GUEST_KEY || e.key === null) {
      doc = load()
      emit()
    }
  })

/** Re-reads storage. For tests, and for a caller that wrote the key itself. */
export const reloadGuest = () => {
  doc = load()
  emit()
}

export const readGuest = (): GuestDoc | null => doc

export type NewGuestTrip = { name: string; destination?: string; start_date?: string | null; end_date?: string | null }

/** False when a guest trip already exists: guests plan one trip. Emits `guest_trip_created` once. */
export function createGuestTrip(input: NewGuestTrip): boolean {
  if (doc) return false
  const dest = input.destination?.trim()
  persist({
    v: 2,
    claim_id: crypto.randomUUID(),
    created_at: new Date().toISOString(),
    trip: {
      name: input.name.trim() || dest || "My trip",
      destinations: dest ? [dest] : [],
      start_date: input.start_date || null,
      end_date: input.end_date || null,
      items: [],
    },
  })
  track("guest_trip_created")
  return true
}

/** The "Use this plan" copy of a sample (05 6.23). False when a guest trip already exists. */
export function createGuestTripFromSample(sample: Sample): boolean {
  if (doc) return false
  persist(fromSample(sample, new Date().toISOString()))
  track("guest_trip_created")
  return true
}

export function updateGuestTrip(patch: Partial<Omit<GuestTrip, "items">>) {
  if (doc) persist({ ...doc, trip: { ...doc.trip, ...patch } })
}

export function addGuestItem(item: Omit<GuestItem, "id">) {
  if (doc) persist({ ...doc, trip: { ...doc.trip, items: [...doc.trip.items, { ...item, id: crypto.randomUUID() }] } })
}

export function removeGuestItem(id: string) {
  if (doc) persist({ ...doc, trip: { ...doc.trip, items: doc.trip.items.filter((i) => i.id !== id) } })
}

export function setKeptSeparate(kept: boolean) {
  if (doc) persist({ ...doc, kept_separate: kept || undefined })
}

export const clearGuest = () => persist(null)

export function useGuest(): GuestDoc | null {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn)
      return () => void listeners.delete(fn)
    },
    () => doc,
  )
}

/**
 * The trip JSON for `POST /me/claim` (04 5.1 `TripJson`). shortcut: a guest cannot geocode (the lookup is a tenant
 * route), so destinations travel as a line in the trip notes instead of `destinations` rows, which need coordinates.
 * Upgrade: resolve them after the claim, or add a keyless geocode for guests.
 */
export function claimPayload(d: GuestDoc) {
  const t = d.trip
  const dated = !!t.start_date && !!t.end_date && t.end_date >= t.start_date // the server rejects a reversed range
  return {
    name: (t.name.trim() || t.destinations[0]?.trim() || "My trip").slice(0, 120),
    start_date: dated ? t.start_date : null,
    end_date: dated ? t.end_date : null,
    notes: t.destinations.length ? `Destinations: ${t.destinations.join(", ")}` : "",
    destinations: [],
    // The server caps items at 200 and location_name at 200 characters (`TripJson`).
    items: t.items.slice(0, 200).map(({ title, day, start_time, category: c, location_name }) => ({
      title: title.slice(0, 200),
      day,
      start_time,
      category: c,
      location_name: location_name?.slice(0, 200) ?? null,
    })),
  }
}
