import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { __resetAnalytics, __sink } from "../../lib/analytics"
import { bodyOf, mockApi, reset, show, type Handler } from "../onboarding/testing"
import { AgentStart } from "./AgentStart"
import { run, trip } from "./testing"

const taster = (over: Record<string, unknown> = {}) => ({ used: false, used_at: null, run_id: null, available: true, credits: 40, ...over })
const preview = (over: Record<string, unknown> = {}) => ({ kind: "deep_research", credits: 0, price: 40, taster: true, taster_used: false, balance: 12, sufficient: true, from_cache: false, ...over })
const route = { id: "rt1", trip_id: "t1", origin_codes: ["JFK"], destination_codes: ["LIS"] }

type Over = { role?: string; taster?: unknown; preview?: unknown; start?: Response; routes?: unknown[] }
const api = ({ role = "owner", taster: ta = taster(), preview: pr = preview(), start, routes = [route] }: Over = {}): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  if (u.endsWith("/v1/trips/t1")) return Response.json(trip({ my_role: role }))
  if (u.endsWith("/v1/me/agent-taster")) return Response.json(ta)
  if (u.includes("/agent-runs/preview")) return Response.json(pr)
  if (u.endsWith("/trips/t1/routes")) return Response.json(routes)
  if (u.endsWith("/trips/t1/agent-runs") && m === "POST") return start ?? Response.json(run({ id: "r9" }), { status: 202 })
  return undefined
}
const open = () => show(<AgentStart />, "/trips/:id/agents", "/trips/t1/agents")
/** The card button is disabled until the preview has loaded. */
const press = async (name: string | RegExp) => {
  const b = await screen.findByRole("button", { name })
  await waitFor(() => expect(b).toBeEnabled())
  fireEvent.click(b)
}
const sent = () => __sink.map((e) => e.event)

beforeEach(() => {
  reset("free")
  __resetAnalytics()
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("taster unused: the entry card says free once, in text and in a chip, and fires taster_offered", async () => {
  mockApi(api())
  open()
  expect(await screen.findByRole("heading", { name: "Try a deep run, free once" })).toBeInTheDocument()
  expect(screen.getByText("Free, one time")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Start free run" })).toBeInTheDocument()
  await waitFor(() => expect(sent()).toContain("taster_offered"))
})

test("taster used: the card is the normal Deep run, 40 credits action", async () => {
  mockApi(api({ taster: taster({ used: true, available: false }), preview: preview({ taster: false, taster_used: true, credits: 40 }) }))
  open()
  expect(await screen.findByRole("heading", { name: "Deep run, 40 credits" })).toBeInTheDocument()
  expect(screen.queryByText("Free, one time")).toBeNull()
  expect(sent()).not.toContain("taster_offered")
})

test("confirm shows Free taster, then starts with an idempotency key and opens the run", async () => {
  const f = mockApi(api())
  open()
  await press("Start free run")
  const dialog = await screen.findByRole("dialog")
  expect(within(dialog).getByText(/^Free taster\./)).toBeInTheDocument()
  fireEvent.click(within(dialog).getByRole("button", { name: "Start run" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/trips/t1/agents/r9"))
  const post = f.mock.calls.find(([u, i]) => String(u).endsWith("/trips/t1/agent-runs") && (i as RequestInit).method === "POST")!
  expect(new Headers((post[1] as RequestInit).headers).get("Idempotency-Key")).toBeTruthy()
  expect(bodyOf(f, "/trips/t1/agent-runs")).toEqual({ kind: "deep_research" })
  expect(__sink.find((e) => e.event === "ai_action_started")!.properties).toMatchObject({ action: "agent_run", feature: "deep_research", credits: 0, taster: true })
})

test("confirm states the cost and what is left for a paid run", async () => {
  mockApi(api({ taster: taster({ available: false, used: true }), preview: preview({ taster: false, credits: 40, balance: 52 }) }))
  open()
  await press("Plan a deep run")
  expect(await screen.findByText("Costs 40 credits. You have 52, so 12 left.")).toBeInTheDocument()
})

test("not enough credits: the confirm offers See plans and cannot start", async () => {
  mockApi(api({ taster: taster({ available: false, used: true }), preview: preview({ taster: false, credits: 40, balance: 12, sufficient: false }) }))
  open()
  await press("Plan a deep run")
  const dialog = await screen.findByRole("dialog")
  expect(within(dialog).getByText("This costs 40 credits and you have 12.")).toBeInTheDocument()
  expect(within(dialog).queryByRole("button", { name: "Start run" })).toBeNull()
  expect(within(dialog).getByRole("link", { name: "See plans" })).toBeInTheDocument()
})

test("a second start while one runs shows the run already active error with a link to it", async () => {
  mockApi(api({ start: Response.json({ code: "run_already_active", detail: "An agent run is already in progress.", active_run_id: "r1" }, { status: 409 }) }))
  open()
  await press("Start free run")
  fireEvent.click(await screen.findByRole("button", { name: "Start run" }))
  const alert = await screen.findByRole("alert")
  expect(alert).toHaveTextContent("A run is already in progress for your account. Wait for it to finish or stop it.")
  expect(within(alert).getByRole("link", { name: "View the run in progress" })).toHaveAttribute("href", "/trips/t1/agents/r1")
  expect(screen.queryByRole("dialog")).toBeNull()
})

test("402 shows the credits message", async () => {
  mockApi(api({ start: Response.json({ code: "insufficient_credits", detail: "no" }, { status: 402 }) }))
  open()
  await press("Start free run")
  fireEvent.click(await screen.findByRole("button", { name: "Start run" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("You do not have enough credits for this run.")
})

test("fare hunt sends the chosen routes", async () => {
  const f = mockApi(api({ preview: preview({ kind: "fare_hunt", taster: false, credits: 40, balance: 80 }) }))
  open()
  fireEvent.click(await screen.findByRole("tab", { name: "Fare hunt" }))
  await screen.findByRole("checkbox", { name: /JFK to LIS/ })
  await press(/^(Plan a deep run|Start free run)$/)
  fireEvent.click(await screen.findByRole("button", { name: "Start run" }))
  await waitFor(() => expect(bodyOf(f, "/trips/t1/agent-runs")).toEqual({ kind: "fare_hunt", route_ids: ["rt1"] }))
})

test("offline disables the start and says AI needs a connection", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api())
  open()
  expect(await screen.findByText("AI needs a connection.")).toBeInTheDocument()
  expect(await screen.findByRole("button", { name: /^(Start free run|Plan a deep run)$/ })).toBeDisabled()
})

test("a viewer cannot start a run", async () => {
  mockApi(api({ role: "viewer" }))
  open()
  expect(await screen.findByText("Only editors can start a deep run on this trip.")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Start free run" })).toBeNull()
})

test("a failed preview shows the error state", async () => {
  mockApi((u, i) => (u.includes("/agent-runs/preview") ? Response.json({}, { status: 500 }) : api()(u, i)))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 4000 })).toHaveTextContent(/Try again|could not|wrong/i)
})

// --- WF-054: consent gate and AI off ---

const consents = (granted: boolean | null, inner: Handler, put: Response = Response.json({ kind: "ai_processing", version: "1", granted: true, accepted_at: "2027-01-01T00:00:00Z" })): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  if (u.endsWith("/v1/me/consents") && m === "GET") return Response.json(granted === null ? [] : [{ kind: "ai_processing", version: "1", granted, accepted_at: "2027-01-01T00:00:00Z" }])
  if (u.endsWith("/v1/me/consents/ai_processing") && m === "PUT") return put
  return inner(u, i)
}
const starts = (f: ReturnType<typeof mockApi>) => f.mock.calls.filter(([u, i]) => String(u).endsWith("/trips/t1/agent-runs") && (i as RequestInit).method === "POST")

test("no consent yet: the gate shows before the confirm, Allow stores it and the confirm follows", async () => {
  const f = mockApi(consents(null, api()))
  open()
  await screen.findByRole("heading", { name: "Try a deep run, free once" })
  await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).endsWith("/v1/me/consents"))).toBe(true))
  await new Promise((r) => setTimeout(r, 20))
  await press("Start free run")
  const gate = await screen.findByRole("dialog", { name: "Allow AI on your trips?" })
  expect(within(gate).getByText("Your trip details and questions are sent to Anthropic to generate suggestions.")).toBeInTheDocument()
  expect(sent()).toContain("ai_consent_shown")
  fireEvent.click(within(gate).getByRole("button", { name: "Allow" }))
  expect(await screen.findByRole("dialog", { name: "Start this run?" })).toBeInTheDocument()
  expect(bodyOf(f, "/v1/me/consents/ai_processing")).toEqual({ version: "1", granted: true })
  expect(sent()).toContain("ai_consent_granted")
  expect(starts(f)).toHaveLength(0)
})

test("Not now leaves the screen usable and starts nothing", async () => {
  const f = mockApi(consents(false, api()))
  open()
  await screen.findByRole("heading", { name: "Try a deep run, free once" })
  await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).endsWith("/v1/me/consents"))).toBe(true))
  await new Promise((r) => setTimeout(r, 20))
  await press("Start free run")
  fireEvent.click(within(await screen.findByRole("dialog", { name: "Allow AI on your trips?" })).getByRole("button", { name: "Not now" }))
  expect(screen.queryByRole("dialog")).toBeNull()
  expect(sent()).toContain("ai_consent_declined")
  expect(f.mock.calls.some(([u, i]) => String(u).includes("/consents/") && (i as RequestInit).method === "PUT")).toBe(false)
  expect(starts(f)).toHaveLength(0)
  expect(screen.getByRole("button", { name: "Start free run" })).toBeEnabled()
  expect(screen.getByRole("tab", { name: "Fare hunt" })).toBeInTheDocument()
})

test("a 403 ai_consent_required opens the gate and Allow retries the same start with the same key", async () => {
  const keys: (string | null)[] = []
  const inner: Handler = (u, i) => {
    if (u.endsWith("/trips/t1/agent-runs") && i?.method === "POST") {
      const n = keys.push(new Headers(i.headers).get("Idempotency-Key"))
      return n === 1 ? Response.json({ code: "ai_consent_required", detail: "Allow AI processing to use this." }, { status: 403 }) : Response.json(run({ id: "r9" }), { status: 202 })
    }
    return api()(u, i)
  }
  mockApi(inner)
  open()
  await press("Start free run")
  fireEvent.click(await screen.findByRole("button", { name: "Start run" }))
  const gate = await screen.findByRole("dialog", { name: "Allow AI on your trips?" })
  expect(screen.getByRole("alert")).toHaveTextContent("AI is off until you allow it. Everything else still works.")
  vi.stubGlobal("fetch", vi.fn(async (u: string | URL | Request, i?: RequestInit) => consents(false, inner)(String(u), i) ?? new Response("{}", { status: 404 })))
  fireEvent.click(within(gate).getByRole("button", { name: "Allow" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/trips/t1/agents/r9"))
  expect(keys).toHaveLength(2)
  expect(keys[0]).toBeTruthy()
  expect(keys[1]).toBe(keys[0])
})

test("a failed save keeps the gate open with an error", async () => {
  mockApi(consents(false, api(), Response.json({ code: "internal_error" }, { status: 500 })))
  open()
  await screen.findByRole("heading", { name: "Try a deep run, free once" })
  await new Promise((r) => setTimeout(r, 20))
  await press("Start free run")
  const gate = await screen.findByRole("dialog", { name: "Allow AI on your trips?" })
  fireEvent.click(within(gate).getByRole("button", { name: "Allow" }))
  expect(await within(gate).findByText("We could not save your choice. Try again.")).toBeInTheDocument()
  expect(screen.getByRole("dialog", { name: "Allow AI on your trips?" })).toBeInTheDocument()
})

test("AI off for this trip: the notice replaces the start card, for an editor and for the owner", async () => {
  mockApi((u, i) => (u.endsWith("/v1/trips/t1") ? Response.json(trip({ my_role: "editor", ai_enabled: false })) : api()(u, i)))
  const { unmount } = open()
  expect(await screen.findByText("AI is off for this trip.")).toBeInTheDocument()
  expect(screen.getByText("Ask the trip owner to turn it on.")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /Start free run|Plan a deep run/ })).toBeNull()
  unmount()
  mockApi((u, i) => (u.endsWith("/v1/trips/t1") ? Response.json(trip({ my_role: "owner", ai_enabled: false })) : api()(u, i)))
  open()
  expect(await screen.findByRole("button", { name: "Turn on AI for this trip" })).toBeInTheDocument()
})

test("a 403 ai_disabled_for_trip from the API says AI is off for this trip", async () => {
  mockApi(api({ start: Response.json({ code: "ai_disabled_for_trip", detail: "AI is turned off for this trip." }, { status: 403 }) }))
  open()
  await press("Start free run")
  fireEvent.click(await screen.findByRole("button", { name: "Start run" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("AI is off for this trip.")
})

test("AI off for this trip: a viewer sees the notice too", async () => {
  mockApi((u, i) => (u.endsWith("/v1/trips/t1") ? Response.json(trip({ my_role: "viewer", ai_enabled: false })) : api()(u, i)))
  open()
  expect(await screen.findByText("AI is off for this trip.")).toBeInTheDocument()
  expect(screen.getByText("Ask the trip owner to turn it on.")).toBeInTheDocument()
})
