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
