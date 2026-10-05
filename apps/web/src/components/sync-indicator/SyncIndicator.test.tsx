import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

const get = vi.fn()
vi.mock("../../routes/auth/api", () => ({ api: { get: (...a: unknown[]) => get(...a) } }))
const track = vi.fn()
vi.mock("../../lib/track", () => ({ track: (...a: unknown[]) => track(...a) }))

import { _resetSync, markAccepted, reportConflict, setQueued, syncNow } from "../../lib/sync"
import { SyncIndicator } from "./SyncIndicator"

const ok = (status = 200, etag = '"1"') => ({ data: {}, response: { status, ok: status < 300, headers: new Headers({ ETag: etag }) } })
const online = (v: boolean) => {
  Object.defineProperty(navigator, "onLine", { value: v, configurable: true })
  act(() => void window.dispatchEvent(new Event(v ? "online" : "offline")))
}
const flush = () => act(async () => void (await vi.advanceTimersByTimeAsync(0)))
const tick = (ms: number) => act(async () => void (await vi.advanceTimersByTimeAsync(ms)))

beforeEach(() => {
  vi.useFakeTimers()
  _resetSync()
  get.mockReset()
  track.mockReset()
  online(true)
})
afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

test("after a successful poll it reads Synced 0 s ago and counts up every 5 seconds", async () => {
  get.mockResolvedValue(ok())
  render(<SyncIndicator tripId="t1" />)
  await flush()
  expect(screen.getByRole("button", { name: /Synced 0 s ago/ })).toBeVisible()
  await tick(5000)
  expect(screen.getByRole("button", { name: /Synced 5 s ago/ })).toBeVisible()
  get.mockReturnValue(new Promise(() => {})) // later polls hang, so the age keeps growing
  await tick(60_000)
  expect(screen.getByRole("button", { name: /Synced 1 min ago/ })).toBeVisible()
})

test("a 304 counts as success and the poll sends If-None-Match", async () => {
  get.mockResolvedValueOnce(ok(200, '"4"')).mockResolvedValue(ok(304, '"4"'))
  render(<SyncIndicator tripId="t1" />)
  await flush()
  await tick(20_000)
  expect(get).toHaveBeenCalledTimes(2)
  expect(get.mock.calls[1][1]).toMatchObject({ headers: { "If-None-Match": '"4"' } })
  expect(screen.getByRole("button", { name: /Synced 0 s ago/ })).toBeVisible()
})

test("the first sync reads Syncing", async () => {
  get.mockReturnValue(new Promise(() => {}))
  render(<SyncIndicator tripId="t1" />)
  await flush()
  expect(screen.getByRole("button", { name: /Syncing/ })).toBeVisible()
})

test("offline reads Offline, N edits waiting at once, and 1 edit in the singular", async () => {
  get.mockResolvedValue(ok())
  render(<SyncIndicator tripId="t1" />)
  await flush()
  setQueued("t1", 3)
  online(false)
  expect(screen.getByRole("button", { name: /Offline, 3 edits waiting/ })).toBeVisible()
  act(() => setQueued("t1", 1))
  expect(screen.getByRole("button", { name: /Offline, 1 edit waiting/ })).toBeVisible()
  online(true)
})

test("three failed polls read Could not sync, retrying, and a failure never resets the timer", async () => {
  get.mockResolvedValueOnce(ok())
  render(<SyncIndicator tripId="t1" />)
  await flush()
  get.mockRejectedValue(new TypeError("net"))
  await tick(20_000)
  expect(screen.getByRole("button", { name: /Synced 20 s ago/ })).toBeVisible()
  await tick(20_000)
  expect(screen.getByRole("button", { name: /Synced 40 s ago/ })).toBeVisible()
  await tick(20_000)
  expect(screen.getByRole("button", { name: /Could not sync, retrying/ })).toBeVisible()
  expect(screen.getByRole("button", { name: "Try now" })).toBeVisible()
  get.mockResolvedValue(ok())
  await tick(20_000)
  expect(screen.getByRole("button", { name: /Synced 0 s ago/ })).toBeVisible()
  expect(screen.queryByRole("button", { name: "Try now" })).toBeNull()
})

test("failures count across a remount, and a hung poll does not stack a second request", async () => {
  get.mockResolvedValueOnce(ok())
  const first = render(<SyncIndicator tripId="t1" />)
  await flush()
  first.unmount()
  get.mockRejectedValue(new TypeError("net"))
  render(<SyncIndicator tripId="t1" />)
  await flush() // mount poll: failure 1
  expect(screen.queryByRole("button", { name: /Could not sync/ })).toBeNull()
  await tick(20_000) // failure 2
  expect(screen.queryByRole("button", { name: /Could not sync/ })).toBeNull()
  await tick(20_000) // failure 3
  expect(screen.getByRole("button", { name: /Could not sync, retrying/ })).toBeVisible()
  expect(get).toHaveBeenCalledTimes(4)
})

test("a server error is a failed poll too", async () => {
  get.mockResolvedValue({ error: {}, response: { status: 503, ok: false, headers: new Headers() } })
  render(<SyncIndicator tripId="t1" />)
  await flush()
  await tick(40_000)
  expect(screen.getByRole("button", { name: /Could not sync, retrying/ })).toBeVisible()
})

test("an accepted queued edit counts as a sync", async () => {
  get.mockRejectedValue(new TypeError("net"))
  render(<SyncIndicator tripId="t1" />)
  await flush()
  act(() => markAccepted("t1"))
  expect(screen.getByRole("button", { name: /Synced 0 s ago/ })).toBeVisible()
})

test("tapping runs a sync now and reports the state", async () => {
  get.mockResolvedValue(ok())
  render(<SyncIndicator tripId="t1" />)
  await flush()
  await tick(10_000)
  fireEvent.click(screen.getByRole("button", { name: /Synced 10 s ago/ }))
  await flush()
  expect(get).toHaveBeenCalledTimes(2)
  expect(track).toHaveBeenCalledWith("sync_indicator_tapped", { state: "synced" })
  expect(screen.getByRole("button", { name: /Synced 0 s ago/ })).toBeVisible()
})

test("the live region is polite and holds the state, never the ticking seconds", async () => {
  get.mockResolvedValue(ok())
  render(<SyncIndicator tripId="t1" />)
  await flush()
  const live = screen.getByText("Synced", { selector: ".sync__live" })
  expect(live).toHaveAttribute("aria-live", "polite")
  expect(live).toHaveTextContent("Synced")
  await tick(5000)
  expect(live).toHaveTextContent(/^Synced$/)
  online(false)
  expect(live).toHaveTextContent("Offline")
  online(true)
})

test("a conflict opens a sheet with Keep mine and Use theirs", async () => {
  get.mockResolvedValue(ok())
  render(<SyncIndicator tripId="t1" />)
  await flush()
  const keepMine = vi.fn().mockResolvedValue(undefined)
  const useTheirs = vi.fn()
  act(() => reportConflict("t1", { keepMine, useTheirs }))
  expect(screen.getByRole("dialog", { name: "This trip changed elsewhere" })).toBeVisible()
  fireEvent.click(screen.getByRole("button", { name: "Keep mine" }))
  await flush()
  expect(keepMine).toHaveBeenCalled()
  expect(screen.queryByRole("dialog")).toBeNull()
  act(() => reportConflict("t1", { keepMine, useTheirs }))
  fireEvent.click(screen.getByRole("button", { name: "Use theirs" }))
  await flush()
  expect(useTheirs).toHaveBeenCalled()
  expect(screen.queryByRole("dialog")).toBeNull()
})

test("syncNow is exported for callers that save and want the indicator refreshed", async () => {
  get.mockResolvedValue(ok())
  await syncNow("t9")
  expect(get).toHaveBeenCalledTimes(1)
})
