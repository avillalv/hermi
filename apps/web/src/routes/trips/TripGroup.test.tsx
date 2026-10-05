import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { bodyOf, mockApi, reset, show } from "../onboarding/testing"
import { TripGroup } from "./TripGroup"

const ana = { id: "p1", name: "Ana", color: "#FF5E7E", home_airports: ["LIS"], linked_user_id: null, is_me: false }
const sam = { id: "p2", name: "Sam", color: "#FFCB2E", home_airports: [], linked_user_id: null, is_me: false }
const me = { ...ana, linked_user_id: "u1", is_me: true }
const trip = (over: Record<string, unknown> = {}) => ({
  id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null,
  home_currency: "USD", my_role: "owner", destinations: [], travelers: [ana, sam], ...over,
})
const open = () => show(<TripGroup />, "/trips/:id/group", "/trips/t1/group")
const isGet = (i?: RequestInit) => !i?.method || i.method === "GET"
const withTrip = (t: unknown, more?: (u: string, i?: RequestInit) => Response | undefined) => (u: string, i?: RequestInit) =>
  u.endsWith("/v1/trips/t1") && isGet(i) ? Response.json(t) : more?.(u, i)
const did = (f: ReturnType<typeof mockApi>, method: string, suffix: string) =>
  f.mock.calls.some(([u, i]) => String(u).endsWith(suffix) && (i as RequestInit | undefined)?.method === method)

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows skeleton rows, then each traveler is one labeled group", async () => {
  mockApi(() => new Promise(() => {}) as never)
  const { container, unmount } = open()
  expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument()
  expect(container.querySelectorAll(".state-skel--line").length).toBeGreaterThanOrEqual(2)
  unmount()
  reset("free")
  mockApi(withTrip(trip({ travelers: [{ ...ana, linked_user_id: "u9" }, sam] })))
  open()
  expect(await screen.findByRole("group", { name: "Ana, home airport LIS" })).toBeInTheDocument()
  expect(screen.getByRole("group", { name: "Sam" })).toBeInTheDocument()
})

test("my own row names my role", async () => {
  mockApi(withTrip(trip({ travelers: [me, sam] })))
  open()
  expect(await screen.findByRole("group", { name: "Ana, owner, home airport LIS" })).toBeInTheDocument()
})

test("the section strip marks Group as the current section", async () => {
  mockApi(withTrip(trip()))
  open()
  await screen.findByRole("group", { name: /Ana/ })
  expect(screen.getByRole("link", { name: "Group" })).toHaveAttribute("aria-current", "page")
  expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/trips/t1")
})

test("an empty trip says Just you so far", async () => {
  mockApi(withTrip(trip({ travelers: [] })))
  open()
  expect(await screen.findByText("Just you so far")).toBeInTheDocument()
  expect(screen.getByText("Add your travel partner so plans and fares are shared.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Invite" })).toBeEnabled()
})

test("a load error shows the message and a retry", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load people. Pull down to try again.")
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("a viewer sees the list with no edit controls", async () => {
  mockApi(withTrip(trip({ my_role: "viewer" })))
  open()
  await screen.findByRole("group", { name: /Ana/ })
  expect(screen.queryByRole("button", { name: /Add traveler|Edit|Remove|Invite/ })).not.toBeInTheDocument()
})

test("there are no birthdate or email fields on the traveler form", async () => {
  mockApi(withTrip(trip()))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Add traveler" }))
  expect(screen.getByLabelText("First name")).toBeInTheDocument()
  expect(screen.getByLabelText("Home airport")).toBeInTheDocument()
  expect(screen.queryByLabelText(/birth|email/i)).not.toBeInTheDocument()
})

test("adding a traveler creates the person and puts them on the trip", async () => {
  const f = mockApi(
    withTrip(trip(), (u, i) => {
      if (u.endsWith("/members")) return Response.json([])
      if (u.endsWith("/v1/people") && i?.method === "POST") return Response.json({ ...sam, id: "p3", name: "Lea", home_airports: ["OPO"] }, { status: 201 })
      if (u.endsWith("/v1/trips/t1/travelers")) return Response.json([ana, sam])
    }),
  )
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Add traveler" }))
  fireEvent.change(screen.getByLabelText("First name"), { target: { value: "Lea" } })
  fireEvent.change(screen.getByLabelText("Home airport"), { target: { value: "opo" } })
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  await waitFor(() => expect(bodyOf(f, "/v1/trips/t1/travelers")).toEqual({ person_ids: ["p1", "p2", "p3"] }))
  expect(bodyOf(f, "/v1/people")).toMatchObject({ name: "Lea", home_airports: ["OPO"] })
})

test("editing a traveler saves name, color and airport", async () => {
  const f = mockApi(withTrip(trip({ travelers: [me, sam] }), (u, i) => (u.endsWith("/v1/people/p1") && i?.method === "PUT" ? Response.json(ana) : undefined)))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Edit Ana" }))
  fireEvent.change(screen.getByLabelText("First name"), { target: { value: "Ana M" } })
  fireEvent.click(screen.getByRole("radio", { name: "Color 3" }))
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  await waitFor(() => expect(bodyOf(f, "/v1/people/p1")).toMatchObject({ name: "Ana M", color: "#2BBFAD", home_airports: ["LIS"] }))
})

test("removing a traveler takes them off the trip and keeps the person", async () => {
  const f = mockApi(withTrip(trip(), (u, i) => (u.endsWith("/v1/trips/t1/travelers") && i?.method === "PUT" ? Response.json([sam]) : undefined)))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Remove Ana from this trip" }))
  await waitFor(() => expect(bodyOf(f, "/v1/trips/t1/travelers")).toEqual({ person_ids: ["p2"] }))
  expect(f.mock.calls.some(([u, i]) => String(u).includes("/v1/people/") && (i as RequestInit)?.method === "DELETE")).toBe(false)
})

test("Which traveler are you? links the account to a traveler", async () => {
  const f = mockApi(
    withTrip(trip(), (u, i) =>
      u.endsWith("/v1/trips/t1/members/me/traveler") && i?.method === "PUT" ? Response.json({ user_id: "u1", role: "owner", person_id: "p2" }) : undefined,
    ),
  )
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Which traveler are you?" }))
  const chooser = screen.getByRole("group", { name: "Which traveler are you?" })
  fireEvent.click(within(chooser).getByRole("button", { name: "Sam" }))
  await waitFor(() => expect(bodyOf(f, "/v1/trips/t1/members/me/traveler")).toEqual({ person_id: "p2" }))
})

test("a linked traveler can be unlinked, and the link prompt is gone", async () => {
  const f = mockApi(withTrip(trip({ travelers: [me, sam] }), (u, i) => (u.endsWith("/members/me/traveler") && i?.method === "DELETE" ? new Response(null, { status: 204 }) : undefined)))
  open()
  const unlink = await screen.findByRole("button", { name: "Unlink from Ana" })
  expect(screen.queryByRole("button", { name: "Which traveler are you?" })).not.toBeInTheDocument()
  fireEvent.click(unlink)
  await waitFor(() => expect(did(f, "DELETE", "/v1/trips/t1/members/me/traveler")).toBe(true))
})

test("the traveler cap shows an inline message with a link to Plan and credits, and no paywall sheet", async () => {
  mockApi(
    withTrip(trip(), (u, i) => {
      if (u.endsWith("/members")) return Response.json([])
      if (u.endsWith("/v1/people") && i?.method === "POST") return Response.json({ ...sam, id: "p3" }, { status: 201 })
      if (u.endsWith("/v1/trips/t1/travelers")) return Response.json({ code: "limit_reached", paywall: { reason: "traveler_limit" } }, { status: 402 })
    }),
  )
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Add traveler" }))
  fireEvent.change(screen.getByLabelText("First name"), { target: { value: "Lea" } })
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("Free trips have 2 travelers. Plus or a Trip Pass allows 8.")
  expect(screen.getByRole("link", { name: "Plan and credits" })).toHaveAttribute("href", "/account")
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
})

test("offline: groups render and every write control is disabled", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(withTrip(trip({ travelers: [me, sam] })))
  open()
  expect(await screen.findByRole("group", { name: "Ana, owner, home airport LIS" })).toBeInTheDocument()
  expect(screen.getByRole("status")).toHaveTextContent("You are offline.")
  for (const name of ["Add traveler", "Edit Ana", "Remove Ana from this trip"]) expect(screen.getByRole("button", { name })).toBeDisabled()
})

test("a trip that is not available says so, with no retry", async () => {
  mockApi((u) => (u.endsWith("/v1/trips/t1") ? new Response("{}", { status: 404 }) : undefined))
  open()
  expect(await screen.findByRole("alert")).toHaveTextContent("This trip is not available.")
  expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument()
})
