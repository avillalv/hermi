import { fireEvent, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { mockApi, reset, show } from "../onboarding/testing"
import { TripEdit } from "./TripEdit"

const lisbon = { id: "d1", position: 0, name: "Lisbon", region: null, country: "Portugal", timezone: "Europe/Lisbon", lat: 38.7, lon: -9.1 }
const porto = { name: "Porto", region: "Porto", country: "Portugal", country_code: "PT", lat: 41.15, lon: -8.61, timezone: "Atlantic/Azores" }
const trip = { id: "t1", version: 3, name: "Lisbon, March", status: "planning", start_date: "2027-03-12", end_date: "2027-03-19", home_currency: "USD", my_role: "owner", destinations: [lisbon] }
const open = () => show(<TripEdit />, "/trips/:id/edit", "/trips/t1/edit")

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const get = (t: unknown = trip) => (u: string, init?: RequestInit) =>
  u.endsWith("/v1/trips/t1") && (!init?.method || init.method === "GET") ? Response.json(t) : undefined

test("loading shows a status, then the form is prefilled", async () => {
  mockApi(get())
  open()
  expect(screen.getByText("Loading your trip")).toBeInTheDocument()
  expect(await screen.findByLabelText("Trip name")).toHaveValue("Lisbon, March")
  expect(screen.getByLabelText("Start date")).toHaveValue("2027-03-12")
  expect(screen.getByLabelText("End date")).toHaveValue("2027-03-19")
  expect(screen.getByLabelText("Currency")).toHaveValue("USD")
  expect(screen.getByText("Lisbon, Portugal")).toBeInTheDocument()
  expect(screen.getByText("Europe/Lisbon")).toBeInTheDocument()
})

test("a place from the search is added with its time zone, and a destination can be removed", async () => {
  mockApi((u, init) => (u.includes("/v1/geo/destinations") ? Response.json([porto]) : get()(u, init)))
  open()
  fireEvent.change(await screen.findByLabelText("Add a destination"), { target: { value: "Por" } })
  fireEvent.click(await screen.findByRole("option", { name: "Porto, Portugal" }))
  expect(screen.getByText("Atlantic/Azores")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Remove Lisbon" }))
  expect(screen.queryByText("Lisbon, Portugal")).not.toBeInTheDocument()
})

test("Save sends the changes with the version and returns to the trip", async () => {
  const f = mockApi((u, init) => (init?.method === "PATCH" ? Response.json({ ...trip, version: 4 }) : get()(u, init)))
  open()
  fireEvent.change(await screen.findByLabelText("Trip name"), { target: { value: "Lisbon and Porto" } })
  fireEvent.change(screen.getByLabelText("Currency"), { target: { value: "EUR" } })
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/trips\/t1$/))
  const body = JSON.parse(String((f.mock.calls.find(([, i]) => i?.method === "PATCH")![1] as RequestInit).body))
  expect(body).toMatchObject({ name: "Lisbon and Porto", home_currency: "EUR", start_date: "2027-03-12", end_date: "2027-03-19", version: 3 })
  expect(body).not.toHaveProperty("destinations") // unchanged list: the API keeps kind, bbox and provider id
})

test("removing and adding a destination sends the list, a kept one as just its identity", async () => {
  const f = mockApi((u, init) =>
    init?.method === "PATCH" ? Response.json(trip) : u.includes("/v1/geo/destinations") ? Response.json([porto]) : get()(u, init),
  )
  open()
  fireEvent.change(await screen.findByLabelText("Add a destination"), { target: { value: "Por" } })
  fireEvent.click(await screen.findByRole("option", { name: "Porto, Portugal" }))
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  await waitFor(() => expect(f.mock.calls.some(([, i]) => i?.method === "PATCH")).toBe(true))
  const body = JSON.parse(String((f.mock.calls.find(([, i]) => i?.method === "PATCH")![1] as RequestInit).body))
  expect(body.destinations).toEqual([{ id: "d1", name: "Lisbon", lat: 38.7, lon: -9.1 }, expect.objectContaining({ name: "Porto", timezone: "Atlantic/Azores" })])
})

test("dates must come as a pair and the end cannot be before the start", async () => {
  const f = mockApi(get())
  open()
  fireEvent.change(await screen.findByLabelText("End date"), { target: { value: "" } })
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  expect(await screen.findByText("Add both dates, or clear both.")).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2027-03-01" } })
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  expect(await screen.findByText("The end date must be on or after the start date.")).toBeInTheDocument()
  expect(f.mock.calls.some(([, i]) => i?.method === "PATCH")).toBe(false)
})

test("a name is required", async () => {
  mockApi(get())
  open()
  fireEvent.change(await screen.findByLabelText("Trip name"), { target: { value: " " } })
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  expect(await screen.findByText("Give your trip a name.")).toBeInTheDocument()
})

test("a viewer cannot edit: no form, a plain explanation", async () => {
  mockApi(get({ ...trip, my_role: "viewer" }))
  open()
  expect(await screen.findByText("Only the owner and editors can change this trip.")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument()
})

test("a conflict (409) and a failed save show an alert and keep the form", async () => {
  let status = 409
  mockApi((u, init) => (init?.method === "PATCH" ? new Response("{}", { status }) : get()(u, init)))
  open()
  await screen.findByLabelText("Trip name")
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("This trip changed elsewhere. Reload and try again.")
  expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument()
  status = 500
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("We could not save your changes. Try again."))
  expect(screen.getByLabelText("Trip name")).toHaveValue("Lisbon, March")
  expect(screen.queryByRole("button", { name: "Reload" })).not.toBeInTheDocument()
})

test("Reload on a conflict fetches the trip again and shows its new values", async () => {
  let current = trip
  const f = mockApi((u, init) => (init?.method === "PATCH" ? new Response("{}", { status: 409 }) : get(current)(u, init)))
  open()
  await screen.findByLabelText("Trip name")
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  current = { ...trip, version: 4, name: "Renamed elsewhere" }
  fireEvent.click(await screen.findByRole("button", { name: "Reload" }))
  expect(await screen.findByDisplayValue("Renamed elsewhere")).toBeInTheDocument()
  expect(f.mock.calls.filter(([, i]) => !i?.method || i.method === "GET").length).toBeGreaterThanOrEqual(2)
})

test("a load error offers Try again", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load this trip. Try again.")
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("offline disables Save and says why", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(get())
  open()
  expect(await screen.findByRole("button", { name: "Save" })).toBeDisabled()
  expect(screen.getByRole("status")).toHaveTextContent("You are offline. Connect to save your changes.")
})

test("a failed place lookup says so and does not block the rest of the form", async () => {
  mockApi((u, init) => (u.includes("/v1/geo/destinations") ? new Response("{}", { status: 503 }) : get()(u, init)))
  open()
  fireEvent.change(await screen.findByLabelText("Add a destination"), { target: { value: "Por" } })
  expect(await screen.findByText("We could not search places right now. Try again in a moment.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Save" })).toBeEnabled()
})
