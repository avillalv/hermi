import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

const track = vi.hoisted(() => vi.fn())
vi.mock("../../lib/track", () => ({ track }))

import { queryClient } from "../../lib/queryClient"
import { authStore } from "../../routes/auth/authStore"
import { mockApi, reset } from "../../routes/onboarding/testing"
import { GuestClaimHost } from "./GuestClaimHost"
import { GuestBanner } from "./GuestBanner"
import { GUEST_KEY, addGuestItem, clearGuest, createGuestTrip, readGuest, reloadGuest } from "./store"

const json = (b: unknown, status = 200) => Response.json(b, { status })
const claimCalls = (f: ReturnType<typeof mockApi>) => f.mock.calls.filter(([u]) => String(u).endsWith("/v1/me/claim"))
const bodies = (f: ReturnType<typeof mockApi>) => claimCalls(f).map(([, i]) => JSON.parse(String((i as RequestInit).body)))

const mount = () =>
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <GuestBanner />
        <GuestClaimHost />
      </MemoryRouter>
    </QueryClientProvider>,
  )

beforeEach(() => {
  reset("free") // signed in as a dev persona
  localStorage.clear()
  clearGuest()
  reloadGuest()
  track.mockClear()
  createGuestTrip({ name: "Lisbon", destination: "Lisbon" })
  addGuestItem({ title: "Castelo", day: "2027-03-12", start_time: "10:00", category: "sights", location_name: null })
})
afterEach(() => {
  vi.unstubAllGlobals()
  authStore.signOut()
})

const me = (u: string) => (u.endsWith("/v1/me") ? json({ id: "u1" }) : undefined)

test("a guest trip is claimed once with its claim id, then cleared", async () => {
  const f = mockApi((u) => me(u) ?? (u.endsWith("/v1/me/claim") ? json({ trip_id: "t1", people_imported: 0, items_imported: 1, archived: false }) : undefined))
  const claimId = readGuest()!.claim_id
  mount()
  expect(await screen.findByRole("dialog", { name: "Your trip is saved" })).toBeInTheDocument()
  expect(claimCalls(f)).toHaveLength(1)
  expect(bodies(f)[0]).toMatchObject({ claim_id: claimId, trip: { name: "Lisbon", items: [{ title: "Castelo" }] } })
  expect(bodies(f)[0].merge).toBeUndefined()
  expect(readGuest()).toBeNull()
})

test("an account with trips gets the Merge or Keep separate choice with the count", async () => {
  let n = 0
  const f = mockApi(
    (u) =>
      me(u) ??
      (u.endsWith("/v1/me/claim")
        ? n++ === 0
          ? json({ code: "state_conflict", detail: "x", counts: { trips: 2, people: 1 } }, 409)
          : json({ trip_id: "t1", people_imported: 0, items_imported: 1, archived: false })
        : undefined),
  )
  mount()
  const dialog = await screen.findByRole("dialog", { name: "Add this trip to your account?" })
  expect(within(dialog).getByText("You already have 2 trips. Add this one too?")).toBeInTheDocument()
  expect(readGuest()).not.toBeNull()
  fireEvent.click(within(dialog).getByRole("button", { name: "Add this trip" }))
  await screen.findByRole("dialog", { name: "Your trip is saved" })
  expect(bodies(f).map((b) => b.merge)).toEqual([undefined, true])
  expect(new Set(bodies(f).map((b) => b.claim_id)).size).toBe(1)
  expect(readGuest()).toBeNull()
})

test("Keep separate leaves the trip on the phone and does not ask again", async () => {
  const f = mockApi((u) => me(u) ?? (u.endsWith("/v1/me/claim") ? json({ code: "state_conflict", detail: "x", counts: { trips: 1, people: 0 } }, 409) : undefined))
  const view = mount()
  const dialog = await screen.findByRole("dialog", { name: "Add this trip to your account?" })
  expect(within(dialog).getByText("You already have 1 trip. Add this one too?")).toBeInTheDocument()
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep separate" }))
  expect(await screen.findByRole("dialog", { name: "Your trip stays on this phone" })).toBeInTheDocument()
  expect(readGuest()?.kept_separate).toBe(true)
  view.unmount()
  mount()
  await new Promise((r) => setTimeout(r, 30))
  expect(claimCalls(f)).toHaveLength(1)
})

test("an over-limit claim comes back archived and says so", async () => {
  mockApi((u) => me(u) ?? (u.endsWith("/v1/me/claim") ? json({ trip_id: "t1", people_imported: 0, items_imported: 1, archived: true }) : undefined))
  mount()
  const dialog = await screen.findByRole("dialog", { name: "Your trip is saved" })
  expect(within(dialog).getByText(/archived/)).toBeInTheDocument()
})

test("a failed claim keeps the local trip, and Retry reuses the same claim id", async () => {
  let n = 0
  const f = mockApi((u) => me(u) ?? (u.endsWith("/v1/me/claim") ? (n++ === 0 ? json({ code: "internal_error" }, 500) : json({ trip_id: "t1", people_imported: 0, items_imported: 1, archived: false })) : undefined))
  mount()
  const dialog = await screen.findByRole("alert")
  expect(dialog).toHaveTextContent("We could not move your trip into your account. It is still on this phone. Try again.")
  expect(readGuest()?.trip.items).toHaveLength(1)
  fireEvent.click(screen.getByRole("button", { name: "Retry" }))
  await screen.findByRole("dialog", { name: "Your trip is saved" })
  expect(claimCalls(f)).toHaveLength(2)
  expect(new Set(bodies(f).map((b) => b.claim_id)).size).toBe(1)
  await waitFor(() => expect(readGuest()).toBeNull())
})

test("nothing is claimed while signed out, or when there is no guest trip", async () => {
  authStore.signOut()
  const f = mockApi(() => json({}))
  mount()
  await new Promise((r) => setTimeout(r, 30))
  expect(f).not.toHaveBeenCalled()
  authStore.signIn("tok", "free")
  clearGuest()
  await new Promise((r) => setTimeout(r, 30))
  expect(claimCalls(f)).toHaveLength(0)
})

test("Keep separate stays claimable while signed in: the banner Save claims with merge and the same claim id", async () => {
  let n = 0
  const f = mockApi(
    (u) =>
      me(u) ??
      (u.endsWith("/v1/me/claim")
        ? n++ === 0
          ? json({ code: "state_conflict", detail: "x", counts: { trips: 1, people: 0 } }, 409)
          : json({ trip_id: "t1", people_imported: 0, items_imported: 1, archived: false })
        : undefined),
  )
  const claimId = readGuest()!.claim_id
  mount()
  const dialog = await screen.findByRole("dialog", { name: "Add this trip to your account?" })
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep separate" }))
  const kept = await screen.findByRole("dialog", { name: "Your trip stays on this phone" })
  fireEvent.click(within(kept).getByRole("button", { name: /ok/i }))
  const banner = await screen.findByRole("region", { name: "Guest trip" })
  fireEvent.click(within(banner).getByRole("button", { name: "Save" }))
  await screen.findByRole("dialog", { name: "Your trip is saved" })
  expect(bodies(f).map((b) => b.merge)).toEqual([undefined, true])
  expect(bodies(f)[1].claim_id).toBe(claimId)
  expect(readGuest()).toBeNull()
})

test("after Not now on a failed claim the banner Save retries it", async () => {
  let n = 0
  const f = mockApi((u) => me(u) ?? (u.endsWith("/v1/me/claim") ? (n++ === 0 ? json({ code: "internal_error" }, 500) : json({ trip_id: "t1", people_imported: 0, items_imported: 1, archived: false })) : undefined))
  mount()
  await screen.findByRole("alert")
  fireEvent.click(screen.getByRole("button", { name: "Not now" }))
  const banner = await screen.findByRole("region", { name: "Guest trip" })
  fireEvent.click(within(banner).getByRole("button", { name: "Save" }))
  await screen.findByRole("dialog", { name: "Your trip is saved" })
  expect(claimCalls(f)).toHaveLength(2)
  expect(new Set(bodies(f).map((b) => b.claim_id)).size).toBe(1)
})

test("Save on a kept trip after a reload sends one merge claim with the stored claim id", async () => {
  const f = mockApi((u) => me(u) ?? (u.endsWith("/v1/me/claim") ? json({ trip_id: "t1", people_imported: 0, items_imported: 1, archived: false }) : undefined))
  const claimId = readGuest()!.claim_id
  localStorage.setItem(GUEST_KEY, JSON.stringify({ ...readGuest()!, kept_separate: true }))
  reloadGuest()
  queryClient.setQueryData(["me"], true)
  mount()
  const banner = await screen.findByRole("region", { name: "Guest trip" })
  fireEvent.click(within(banner).getByRole("button", { name: "Save" }))
  await screen.findByRole("dialog", { name: "Your trip is saved" })
  await new Promise((r) => setTimeout(r, 30))
  expect(bodies(f)).toHaveLength(1)
  expect(bodies(f)[0]).toMatchObject({ merge: true, claim_id: claimId })
})

test("closing the Merge choice keeps the trip reachable from the banner", async () => {
  mockApi((u) => me(u) ?? (u.endsWith("/v1/me/claim") ? json({ code: "state_conflict", detail: "x", counts: { trips: 1, people: 0 } }, 409) : undefined))
  mount()
  const dialog = await screen.findByRole("dialog", { name: "Add this trip to your account?" })
  fireEvent.keyDown(dialog, { key: "Escape" })
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
  expect(readGuest()?.kept_separate).toBe(true)
  const banner = screen.getByRole("region", { name: "Guest trip" })
  expect(within(banner).getByText("Guest trip, not in your account yet")).toBeInTheDocument()
})
