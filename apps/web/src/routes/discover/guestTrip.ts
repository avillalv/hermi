import type { Sample } from "./api"

const KEY = "hermi.guestTrip"

/**
 * The one guest trip, kept on this device only (05 6.2). shortcut: a localStorage copy of the sample as read, with no
 * editing, sync or claim yet. Upgrade when full guest mode lands: move it into the local trip store that Create trip uses.
 */
export type GuestTrip = { saved_at: string; sample: Sample }

export function readGuestTrip(): GuestTrip | null {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "null") as GuestTrip | null
    return Array.isArray(v?.sample?.presentation?.days) ? v : null
  } catch {
    return null
  }
}

/** False when a guest trip already exists: guests plan one trip. */
export function saveGuestTrip(sample: Sample): boolean {
  if (readGuestTrip()) return false
  localStorage.setItem(KEY, JSON.stringify({ saved_at: new Date().toISOString(), sample } satisfies GuestTrip))
  return true
}
