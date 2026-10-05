import { TRAVELER_COLORS } from "@hermi/tokens"
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { bodyOf, mockApi, reset, show, type Handler } from "../onboarding/testing"
import { bookmarkletHref } from "./Bookmarklet"
import { Stays, brandOf } from "./Stays"

const ANA = { id: "p1", name: "Ana", color: TRAVELER_COLORS[0], home_airports: [], linked_user_id: "u1", is_me: true }
const LEO = { id: "p2", name: "Leo", color: TRAVELER_COLORS[1], home_airports: [], linked_user_id: "u2", is_me: false }
const trip = (over: Record<string, unknown> = {}) => ({
  id: "t1", version: 1, name: "La Fortuna", status: "planning", start_date: "2027-11-27", end_date: "2027-12-01", home_currency: "USD",
  my_role: "owner", destinations: [], travelers: [ANA, LEO], ...over,
})
const usd = (minor: number) => ({ amount_minor: minor, currency: "USD" })
const stay = (id: string, title: string, over: Record<string, unknown> = {}) => ({
  id, trip_id: "t1", title, url: null, site: null, check_in: null, check_out: null, nights: 4, price_total: usd(56800), price_per_night: usd(14200),
  bedrooms: null, rating: 4.9, notes: "", status: "shortlisted", added_via: "paste", version: 1, votes: [], vote_summary: { hearts: 0 }, ...over,
})
const heart = (user: string, person: string) => ({ user_id: user, person_id: person })
const STAYS = () => [
  stay("s1", "Casita with volcano view", { site: "airbnb.com", url: "https://www.airbnb.com/rooms/123?utm_source=x&adults=2#top", votes: [heart("u1", "p1"), heart("u2", "p2")], vote_summary: { hearts: 2 } }),
  stay("s2", "Hotel near the hot springs", { site: "booking.com", price_per_night: usd(18800), price_total: usd(75200), votes: [heart("u2", "p2")], vote_summary: { hearts: 1 } }),
  stay("s3", "Treehouse lodge", { price_per_night: null, price_total: null, rating: null }),
]

type Over = { role?: string; stays?: unknown[]; sorted?: string; more?: Handler }
const api = ({ role = "owner", stays = STAYS(), sorted = "votes", more }: Over = {}): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  const r = more?.(u, i)
  if (r) return r
  if (u.endsWith("/v1/me")) return Response.json({ id: "u1" })
  if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip({ my_role: role }))
  if (u.includes("/trips/t1/lodging?") && m === "GET") return Response.json({ items: stays, has_more: false, next_cursor: null, sorted_by: new URL(u).searchParams.get("sort") ?? sorted })
  return undefined
}
const open = (url = "/trips/t1/stays") => show(<Stays />, "/trips/:id/stays", url)
const call = (f: ReturnType<typeof mockApi>, method: string, part: string) =>
  f.mock.calls.find(([u, i]) => String(u).includes(part) && ((i as RequestInit | undefined)?.method ?? "GET") === method)
const card = (title: string) => screen.findByRole("article", { name: new RegExp(title) })

beforeEach(() => reset("free"))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("loading shows card skeletons", () => {
  mockApi(() => new Promise(() => {}) as never)
  const { container } = open()
  expect(container.querySelectorAll(".stays__skel")).toHaveLength(3)
  expect(screen.getByText("Loading your stays")).toBeInTheDocument()
})

test("error: a failed load shows the message and a retry", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load your stays. Try again.")
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("empty: says no stays and offers Add a stay", async () => {
  mockApi(api({ stays: [] }))
  open()
  expect(await screen.findByText("No stays yet")).toBeInTheDocument()
  expect(screen.getByText("Paste a link or search to start a shortlist.")).toBeInTheDocument()
  expect(screen.getAllByRole("button", { name: "Add a stay" }).length).toBeGreaterThan(0)
})

test("each stay shows its price per night, the total and a prompt when there is no price", async () => {
  mockApi(api())
  open()
  const a = within(await card("Casita"))
  expect(a.getByText("$142")).toBeInTheDocument()
  expect(a.getByText("a night")).toBeInTheDocument()
  expect(a.getByText("$568 total")).toBeInTheDocument()
  expect(within(await card("Hotel")).getByText("$188")).toBeInTheDocument()
  expect(within(await card("Treehouse")).getByText("Add a price to compare")).toBeInTheDocument()
})

test("the sort order is stated, follows the control and never mentions commission", async () => {
  const f = mockApi(api())
  open()
  expect(await screen.findByText("Sorted by hearts, most first")).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText("Sort"), { target: { value: "price" } })
  expect(await screen.findByText("Sorted by price per night, lowest first")).toBeInTheDocument()
  expect(f.mock.calls.some(([u]) => String(u).includes("sort=price"))).toBe(true)
  expect(document.body.textContent).not.toMatch(/recommended|top pick|commission/i)
})

test("a pasted link opens exactly as pasted, and no page of the stay site is ever requested", async () => {
  const f = mockApi(api())
  open()
  const link = within(await card("Casita")).getByRole("link", { name: "Open Casita with volcano view" })
  expect(link.getAttribute("href")).toBe("https://www.airbnb.com/rooms/123?utm_source=x&adults=2#top")
  expect(link).toHaveAttribute("rel", "noopener noreferrer")
  expect(f.mock.calls.every(([u]) => !String(u).includes("airbnb"))).toBe(true)
})

test("the source label names the brand from the real host, and a stay with two travelers shows the per-person price", async () => {
  mockApi(api())
  open()
  const a = within(await card("Casita"))
  expect(a.getByText("Airbnb")).toBeInTheDocument()
  expect(a.getByText("$284 each")).toBeInTheDocument()
  expect(within(await card("Hotel")).getByText("Booking.com")).toBeInTheDocument()
})

test("only http and https links become anchors; javascript: and data: links stay plain text", async () => {
  mockApi(api({ stays: [stay("s1", "Bad one", { url: "javascript:alert(1)" }), stay("s2", "Data one", { url: "data:text/html,hi" }), stay("s3", "Good one", { url: "HTTPS://example.com/x" })] }))
  open()
  expect(within(await card("Bad one")).queryByRole("link")).toBeNull()
  expect(within(await card("Data one")).queryByRole("link")).toBeNull()
  expect(within(await card("Good one")).getByRole("link")).toHaveAttribute("href", "HTTPS://example.com/x")
})

test("the heart toggles for me only, sends voted true then false and updates the tally", async () => {
  const state = { mine: false }
  const f = mockApi(
    api({
      stays: [stay("s2", "Hotel near the hot springs", { votes: [heart("u2", "p2")], vote_summary: { hearts: 1 } })],
      more: (u, i) => {
        if (!u.endsWith("/lodging/s2/votes/me")) return undefined
        state.mine = JSON.parse(String(i?.body)).voted
        const votes = [heart("u2", "p2"), ...(state.mine ? [heart("u1", "p1")] : [])]
        return Response.json(stay("s2", "Hotel near the hot springs", { votes, vote_summary: { hearts: votes.length } }))
      },
    }),
  )
  open()
  const c = within(await card("Hotel"))
  expect(c.getByRole("button", { name: "1 of 2 like this" })).toBeInTheDocument()
  const mine = c.getByRole("button", { name: /^You love this/ })
  expect(mine).toHaveAttribute("aria-pressed", "false")
  expect(c.queryByRole("button", { name: /Leo/ })).toBeNull() // another traveler's heart is not mine to press
  expect(c.getByRole("img", { name: "Leo likes Hotel near the hot springs" })).toBeInTheDocument()
  fireEvent.click(mine)
  await waitFor(() => expect(c.getByRole("button", { name: "2 of 2 like this" })).toBeInTheDocument())
  expect(c.getByRole("button", { name: /^You love this/ })).toHaveAttribute("aria-pressed", "true")
  expect(call(f, "PUT", "/lodging/s2/votes/me")).toBeTruthy()
  fireEvent.click(c.getByRole("button", { name: /^You love this/ }))
  await waitFor(() => expect(c.getByRole("button", { name: "1 of 2 like this" })).toBeInTheDocument())
  expect(state.mine).toBe(false)
})

test("a viewer can heart but cannot add or change stays", async () => {
  mockApi(api({ role: "viewer" }))
  open()
  const c = within(await card("Hotel"))
  expect(c.getByRole("button", { name: /^You love this/ })).toBeEnabled()
  expect(screen.queryByRole("button", { name: "Add a stay" })).toBeNull()
  expect(c.queryByRole("button", { name: /Mark .* as booked/ })).toBeNull()
  expect(screen.getByText("You can heart stays. Only editors can add or change them.")).toBeInTheDocument()
})

test("exactly one stay is Booked: the badge shows and the others cannot be booked", async () => {
  mockApi(api({ stays: [stay("s1", "Casita", { status: "booked" }), stay("s2", "Hotel"), stay("s3", "Treehouse")] }))
  open()
  const a = within(await card("Casita"))
  expect(a.getByText("Booked")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /Mark .* as booked/ })).toBeNull()
  expect(screen.getByText("One stay is booked. Mark it as not booked to book another.")).toBeInTheDocument()
  expect(a.getByRole("button", { name: "Mark Casita as not booked" })).toBeInTheDocument()
})

test("Mark booked sends status booked, and a 409 from the API shows its message", async () => {
  const f = mockApi(api({ more: (u, i) => (u.endsWith("/lodging/s2") && i?.method === "PATCH" ? Response.json({ code: "state_conflict", detail: "Another stay is already booked. Change it first." }, { status: 409 }) : undefined) }))
  open()
  fireEvent.click(within(await card("Hotel")).getByRole("button", { name: "Mark Hotel near the hot springs as booked" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("Another stay is already booked. Change it first.")
  expect(bodyOf(f, "/lodging/s2")).toEqual({ status: "booked", version: 1 })
})

test("rejected stays sit in a collapsed section with Restore", async () => {
  const f = mockApi(api({ stays: [stay("s1", "Casita"), stay("s2", "Hotel", { status: "rejected" })] }))
  open()
  await card("Casita")
  expect(screen.queryByRole("article", { name: /Hotel/ })).toBeNull()
  const toggle = screen.getByRole("button", { name: "Rejected (1)" })
  expect(toggle).toHaveAttribute("aria-expanded", "false")
  fireEvent.click(toggle)
  expect(toggle).toHaveAttribute("aria-expanded", "true")
  fireEvent.click(within(await card("Hotel")).getByRole("button", { name: "Restore Hotel" }))
  await waitFor(() => expect(bodyOf(f, "/lodging/s2")).toEqual({ status: "shortlisted", version: 1 }))
})

const five = () => [stay("s1", "One"), stay("s2", "Two"), stay("s3", "Three"), stay("s4", "Four"), stay("s5", "Five")]

test("compare cap: the bar shows for 2 to 4 stays and a fifth cannot be picked", async () => {
  mockApi(api({ stays: five() }))
  open()
  await card("One")
  expect(screen.queryByRole("button", { name: /^Compare \(/ })).toBeNull()
  const pick = (t: string) => screen.getByRole("checkbox", { name: `Compare ${t}` })
  fireEvent.click(pick("One"))
  expect(screen.queryByRole("button", { name: /^Compare \(/ })).toBeNull() // one is not a comparison
  for (const t of ["Two", "Three", "Four"]) fireEvent.click(pick(t))
  expect(screen.getByRole("button", { name: "Compare (4)" })).toBeInTheDocument()
  expect(pick("Five")).toBeDisabled()
  expect(screen.getByText("You can compare up to 4 stays.")).toBeInTheDocument()
  fireEvent.click(pick("Four"))
  expect(pick("Five")).toBeEnabled()
  expect(screen.getByRole("button", { name: "Compare (3)" })).toBeInTheDocument()
})

test("Compare opens a real table with row headers and text for the cheapest", async () => {
  const f = mockApi(
    api({
      stays: five(),
      more: (u) =>
        u.includes("/lodging/compare")
          ? Response.json({
              columns: ["s1", "s2"], home_currency: "USD",
              rows: [
                { key: "title", label: "Stay", values: ["One", "Two"] },
                { key: "price_per_night", label: "Price per night", values: [14200, 18800] },
                { key: "bedrooms", label: "Bedrooms", values: [2, null] },
                { key: "votes", label: "Hearts", values: [2, 1] },
                { key: "distance_to_center_km", label: "Distance to the center (km)", values: [1.5, 3] },
                { key: "pros", label: "Pros", values: [["quiet", "pool"], ""] },
              ],
            })
          : undefined,
    }),
  )
  open()
  await card("One")
  fireEvent.click(screen.getByRole("checkbox", { name: "Compare One" }))
  fireEvent.click(screen.getByRole("checkbox", { name: "Compare Two" }))
  fireEvent.click(screen.getByRole("button", { name: "Compare (2)" }))
  const table = await screen.findByRole("table", { name: "Compare stays" })
  expect(call(f, "GET", "/lodging/compare?ids=s1%2Cs2")).toBeTruthy()
  expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Stay", "One", "Two"])
  const row = within(table).getByRole("row", { name: /Price per night/ })
  expect(within(row).getByRole("rowheader")).toHaveAttribute("scope", "row")
  expect(within(row).getByText("$142")).toBeInTheDocument()
  expect(within(row).getByText("Lowest")).toBeInTheDocument()
  expect(within(row).getByText("Cheaper than the others by $46")).toBeInTheDocument()
  expect(within(within(table).getByRole("row", { name: /Bedrooms/ })).getByText("Not set")).toBeInTheDocument()
  expect(within(within(table).getByRole("row", { name: /Distance/ })).getByText("1.5")).toBeInTheDocument()
  expect(within(within(table).getByRole("row", { name: /Pros/ })).getByText("quiet, pool")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Back to the list" }))
  expect(await card("One")).toBeInTheDocument()
})

test("compare: a plan limit from the API is shown in words", async () => {
  mockApi(api({ stays: five(), more: (u) => (u.includes("/lodging/compare") ? Response.json({ code: "limit_reached", detail: "You can compare 2 stays at once on your plan." }, { status: 402 }) : undefined) }))
  open()
  await card("One")
  for (const t of ["One", "Two", "Three"]) fireEvent.click(screen.getByRole("checkbox", { name: `Compare ${t}` }))
  fireEvent.click(screen.getByRole("button", { name: "Compare (3)" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("You can compare 2 stays at once on your plan.")
})

test("Add a stay: a pasted link is saved as typed, with the dates read from the link text only", async () => {
  const typed = "https://www.airbnb.com/rooms/123?check_in=2027-11-27&check_out=2027-12-01&utm_source=abc"
  const f = mockApi(
    api({
      stays: [],
      more: (u, i) => {
        if (u.endsWith("/lodging/parse-link")) return Response.json({ site: "airbnb", check_in: "2027-11-27", check_out: "2027-12-01", guests: null, note: "We never change your links." })
        if (u.endsWith("/trips/t1/lodging") && i?.method === "POST") return Response.json(stay("n1", "Casita"), { status: 201 })
        return undefined
      },
    }),
  )
  open()
  fireEvent.click((await screen.findAllByRole("button", { name: "Add a stay" }))[0])
  const dialog = await screen.findByRole("dialog", { name: "Add a stay" })
  expect(within(dialog).getByText("We never change your links and never load these pages.")).toBeInTheDocument()
  fireEvent.click(within(dialog).getByRole("button", { name: "Save stay" }))
  expect(await within(dialog).findByText("Paste a link.")).toBeInTheDocument()
  fireEvent.change(within(dialog).getByLabelText("Link"), { target: { value: typed } })
  fireEvent.click(within(dialog).getByRole("button", { name: "Save stay" }))
  expect(await within(dialog).findByText("Add a name for this stay.")).toBeInTheDocument()
  fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Casita" } })
  fireEvent.change(within(dialog).getByLabelText("Price per night"), { target: { value: "142.50" } })
  fireEvent.click(within(dialog).getByRole("button", { name: "Save stay" }))
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
  expect(bodyOf(f, "/trips/t1/lodging")).toEqual({
    title: "Casita", url: typed, added_via: "paste", price_per_night: { amount_minor: 14250, currency: "USD" }, check_in: "2027-11-27", check_out: "2027-12-01",
  })
  expect(bodyOf(f, "/lodging/parse-link")).toEqual({ url: typed })
  expect(f.mock.calls.every(([u]) => !String(u).includes("airbnb.com"))).toBe(true)
})

test("Add a stay: a full trip (402) shows the API's words, keeps the sheet open and keeps what was typed", async () => {
  const detail = "A trip can hold 8 saved stays on your plan. Remove one to make room, or upgrade."
  mockApi(api({ stays: [], more: (u, i) => (u.endsWith("/trips/t1/lodging") && i?.method === "POST" ? Response.json({ code: "limit_reached", detail }, { status: 402 }) : undefined) }))
  open()
  fireEvent.click((await screen.findAllByRole("button", { name: "Add a stay" }))[0])
  const dialog = await screen.findByRole("dialog", { name: "Add a stay" })
  fireEvent.click(within(dialog).getByRole("tab", { name: "Add by hand" }))
  fireEvent.change(within(dialog).getByLabelText("Link"), { target: { value: "https://example.com/stay?a=1" } })
  fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Cabin" } })
  fireEvent.change(within(dialog).getByLabelText("Price per night"), { target: { value: "99" } })
  fireEvent.click(within(dialog).getByRole("button", { name: "Save stay" }))
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(detail)
  expect(screen.getByRole("dialog", { name: "Add a stay" })).toBeInTheDocument()
  expect(within(dialog).getByLabelText("Link")).toHaveValue("https://example.com/stay?a=1")
  expect(within(dialog).getByLabelText("Name")).toHaveValue("Cabin")
  expect(within(dialog).getByLabelText("Price per night")).toHaveValue("99")
})

test("Add a stay: a failed save says what to do and keeps the sheet open", async () => {
  mockApi(api({ stays: [], more: (u, i) => (u.endsWith("/trips/t1/lodging") && i?.method === "POST" ? Response.json({ code: "validation_failed", detail: "x" }, { status: 422 }) : undefined) }))
  open()
  fireEvent.click((await screen.findAllByRole("button", { name: "Add a stay" }))[0])
  const dialog = await screen.findByRole("dialog", { name: "Add a stay" })
  fireEvent.click(within(dialog).getByRole("tab", { name: "Add by hand" }))
  fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Cabin" } })
  fireEvent.click(within(dialog).getByRole("button", { name: "Save stay" }))
  expect(await within(dialog).findByRole("alert")).toHaveTextContent("We could not save this stay. Check the link and try again.")
})

test("the paste helper from the bookmarklet opens the sheet with the page address and title, and saves nothing until the person confirms", async () => {
  const f = mockApi(api({ stays: [] }))
  open(`/trips/t1/stays?add=1&via=bookmarklet&url=${encodeURIComponent("https://www.vrbo.com/9?x=1&y=2")}&title=${encodeURIComponent("Treehouse lodge | Vrbo")}`)
  const dialog = await screen.findByRole("dialog", { name: "Add a stay" })
  expect(within(dialog).getByLabelText("Link")).toHaveValue("https://www.vrbo.com/9?x=1&y=2")
  expect(within(dialog).getByLabelText("Name")).toHaveValue("Treehouse lodge | Vrbo")
  expect(within(dialog).getByText("Filled from the page you saved. Check the name and add a price.")).toBeInTheDocument()
  expect(call(f, "POST", "/lodging")).toBeUndefined()
})

test("the bookmarklet sends only the open page's address and title to the Hermi paste helper", () => {
  const href = bookmarkletHref("https://app.hermi.test", "t 1")
  expect(href.startsWith("javascript:")).toBe(true)
  const opened = vi.fn()
  new Function("window", "location", "document", decodeURIComponent(href.slice("javascript:".length)))({ open: opened }, { href: "https://www.booking.com/hotel/cr/x.html?a=1&b=2" }, { title: "Hotel X" })
  expect(opened).toHaveBeenCalledTimes(1)
  const [url, target, features] = opened.mock.calls[0]
  const u = new URL(url)
  expect(u.origin + u.pathname).toBe("https://app.hermi.test/trips/t%201/stays")
  expect(u.searchParams.get("url")).toBe("https://www.booking.com/hotel/cr/x.html?a=1&b=2")
  expect(u.searchParams.get("title")).toBe("Hotel X")
  expect(u.searchParams.get("via")).toBe("bookmarklet")
  expect([target, features]).toEqual(["_blank", "noopener"])
})

test("offline: stays stay readable and adding is off", async () => {
  mockApi(api())
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  open()
  await card("Casita")
  expect(screen.getByRole("status")).toHaveTextContent("Offline. You can read your stays. Reconnect to add or change them.")
  expect(screen.getAllByRole("button", { name: "Add a stay" })[0]).toBeDisabled()
})

test("the brand label needs the registrable domain, so a lookalike host shows raw", () => {
  expect(brandOf("airbnb.com")).toBe("Airbnb")
  expect(brandOf("booking.co.uk")).toBe("Booking.com")
  expect(brandOf("airbnb.evil.com")).toBeUndefined()
  expect(brandOf("booking.example.com")).toBeUndefined()
})
