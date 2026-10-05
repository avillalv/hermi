import { useSyncExternalStore } from "react"
import { api } from "../routes/auth/api"
import { queryClient } from "./queryClient"

/** 05 4.21 sync indicator state, per trip. Conditional polling (If-None-Match, 304 counts as success) every POLL_MS. */
export type Conflict = { keepMine: () => void | Promise<void>; useTheirs: () => void | Promise<void> }
export type SyncState = { lastOk: number | null; failures: number; syncing: boolean; queued: number; etag: string | null; conflict: Conflict | null }

export const POLL_MS = 20_000 // inside the 15 to 30 s of WF-125
export const FAILING_AFTER = 3

const empty: SyncState = { lastOk: null, failures: 0, syncing: false, queued: 0, etag: null, conflict: null }
const states = new Map<string, SyncState>()
const listeners = new Set<() => void>()
const inflight = new Set<string>() // the real guard; `syncing` is display only

const read = (id: string) => states.get(id) ?? empty
function patch(id: string, p: Partial<SyncState>) {
  states.set(id, { ...read(id), ...p })
  listeners.forEach((l) => l())
}
const subscribe = (cb: () => void) => (listeners.add(cb), () => void listeners.delete(cb))

export const useSyncState = (id: string) => useSyncExternalStore(subscribe, () => read(id))

/** An accepted queued edit counts as a successful sync (05 4.21). */
export const markAccepted = (id: string) => patch(id, { lastOk: Date.now(), failures: 0 })

/** The offline queue seam. shortcut: nothing writes it until WF-089 lands, so it reads 0; that ticket calls this on every queue change. */
export const setQueued = (id: string, n: number) => patch(id, { queued: n })

/** A writer that got a 409 hands over its two ways out; the indicator shows the "Keep mine" and "Use theirs" sheet. */
export const reportConflict = (id: string, conflict: Conflict) => patch(id, { conflict })
export const clearConflict = (id: string) => patch(id, { conflict: null })

/** One conditional GET of the trip. A failed poll adds to `failures` and never touches `lastOk`. `visible` shows the Syncing state (first sync and taps). */
export async function syncNow(id: string, visible = false): Promise<void> {
  if (inflight.has(id) || (typeof navigator !== "undefined" && !navigator.onLine)) return
  inflight.add(id)
  if (visible || read(id).lastOk === null) patch(id, { syncing: true })
  const etag = read(id).etag
  try {
    // shortcut: the API sets an ETag on this GET but ignores If-None-Match (no 304 yet), so every poll is a full 200. The API ticket that adds 304 makes it cheap.
    const r = await api.get(`/v1/trips/${encodeURIComponent(id)}`, { headers: etag ? { "If-None-Match": etag } : undefined, signal: AbortSignal.timeout(10_000) })
    const s = r.response.status
    if (s !== 304 && !r.response.ok) throw new Error(`sync ${s}`)
    const next = r.response.headers.get("ETag") ?? etag
    // Someone else saved: refresh what is on screen. The first poll only learns the tag.
    if (etag && next && next !== etag) void queryClient.invalidateQueries({ queryKey: ["trip", id] })
    patch(id, { lastOk: Date.now(), failures: 0, syncing: false, etag: next })
  } catch {
    patch(id, { failures: read(id).failures + 1, syncing: false })
  } finally {
    inflight.delete(id)
  }
}

/** Poll now and then every POLL_MS. Returns the stop function. */
export function startPolling(id: string): () => void {
  void syncNow(id)
  const h = setInterval(() => void syncNow(id), POLL_MS)
  return () => clearInterval(h)
}

/** Tests only. */
export const _resetSync = () => (states.clear(), inflight.clear(), listeners.forEach((l) => l()))

// shortcut: a dev-server-only hook so Playwright can stand in for the offline queue until WF-089 lands. Remove when WF-089 calls setQueued from the real queue.
if (import.meta.env.DEV && typeof window !== "undefined") (window as unknown as { __hermiSetQueued?: typeof setQueued }).__hermiSetQueued = setQueued
