import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { __resetAnalytics, __sink } from "../../lib/analytics"
import { trip } from "../agents/testing"
import { bodyOf, mockApi, reset, show, type Handler } from "../onboarding/testing"
import { AiActionPage } from "./AiActionPage"

const credits = (over: Record<string, unknown> = {}) => ({
  available: 27, own: 27, pool: 0, payer: "own", blocked: false, version: 3, total: 27, monthly: 27, trip_pass: 0, purchased: 0, next_monthly_grant_at: null, ...over,
})
const receipt = (over: Record<string, unknown> = {}) => ({ action: "explain", reserved: 1, charged: 1, from_cache: false, balance_after: 26, reservation_id: "res1", ...over })
const granted = (g: boolean) => [{ kind: "ai_processing", version: "1", granted: g, accepted_at: "2027-01-01T00:00:00Z" }]
const item = (n: number, over: Record<string, unknown> = {}) => ({
  title: `Stop ${n}`, day: "2027-05-02", start_time: "09:00", end_time: "10:00", category: "sights", status: "idea", location_name: `Place ${n}`,
  notes: "", saved_place_id: null, verify: false, source: "ai_draft", ...over,
})
const explained = (over: Record<string, unknown> = {}) => ({
  answer: "Alfama is hilly and best on foot.", confidence: "high", needs_source_check: false, sources: [], label: "AI suggestion", run_id: "run1", credits: receipt(), ...over,
})
const packed = { items: [{ label: "Rain jacket", group: "clothing", qty: 1, reason: "Showers in May" }, { label: "Passport", group: "documents", qty: null, reason: null }], label: "x", run_id: "run2", credits: receipt() }
const dayDraft = (items = [item(1), item(2, { verify: true })]) => ({ day: "2027-05-02", title: "Old town", items, rationale: "Close together.", label: "x", run_id: "run3", credits: receipt({ action: "draft_day" }) })
const tripJob = (n = 2) => ({
  id: "run4", kind: "draft_trip", status: "done", error_code: null, credits: receipt({ action: "draft_trip", reserved: 4, charged: 4, balance_after: 23 }),
  result: { days: Array.from({ length: n }, (_, d) => ({ day: `2027-05-0${d + 1}`, title: `Day ${d + 1}`, rationale: "", items: [item(d * 10 + 1, { day: `2027-05-0${d + 1}` })] })), overview: "A slow week.", label: "x" },
})

type Over = {
  role?: string
  aiOn?: boolean
  credits?: Response
  consent?: boolean
  post?: (path: string, body: unknown) => Response | Promise<Response>
  dates?: boolean
}
const api = ({ role = "owner", aiOn = true, credits: c, consent = true, post, dates = true }: Over = {}): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  if (u.endsWith("/v1/trips/t1")) return Response.json(trip({ my_role: role, ai_enabled: aiOn, ...(dates ? { start_date: "2027-05-01", end_date: "2027-05-05" } : {}) }))
  if (u.includes("/v1/me/credits")) return c?.clone() ?? Response.json(credits())
  if (u.endsWith("/v1/me/consents") && m === "GET") return Response.json(granted(consent))
  if (u.endsWith("/v1/me/consents/ai_processing") && m === "PUT") return Response.json(granted(true)[0])
  if (m === "POST" && post) {
    const path = u.split("/v1/trips/t1/")[1] ?? u
    return post(path, i?.body ? JSON.parse(String(i.body)) : undefined)
  }
  return undefined
}
const open = (action: string, query = "") => show(<AiActionPage />, "/trips/:id/ai/:action", `/trips/t1/ai/${action}${query}`)
const posts = (f: ReturnType<typeof mockApi>, tail: string) => f.mock.calls.filter(([u, i]) => String(u).endsWith(tail) && (i as RequestInit | undefined)?.method === "POST")
const sent = () => __sink.map((e) => e.event)
/** The button is enabled once the trip is in; the short wait lets the consent answer settle. */
const ready = async (name: RegExp | string) => {
  const b = await screen.findByRole("button", { name })
  await waitFor(() => expect(b).toBeEnabled())
  await new Promise((r) => setTimeout(r, 30))
  return b
}
const problem = (status: number, body: Record<string, unknown>, headers: Record<string, string> = {}) =>
  Response.json(body, { status, headers: { "Content-Type": "application/problem+json", ...headers } })
const ask = async (text = "Is Alfama hilly?") => {
  fireEvent.change(await screen.findByLabelText("Your question"), { target: { value: text } })
  fireEvent.click(await ready("Ask, costs 1 credit"))
}

beforeEach(() => {
  reset("free")
  __resetAnalytics()
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

// ---- explain ----

test("explain: the chip shows the price and the pool before anything is sent", async () => {
  mockApi(api({ credits: Response.json(credits({ available: 40, own: 0, pool: 40, payer: "trip_pass" })) }))
  open("explain")
  const b = await screen.findByRole("button", { name: /^Ask, costs 1 credit/ })
  expect(within(b).getByText("Trip Pass credits")).toBeInTheDocument()
  expect(await screen.findByText(/40 credits left\. Trip Pass credits/)).toBeInTheDocument()
})

test("explain empty: no question, no ask", async () => {
  mockApi(api())
  open("explain")
  expect(await screen.findByRole("button", { name: "Ask, costs 1 credit" })).toBeDisabled()
})

test("explain: sends the question with a key, shows the answer, the label, what it cost and thumbs", async () => {
  const f = mockApi(api({ post: () => Response.json(explained()) }))
  open("explain")
  await ask()
  expect(await screen.findByText("Alfama is hilly and best on foot.")).toBeInTheDocument()
  expect(bodyOf(f, "/ai/explain")).toEqual({ question: "Is Alfama hilly?" })
  expect(new Headers((posts(f, "/ai/explain")[0]![1] as RequestInit).headers).get("Idempotency-Key")).toBeTruthy()
  expect(screen.getByText("AI suggestion, check details before booking")).toBeInTheDocument()
  expect(screen.getByText("Used 1 credit. 26 left.")).toBeInTheDocument()
  expect(screen.getByRole("group", { name: "Was this helpful?" })).toBeInTheDocument()
  expect(sent()).toEqual(expect.arrayContaining(["ai_action_started", "ai_action_completed"]))
})

test("explain: a free repeat says so and charges nothing", async () => {
  mockApi(api({ post: () => Response.json(explained({ credits: receipt({ reserved: 0, charged: 0, from_cache: true, reservation_id: null }) })) }))
  open("explain")
  await ask()
  expect(await screen.findByText("Free repeat, no credits used.")).toBeInTheDocument()
  expect(screen.queryByText(/Used 1 credit/)).toBeNull()
})

test("explain: the item or place in the address is sent as the context", async () => {
  const f = mockApi(api({ post: () => Response.json(explained()) }))
  open("explain", "?item=i1")
  await ask()
  await screen.findByText("Alfama is hilly and best on foot.")
  expect(bodyOf(f, "/ai/explain")).toEqual({ question: "Is Alfama hilly?", context: { item_id: "i1" } })
})

test("explain loading: a status says it is working and the button is busy", async () => {
  mockApi(api({ post: () => new Promise<Response>(() => undefined) }))
  open("explain")
  await ask()
  expect(await screen.findByText("Working on your answer")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: /^Ask/ })).toHaveAttribute("aria-busy", "true")
})

test("explain error: says nothing was charged, and Try again asks with a fresh key", async () => {
  let n = 0
  const f = mockApi(api({ post: () => (n++ === 0 ? problem(502, { code: "ai_failed" }) : Response.json(explained())) }))
  open("explain")
  await ask()
  expect(await screen.findByText("That did not work, and you were not charged. Try again.")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Try again" }))
  expect(await screen.findByText("Alfama is hilly and best on foot.")).toBeInTheDocument()
  const keys = posts(f, "/ai/explain").map(([, i]) => new Headers((i as RequestInit).headers).get("Idempotency-Key"))
  expect(new Set(keys).size).toBe(2)
})

test("explain limit: a rate limit says how long to wait", async () => {
  mockApi(api({ post: () => problem(429, { code: "rate_limited" }, { "Retry-After": "12" }) }))
  open("explain")
  await ask()
  expect(await screen.findByText(/Slow down a little\. Try again in a few seconds\./)).toBeInTheDocument()
  expect(screen.getByText(/12/)).toBeInTheDocument()
})

test("explain limit: the paused ceiling shows the server sentence", async () => {
  mockApi(api({ post: () => problem(429, { code: "provider_budget_exhausted", detail: "AI is paused until 1 Nov. Saved data and cached fares still work." }) }))
  open("explain")
  await ask()
  expect(await screen.findByText("AI is paused until 1 Nov. Saved data and cached fares still work.")).toBeInTheDocument()
})

test("explain limit: out of credits names the shortfall and links to plans", async () => {
  mockApi(api({ credits: Response.json(credits({ available: 0, own: 0 })), post: () => problem(402, { code: "insufficient_credits" }) }))
  open("explain")
  await ask()
  expect(await screen.findByText("You do not have enough credits for this.")).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "See plans" })).toHaveAttribute("href", "/account")
})

test("explain offline: the button is disabled and the line says AI needs a connection", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api())
  open("explain")
  expect(await screen.findByText("AI needs a connection.")).toBeInTheDocument()
  expect(await screen.findByRole("button", { name: "Ask, costs 1 credit" })).toBeDisabled()
})

test("AI off for the trip and viewers: no form, and the reason", async () => {
  mockApi(api({ aiOn: false }))
  open("explain")
  expect(await screen.findByText("AI is off for this trip.")).toBeInTheDocument()
  expect(screen.queryByLabelText("Your question")).toBeNull()
  cleanup()
  mockApi(api({ role: "viewer" }))
  open("explain")
  expect(await screen.findByText("Viewers cannot run AI on this trip. Ask an editor.")).toBeInTheDocument()
  expect(screen.queryByLabelText("Your question")).toBeNull()
})

test("consent: the gate opens on first use and Allow runs the question", async () => {
  const f = mockApi(api({ consent: false, post: () => Response.json(explained()) }))
  open("explain")
  await ask()
  const gate = await screen.findByRole("dialog", { name: "Allow AI on your trips?" })
  expect(posts(f, "/ai/explain")).toHaveLength(0)
  fireEvent.click(within(gate).getByRole("button", { name: "Allow" }))
  expect(await screen.findByText("Alfama is hilly and best on foot.")).toBeInTheDocument()
  expect(posts(f, "/ai/explain")).toHaveLength(1)
})

test("a consent refusal from the API offers Allow AI", async () => {
  mockApi(api({ post: () => problem(403, { code: "ai_consent_required" }) }))
  open("explain")
  await ask()
  expect(await screen.findByText("AI is off until you allow it. Everything else still works.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Allow AI" })).toBeInTheDocument()
})

// ---- packing list ----

test("packing: groups, the checklist, copy and the receipt", async () => {
  const f = mockApi(api({ post: () => Response.json(packed) }))
  const write = vi.fn().mockResolvedValue(undefined)
  Object.assign(navigator, { clipboard: { writeText: write } })
  open("packing")
  fireEvent.change(await screen.findByLabelText("Anything to plan around"), { target: { value: "hiking" } })
  fireEvent.click(await ready("Suggest a packing list, costs 1 credit"))
  const clothing = await screen.findByRole("group", { name: "Clothing" })
  expect(within(clothing).getByRole("checkbox", { name: /Rain jacket/ })).not.toBeChecked()
  fireEvent.click(within(clothing).getByRole("checkbox", { name: /Rain jacket/ }))
  expect(within(clothing).getByRole("checkbox", { name: /Rain jacket/ })).toBeChecked()
  expect(screen.getByRole("group", { name: "Documents" })).toBeInTheDocument()
  expect(bodyOf(f, "/ai/packing-list")).toEqual({ preferences: "hiking" })
  expect(screen.getByText("Used 1 credit. 26 left.")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Copy list" }))
  await waitFor(() => expect(write).toHaveBeenCalledWith("- Rain jacket\n- Passport"))
  expect(await screen.findByText("List copied.")).toBeInTheDocument()
})

test("packing empty and error states", async () => {
  mockApi(api({ post: () => Response.json({ ...packed, items: [] }) }))
  open("packing")
  fireEvent.click(await ready("Suggest a packing list, costs 1 credit"))
  expect(await screen.findByText(/We could not make a list from this trip yet/)).toBeInTheDocument()
  cleanup()
  mockApi(api({ post: () => problem(502, { code: "ai_failed" }) }))
  open("packing")
  fireEvent.click(await ready("Suggest a packing list, costs 1 credit"))
  expect(await screen.findByText("That did not work, and you were not charged. Try again.")).toBeInTheDocument()
})

test("packing loading and offline", async () => {
  mockApi(api({ post: () => new Promise<Response>(() => undefined) }))
  open("packing")
  fireEvent.click(await ready("Suggest a packing list, costs 1 credit"))
  expect(await screen.findByText("Writing your packing list")).toBeInTheDocument()
  cleanup()
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api())
  open("packing")
  expect(await screen.findByText("AI needs a connection.")).toBeInTheDocument()
  expect(await screen.findByRole("button", { name: /Suggest a packing list/ })).toBeDisabled()
})

// ---- draft day ----

test("draft day: preview, nothing saved until Accept all, then one bulk post with source ai_draft", async () => {
  const f = mockApi(api({ post: (p) => (p.endsWith("ai/draft-day") ? Response.json(dayDraft()) : Response.json([], { status: 201 })) }))
  open("day", "?day=2027-05-02")
  fireEvent.click(await ready("Draft, costs 1 credit"))
  expect(await screen.findByText("Stop 1")).toBeInTheDocument()
  expect(bodyOf(f, "/ai/draft-day")).toEqual({ day: "2027-05-02" })
  expect(screen.getByText("Check hours before you go")).toBeInTheDocument()
  expect(posts(f, "/items/bulk")).toHaveLength(0)
  fireEvent.click(screen.getByRole("button", { name: "Accept all" }))
  expect(await screen.findByText("Added 2 items to your plan.")).toBeInTheDocument()
  const body = bodyOf(f, "/items/bulk")
  expect(body.source).toBe("ai_draft")
  expect(body.items).toHaveLength(2)
  expect(body.items[0]).toMatchObject({ title: "Stop 1", day: "2027-05-02", start_time: "09:00", category: "sights" })
  expect(screen.getByRole("link", { name: "Open the plan" })).toHaveAttribute("href", "/trips/t1/plan")
  expect(sent().filter((e) => e === "itinerary_item_added")).toHaveLength(2)
})

test("draft day: pick items and add only those", async () => {
  const f = mockApi(api({ post: (p) => (p.endsWith("ai/draft-day") ? Response.json(dayDraft()) : Response.json([], { status: 201 })) }))
  open("day")
  fireEvent.click(await ready("Draft, costs 1 credit"))
  const add = await screen.findByRole("button", { name: "Add picked (0)" })
  expect(add).toBeDisabled()
  fireEvent.click(screen.getByRole("checkbox", { name: /Stop 2/ }))
  fireEvent.click(screen.getByRole("button", { name: "Add picked (1)" }))
  expect(await screen.findByText("Added 1 item to your plan.")).toBeInTheDocument()
  expect(bodyOf(f, "/items/bulk").items.map((i: { title: string }) => i.title)).toEqual(["Stop 2"])
})

test("draft day: a save that fails keeps the draft and says nothing changed", async () => {
  mockApi(api({ post: (p) => (p.endsWith("ai/draft-day") ? Response.json(dayDraft()) : problem(500, { code: "internal_error" })) }))
  open("day")
  fireEvent.click(await ready("Draft, costs 1 credit"))
  fireEvent.click(await screen.findByRole("button", { name: "Accept all" }))
  expect(await screen.findByText(/We could not add these to your plan\. Nothing was changed/)).toBeInTheDocument()
  expect(screen.getByText("Stop 1")).toBeInTheDocument()
})

test("draft day: a free repeat is stated", async () => {
  mockApi(api({ post: () => Response.json({ ...dayDraft(), credits: receipt({ reserved: 0, charged: 0, from_cache: true }) }) }))
  open("day")
  fireEvent.click(await ready("Draft, costs 1 credit"))
  expect(await screen.findByText("Free repeat, no credits used.")).toBeInTheDocument()
})

test("draft day: a trip without dates asks for them", async () => {
  mockApi(api({ dates: false }))
  open("day")
  expect(await screen.findByText(/Add trip dates first/)).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Add dates" })).toHaveAttribute("href", "/trips/t1/edit")
})

test("draft day: loading, error and offline", async () => {
  mockApi(api({ post: () => new Promise<Response>(() => undefined) }))
  open("day")
  fireEvent.click(await ready("Draft, costs 1 credit"))
  expect(await screen.findByText("Drafting your day")).toBeInTheDocument()
  cleanup()
  mockApi(api({ post: () => problem(422, { code: "ai_refused" }) }))
  open("day")
  fireEvent.click(await ready("Draft, costs 1 credit"))
  expect(await screen.findByText("That did not work, and you were not charged. Try again.")).toBeInTheDocument()
  cleanup()
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api())
  open("day")
  expect(await screen.findByText("AI needs a connection.")).toBeInTheDocument()
  expect(await screen.findByRole("button", { name: /^Draft, costs/ })).toBeDisabled()
})

// ---- draft trip, and the blurred day one ----

test("draft trip: days in the preview, Accept all saves every item", async () => {
  const f = mockApi(api({ post: (p) => (p.endsWith("ai/draft-trip") ? Response.json(tripJob(), { status: 202 }) : Response.json([], { status: 201 })) }))
  open("trip")
  fireEvent.click(await ready("Draft, costs 4 credits"))
  expect(await screen.findByText("A slow week.")).toBeInTheDocument()
  expect(screen.getByText(/Day 1/)).toBeInTheDocument()
  expect(screen.getByText(/Day 2/)).toBeInTheDocument()
  expect(bodyOf(f, "/ai/draft-trip")).toEqual({})
  expect(screen.getByText("Used 4 credits. 23 left.")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Accept all" }))
  expect(await screen.findByText("Added 2 items to your plan.")).toBeInTheDocument()
})

test("draft trip: a long draft is saved in blocks of 50", async () => {
  const many = tripJob(1)
  many.result.days[0]!.items = Array.from({ length: 60 }, (_, n) => item(n))
  const f = mockApi(api({ post: (p) => (p.endsWith("ai/draft-trip") ? Response.json(many, { status: 202 }) : Response.json([], { status: 201 })) }))
  open("trip")
  fireEvent.click(await ready("Draft, costs 4 credits"))
  fireEvent.click(await screen.findByRole("button", { name: "Accept all" }))
  expect(await screen.findByText("Added 60 items to your plan.")).toBeInTheDocument()
  expect(posts(f, "/items/bulk")).toHaveLength(2)
})

test("draft trip: a later block that fails says how many were added", async () => {
  const many = tripJob(1)
  many.result.days[0]!.items = Array.from({ length: 60 }, (_, n) => item(n))
  let blocks = 0
  mockApi(api({ post: (p) => (p.endsWith("ai/draft-trip") ? Response.json(many, { status: 202 }) : blocks++ === 0 ? Response.json([], { status: 201 }) : problem(500, {})) }))
  open("trip")
  fireEvent.click(await ready("Draft, costs 4 credits"))
  fireEvent.click(await screen.findByRole("button", { name: "Accept all" }))
  expect(await screen.findByText(/Added 50 items, then something went wrong/)).toBeInTheDocument()
})

test("draft trip at 0 credits: day one is blurred behind the out of credits offer, with the free path and no purchase", async () => {
  const f = mockApi(api({ credits: Response.json(credits({ available: 0, own: 0 })) }))
  open("trip")
  const over = await screen.findByText("Add credits and Hermi drafts your days here.")
  const preview = over.closest(".ai-locked__card")!.querySelector(".ai-locked__preview")!
  expect(preview).toHaveAttribute("aria-hidden", "true")
  expect(over.closest("[aria-hidden]")).toBeNull()
  expect(screen.getByRole("heading", { name: "You are out of credits" })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Write it myself" })).toHaveAttribute("href", "/trips/t1/plan")
  expect(screen.getByText("You can add credits or upgrade in the iOS app.")).toBeInTheDocument()
  expect(screen.queryByText(/\$\d/)).toBeNull()
  expect(screen.getByRole("button", { name: /^Draft, costs 4 credits/ })).toBeEnabled()
  expect(posts(f, "/ai/draft-trip")).toHaveLength(0)
  expect(__sink.find((e) => e.event === "paywall_viewed")!.properties).toMatchObject({ placement: "credits" })
})

test("draft day: a 402 from the API shows the same blurred day one", async () => {
  mockApi(api({ post: () => problem(402, { code: "insufficient_credits" }) }))
  open("day")
  fireEvent.click(await ready("Draft, costs 1 credit"))
  expect(await screen.findByText("Add credits and Hermi drafts your days here.")).toBeInTheDocument()
  expect(screen.getByRole("heading", { name: "You are out of credits" })).toBeInTheDocument()
})

test("a refund debt is not the paywall: the blocked line shows and no offer", async () => {
  mockApi(api({ credits: Response.json(credits({ available: 0, blocked: true })) }))
  open("trip")
  expect(await screen.findByText(/A refund put your credits below zero/)).toBeInTheDocument()
  expect(screen.queryByRole("heading", { name: "You are out of credits" })).toBeNull()
})

test("draft trip at 0 credits: the button can still be pressed, and a 402 keeps the blurred day one", async () => {
  const f = mockApi(api({ credits: Response.json(credits({ available: 0, own: 0 })), post: () => problem(402, { code: "insufficient_credits" }) }))
  open("trip")
  fireEvent.click(await ready("Draft, costs 4 credits"))
  await waitFor(() => expect(posts(f, "ai/draft-trip")).toHaveLength(1))
  expect(await screen.findByText("Add credits and Hermi drafts your days here.")).toBeInTheDocument()
  expect(screen.queryByText("That did not work, and you were not charged. Try again.")).toBeNull()
})

test("a charge of 0 that is not a repeat does not say free repeat", async () => {
  mockApi(api({ post: () => Response.json(explained({ credits: receipt({ reserved: 1, charged: 0, from_cache: false }) })) }))
  open("explain")
  await ask()
  await screen.findByText("Alfama is hilly and best on foot.")
  expect(screen.queryByText("Free repeat, no credits used.")).toBeNull()
})

test("a draft that costs 1 credit says credit in the singular", async () => {
  mockApi(api())
  open("day")
  expect(await screen.findByRole("button", { name: "Draft, costs 1 credit" })).toBeInTheDocument()
})
