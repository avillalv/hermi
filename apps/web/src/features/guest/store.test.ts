import { beforeEach, expect, test, vi } from "vitest"

const track = vi.hoisted(() => vi.fn())
vi.mock("../../lib/track", () => ({ track }))

import { GUEST_KEY, addGuestItem, claimPayload, clearGuest, createGuestTrip, readGuest, reloadGuest, removeGuestItem, updateGuestTrip } from "./store"

beforeEach(() => {
  localStorage.clear()
  reloadGuest()
  track.mockClear()
})

test("a guest plans one trip, and guest_trip_created fires once", () => {
  expect(createGuestTrip({ name: "Lisbon", destination: "Lisbon", start_date: "2027-03-12", end_date: "2027-03-15" })).toBe(true)
  expect(createGuestTrip({ name: "Porto" })).toBe(false)
  expect(readGuest()?.trip.name).toBe("Lisbon")
  expect(track.mock.calls.filter(([n]) => n === "guest_trip_created")).toHaveLength(1)
})

test("edits stay on the device and keep the same claim id", () => {
  createGuestTrip({ name: "Lisbon" })
  const id = readGuest()!.claim_id
  addGuestItem({ title: "Castelo", day: "2027-03-12", start_time: "10:00", category: "sights", location_name: null })
  updateGuestTrip({ name: "Lisbon trip" })
  reloadGuest()
  expect(readGuest()?.claim_id).toBe(id)
  expect(readGuest()?.trip.items).toHaveLength(1)
  removeGuestItem(readGuest()!.trip.items[0].id)
  expect(readGuest()?.trip.items).toHaveLength(0)
  expect(JSON.parse(localStorage.getItem(GUEST_KEY)!).claim_id).toBe(id)
})

test("the old read-only sample copy is migrated into an editable trip once", () => {
  localStorage.setItem(
    "hermi.guestTrip",
    JSON.stringify({
      saved_at: "2026-10-01T00:00:00Z",
      sample: {
        title: "Lisbon in 5 days",
        presentation: {
          trip: { name: "Lisbon in 5 days", destinations: [{ name: "Lisbon" }] },
          days: [{ day: "2027-03-12", title: "Alfama", items: [{ id: "i1", start_time: "10:00:00", title: "Castelo walk", category: "activity", location_name: "Alfama" }] }],
          stays: [],
        },
      },
    }),
  )
  reloadGuest()
  const d = readGuest()!
  expect(d.trip).toMatchObject({ name: "Lisbon in 5 days", destinations: ["Lisbon"], start_date: "2027-03-12" })
  expect(d.trip.items[0]).toMatchObject({ title: "Castelo walk", day: "2027-03-12", start_time: "10:00", category: "other" })
  expect(localStorage.getItem("hermi.guestTrip")).toBeNull()
  const id = d.claim_id
  reloadGuest()
  expect(readGuest()?.claim_id).toBe(id)
})

test("a damaged value reads as no trip, and clearing removes it", () => {
  localStorage.setItem(GUEST_KEY, "{not json")
  reloadGuest()
  expect(readGuest()).toBeNull()
  createGuestTrip({ name: "A" })
  clearGuest()
  expect(localStorage.getItem(GUEST_KEY)).toBeNull()
})

test("the claim payload sends dates only as a pair and keeps destinations in the notes", () => {
  createGuestTrip({ name: "Lisbon", destination: "Lisbon", start_date: "2027-03-12" })
  expect(claimPayload(readGuest()!)).toMatchObject({ name: "Lisbon", start_date: null, end_date: null, notes: "Destinations: Lisbon", destinations: [] })
})

test("the claim payload always satisfies the server trip shape", () => {
  createGuestTrip({ name: "Lisbon", destination: "Porto" })
  updateGuestTrip({ name: "   " })
  expect(claimPayload(readGuest()!).name).toBe("Porto")
  updateGuestTrip({ destinations: [] })
  expect(claimPayload(readGuest()!).name).toBe("My trip")
  updateGuestTrip({ name: "x".repeat(300) })
  expect(claimPayload(readGuest()!).name).toHaveLength(120)
  addGuestItem({ title: "y".repeat(500), day: null, start_time: null, category: "other", location_name: null })
  expect(claimPayload(readGuest()!).items[0].title).toHaveLength(200)
  updateGuestTrip({ start_date: "2027-03-12", end_date: "2027-03-10" })
  expect(claimPayload(readGuest()!)).toMatchObject({ start_date: null, end_date: null })
  updateGuestTrip({ start_date: "2027-03-10", end_date: "2027-03-12" })
  expect(claimPayload(readGuest()!)).toMatchObject({ start_date: "2027-03-10", end_date: "2027-03-12" })
})

test("the claim payload caps items at 200 and location_name at 200 characters", () => {
  createGuestTrip({ name: "Lisbon", destination: "Lisbon" })
  for (let i = 0; i < 205; i++) addGuestItem({ title: `Stop ${i}`, day: null, start_time: null, category: "other", location_name: i === 0 ? "z".repeat(300) : null })
  const p = claimPayload(readGuest()!)
  expect(p.items).toHaveLength(200)
  expect(p.items[0].location_name).toHaveLength(200)
})
