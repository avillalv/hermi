import { fireEvent, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { CreateTrip } from "./CreateTrip"
import { bodyOf, mockApi, reset, show } from "./testing"

const created = () => Response.json({ id: "t1", name: "x" }, { status: 201 })
const isCreate = (u: string, init?: RequestInit) => u.endsWith("/v1/trips") && init?.method === "POST"
const suggest = (u: string) =>
  u.includes("/v1/geo/destinations") ? Response.json([{ name: "Lisbon", country: "Portugal", country_code: "PT", lat: 38.7, lon: -9.1 }]) : undefined

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const next = () => fireEvent.click(screen.getByRole("button", { name: "Next" }))
const fill = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } })
const toStep3 = (place = "Rome") => {
  fill("Search a city or country", place)
  next()
  fireEvent.click(screen.getByLabelText("I do not have dates yet"))
  next()
}

test("three steps create a trip with the picked place, dates and name, then go to Trips", async () => {
  const f = mockApi((u, init) => suggest(u) ?? (isCreate(u, init) ? created() : undefined))
  show(<CreateTrip />, "/trips/new")
  expect(screen.getByText("Step 1 of 3")).toBeInTheDocument()
  fill("Search a city or country", "Lis")
  fireEvent.click(await screen.findByRole("option", { name: /Lisbon/ }))
  next()
  expect(screen.getByText("Step 2 of 3")).toBeInTheDocument()
  fill("Start date", "2027-03-12")
  fill("End date", "2027-03-19")
  next()
  expect(screen.getByText("Step 3 of 3")).toBeInTheDocument()
  expect(screen.getByLabelText("Trip name")).toHaveValue("Lisbon, March")
  expect(screen.getByText("Just me")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/))
  const body = bodyOf(f, "/v1/trips")
  expect(body).toMatchObject({ name: "Lisbon, March", start_date: "2027-03-12", end_date: "2027-03-19" })
  expect(body.destinations[0]).toMatchObject({ name: "Lisbon", lat: 38.7, lon: -9.1 })
})

test("dates are optional and a place can be typed when search fails", async () => {
  const f = mockApi((u, init) => (u.includes("/geo/") ? new Response("{}", { status: 500 }) : isCreate(u, init) ? created() : undefined))
  show(<CreateTrip />, "/trips/new")
  fill("Search a city or country", "Porto")
  expect(await screen.findByText(/We could not search places right now/)).toBeInTheDocument()
  next()
  fireEvent.click(screen.getByLabelText("I do not have dates yet"))
  next()
  expect(screen.getByLabelText("Trip name")).toHaveValue("Porto")
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  await waitFor(() => expect(bodyOf(f, "/v1/trips")).toBeDefined())
  const body = bodyOf(f, "/v1/trips")
  expect(body.start_date).toBeUndefined()
  expect(body.destinations).toBeUndefined()
})

test("step 1 needs a place and step 2 rejects an end before the start", () => {
  mockApi(() => undefined)
  show(<CreateTrip />, "/trips/new")
  next()
  expect(screen.getByText("Step 1 of 3")).toBeInTheDocument()
  fill("Search a city or country", "Rome")
  next()
  fill("Start date", "2027-03-12")
  fill("End date", "2027-03-01")
  next()
  expect(screen.getByRole("alert")).toHaveTextContent("The end date must be on or after the start date.")
  expect(screen.getByText("Step 2 of 3")).toBeInTheDocument()
})

test("Back keeps what was typed", () => {
  mockApi(() => undefined)
  show(<CreateTrip />, "/trips/new")
  fill("Search a city or country", "Rome")
  next()
  fireEvent.click(screen.getByRole("button", { name: "Back" }))
  expect(screen.getByLabelText("Search a city or country")).toHaveValue("Rome")
})

test("the Free trip limit shows the limit copy", async () => {
  mockApi((u, init) => (isCreate(u, init) ? Response.json({ code: "limit_reached" }, { status: 402 }) : undefined))
  show(<CreateTrip />, "/trips/new")
  toStep3()
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("You have 2 active trips. Archive one to make room, or upgrade.")
})

test("a server error shows the create failure", async () => {
  mockApi((u, init) => (isCreate(u, init) ? new Response("{}", { status: 500 }) : undefined))
  show(<CreateTrip />, "/trips/new")
  toStep3()
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("We could not create your trip. Try again.")
})

test("offline disables Create and says so", () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(() => undefined)
  show(<CreateTrip />, "/trips/new")
  toStep3()
  expect(screen.getByRole("button", { name: "Create trip" })).toBeDisabled()
  expect(screen.getByRole("status")).toHaveTextContent("You are offline. Connect to create your trip.")
})

test("the place list works from the keyboard", async () => {
  mockApi((u) =>
    u.includes("/v1/geo/destinations")
      ? Response.json([
          { name: "Lisbon", country: "Portugal", lat: 38.7, lon: -9.1 },
          { name: "Lima", country: "Peru", lat: -12, lon: -77 },
        ])
      : undefined,
  )
  show(<CreateTrip />, "/trips/new")
  const input = screen.getByLabelText("Search a city or country")
  fireEvent.change(input, { target: { value: "Li" } })
  await screen.findAllByRole("option")
  fireEvent.keyDown(input, { key: "ArrowDown" })
  expect(input).toHaveAttribute("aria-activedescendant", screen.getAllByRole("option")[0].id)
  fireEvent.keyDown(input, { key: "ArrowDown" })
  fireEvent.keyDown(input, { key: "ArrowDown" }) // wraps to the first
  fireEvent.keyDown(input, { key: "ArrowUp" }) // wraps to the last
  expect(input).toHaveAttribute("aria-activedescendant", screen.getAllByRole("option")[1].id)
  fireEvent.keyDown(input, { key: "Enter" })
  expect(input).toHaveValue("Lima")
  expect(screen.queryByRole("option")).not.toBeInTheDocument()
  expect(screen.getByText("Step 1 of 3")).toBeInTheDocument() // Enter on an option picks, it does not advance
  fireEvent.change(input, { target: { value: "Lis" } })
  await screen.findAllByRole("option")
  fireEvent.keyDown(input, { key: "Escape" })
  expect(screen.queryByRole("option")).not.toBeInTheDocument()
})

test("a step 1 error is announced once", () => {
  mockApi(() => undefined)
  show(<CreateTrip />, "/trips/new")
  next()
  expect(screen.getAllByRole("alert")).toHaveLength(1)
})

const tripEvents = () => {
  const seen: { event: string; props: Record<string, unknown> }[] = []
  const on = (e: Event) => seen.push((e as CustomEvent).detail)
  window.addEventListener("hermi:event", on)
  return { seen, stop: () => window.removeEventListener("hermi:event", on) }
}

test("a successful create fires trip_created once with the catalogue properties", async () => {
  const ev = tripEvents()
  mockApi((u, init) => suggest(u) ?? (isCreate(u, init) ? created() : undefined))
  show(<CreateTrip />, "/trips/new")
  fill("Search a city or country", "Lis")
  fireEvent.click(await screen.findByRole("option", { name: /Lisbon/ }))
  next()
  fill("Start date", "2027-03-12")
  fill("End date", "2027-03-19")
  next()
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/))
  expect(ev.seen.filter((e) => e.event === "trip_created")).toEqual([{ event: "trip_created", props: { source: "blank", destination_count: 1, has_dates: true } }])
  ev.stop()
})

test("a failing create does not fire trip_created", async () => {
  const ev = tripEvents()
  const f = mockApi((u, init) => (isCreate(u, init) ? new Response("{}", { status: 500 }) : undefined))
  show(<CreateTrip />, "/trips/new")
  toStep3()
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  await waitFor(() => expect(bodyOf(f, "/v1/trips")).toBeDefined())
  await screen.findByRole("alert")
  expect(ev.seen.filter((e) => e.event === "trip_created")).toHaveLength(0)
  ev.stop()
})
