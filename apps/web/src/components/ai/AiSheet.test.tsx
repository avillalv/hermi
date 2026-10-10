import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { __resetAnalytics, __sink } from "../../lib/analytics"
import { trip } from "../../routes/agents/testing"
import { bodyOf, mockApi, reset, show, type Handler } from "../../routes/onboarding/testing"
import { AiSheet, type SheetAction } from "./index"

const credits = (over: Record<string, unknown> = {}) => ({
  available: 27, own: 27, pool: 0, payer: "own", blocked: false, version: 3, price: 1,
  total: 27, monthly: 27, trip_pass: 0, purchased: 0, next_monthly_grant_at: null, ...over,
})
const taster = { used: true, used_at: null, run_id: null, available: false, credits: 40 }
const granted = (g: boolean) => [{ kind: "ai_processing", version: "1", granted: g, accepted_at: "2027-01-01T00:00:00Z" }]

type Over = { role?: string; aiOn?: boolean; credits?: Response; consent?: boolean; taster?: unknown }
const api = ({ role = "owner", aiOn = true, credits: c, consent = true, taster: ta = taster }: Over = {}): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  if (u.endsWith("/v1/trips/t1")) return Response.json(trip({ my_role: role, ai_enabled: aiOn }))
  if (u.includes("/v1/me/credits")) return c ?? Response.json(credits())
  if (u.endsWith("/v1/me/consents") && m === "GET") return Response.json(granted(consent))
  if (u.endsWith("/v1/me/consents/ai_processing") && m === "PUT") return Response.json(granted(true)[0])
  if (u.endsWith("/v1/me/agent-taster")) return Response.json(ta)
  return undefined
}
const open = (onRun: (a: SheetAction) => unknown = vi.fn(), onClose = vi.fn()) =>
  show(<AiSheet tripId="t1" onClose={onClose} onRun={onRun as never} />, "/trips/:id/ai", "/trips/t1/ai")
const row = (name: RegExp | string) => screen.findByRole("button", { name })
const sent = () => __sink.map((e) => e.event)
/** The consent answer is in once its request has been made and settled. */
const consentRead = async (f: ReturnType<typeof mockApi>) => {
  await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).endsWith("/v1/me/consents"))).toBe(true))
  await new Promise((res) => setTimeout(res, 20))
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

test("loading: the sheet is there and no row is yet", () => {
  mockApi(() => new Promise<Response>(() => undefined) as never)
  open()
  expect(screen.getByRole("dialog", { name: "Plan with AI" })).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /Explain/ })).toBeNull()
})

test("rows show the table price and fire ai_sheet_opened", async () => {
  mockApi(api())
  open()
  expect(await row("Draft the trip, costs 4 credits")).toBeEnabled()
  expect(screen.getByRole("button", { name: "Draft this day, costs 1 credit" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Research a question, costs 8 credits" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Explain, costs 1 credit" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Suggest a packing list, costs 1 credit" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Deep agent run, costs 40 credits. You have 27" })).toBeInTheDocument()
  expect(screen.getAllByText("8 credits from shared cache").length).toBeGreaterThan(0)
  expect(sent()).toContain("ai_sheet_opened")
})

test("the research row says 1 credit in the singular and the agent row says 8 credits", async () => {
  mockApi(api())
  open()
  const r = await row(/Research a question/)
  expect(within(r).getByText("1 credit from shared cache")).toBeInTheDocument()
  expect(within(screen.getByRole("button", { name: /Deep agent run/ })).getByText("8 credits from shared cache")).toBeInTheDocument()
})

test("the confirm button names the action, and its accessible name starts with the visible text", async () => {
  mockApi(api())
  open()
  fireEvent.click(await row("Research a question, costs 8 credits"))
  const confirm = await screen.findByRole("group", { name: "Research a question?" })
  const start = within(confirm).getByRole("button", { name: "Start research, costs 8 credits" })
  expect(start.textContent).toMatch(/^Start research/)
})

test("the balance pill shows the number and the pool that pays", async () => {
  mockApi(api())
  open()
  const pill = await screen.findByRole("link", { name: "Balance, 27 credits left. Subscription and credits" })
  expect(within(pill).getByText("Your credits")).toBeInTheDocument()
})

test("a Trip Pass pool is named on the pill and the chips, and still counts", async () => {
  mockApi(api({ credits: Response.json(credits({ available: 40, own: 0, pool: 40, payer: "trip_pass" })) }))
  open()
  const pill = await screen.findByRole("link", { name: /Balance, 40 credits left/ })
  expect(within(pill).getByText("Trip Pass credits")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Draft the trip, costs 4 credits. Trip Pass credits" })).toBeEnabled()
})

test("error: says what happened and offers a retry", async () => {
  mockApi(api({ credits: Response.json({ code: "internal_error" }, { status: 500 }) }))
  open()
  expect(await screen.findByText("We could not load your credits. Try again.", {}, { timeout: 3000 })).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /Explain/ })).toBeNull()
})

test("offline: rows are disabled and the line says AI needs a connection", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api())
  open()
  expect(await screen.findByText("AI needs a connection.")).toBeInTheDocument()
  expect(await row("Explain, costs 1 credit")).toBeDisabled()
})

test("AI off for the trip: rows are disabled and the owner can turn it on", async () => {
  mockApi(api({ aiOn: false }))
  open()
  expect(await screen.findByText("AI is off for this trip.", { selector: "strong" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Turn on AI for this trip" })).toBeInTheDocument()
  expect(await row("Explain, costs 1 credit")).toBeDisabled()
})

test("viewer: rows are disabled with the reason", async () => {
  mockApi(api({ role: "viewer" }))
  open()
  expect(await screen.findByText("Viewers cannot run AI on this trip. Ask an editor.")).toBeInTheDocument()
  expect(await row("Explain, costs 1 credit")).toBeDisabled()
})

test("a refund debt blocks the rows and says why", async () => {
  mockApi(api({ credits: Response.json(credits({ blocked: true })) }))
  open()
  expect(await screen.findByText(/A refund put your credits below zero/)).toBeInTheDocument()
  expect(await row("Explain, costs 1 credit")).toBeDisabled()
})

test("insufficient: the chip warns, and choosing the row runs nothing and links to plans", async () => {
  const onRun = vi.fn()
  mockApi(api({ credits: Response.json(credits({ available: 12, own: 12 })) }))
  open(onRun)
  const agent = await row(/Deep agent run, costs 40 credits. You have 12/)
  expect(screen.getByText("You have 12")).toBeInTheDocument()
  fireEvent.click(agent)
  expect(await screen.findByRole("alert")).toHaveTextContent("This costs 40 credits and you have 12.")
  expect(screen.getByRole("link", { name: "See plans" })).toHaveAttribute("href", "/account")
  expect(onRun).not.toHaveBeenCalled()
})

test("below 6 credits a row runs at once", async () => {
  const onRun = vi.fn()
  mockApi(api())
  open(onRun)
  fireEvent.click(await row("Draft the trip, costs 4 credits"))
  await waitFor(() => expect(onRun).toHaveBeenCalledWith("trip"))
})

test("at 6 credits or more a confirm step shows the balance before and after and never starts by itself", async () => {
  const onRun = vi.fn()
  mockApi(api())
  open(onRun)
  fireEvent.click(await row("Research a question, costs 8 credits"))
  const confirm = await screen.findByRole("group", { name: "Research a question?" })
  expect(within(confirm).getByText("Costs 8 credits. You have 27, so 19 left.")).toBeInTheDocument()
  expect(onRun).not.toHaveBeenCalled()
  fireEvent.click(within(confirm).getByRole("button", { name: "Cancel" }))
  expect(onRun).not.toHaveBeenCalled()
  expect(screen.queryByRole("group", { name: "Research a question?" })).toBeNull()
  fireEvent.click(screen.getByRole("button", { name: "Research a question, costs 8 credits" }))
  const again = await screen.findByRole("group", { name: "Research a question?" })
  fireEvent.click(within(again).getByRole("button", { name: "Start research, costs 8 credits" }))
  await waitFor(() => expect(onRun).toHaveBeenCalledWith("research"))
})

test("the agent row goes straight on, because its screen confirms", async () => {
  const onRun = vi.fn()
  mockApi(api({ credits: Response.json(credits({ available: 60, own: 60 })) }))
  open(onRun)
  fireEvent.click(await row(/Deep agent run/))
  await waitFor(() => expect(onRun).toHaveBeenCalledWith("agent"))
})

test("the taster makes the agent row free, in text", async () => {
  mockApi(api({ taster: { ...taster, used: false, available: true }, credits: Response.json(credits({ available: 0, own: 0 })) }))
  open()
  expect(await row("Deep agent run, free")).toBeEnabled()
  expect(screen.getByText("Your first run is free, one time")).toBeInTheDocument()
})

test("no consent: choosing a row shows the gate, Allow resumes the action", async () => {
  const onRun = vi.fn()
  const f = mockApi(api({ consent: false }))
  open(onRun)
  const r = await row("Draft the trip, costs 4 credits")
  await consentRead(f)
  fireEvent.click(r)
  fireEvent.click(await screen.findByRole("button", { name: "Allow" }))
  await waitFor(() => expect(onRun).toHaveBeenCalledWith("trip"))
  expect(bodyOf(f, "/v1/me/consents/ai_processing")).toEqual({ version: "1", granted: true })
})

test("consent unknown (the read failed): choosing a row opens the gate instead of skipping it", async () => {
  const onRun = vi.fn()
  const base = api()
  const f = mockApi((u, i) => (u.endsWith("/v1/me/consents") && (i?.method ?? "GET") === "GET" ? Response.json({ code: "internal_error" }, { status: 500 }) : base(u, i)))
  open(onRun)
  const explain = await row("Explain, costs 1 credit")
  await consentRead(f)
  fireEvent.click(explain)
  expect(await screen.findByRole("button", { name: "Allow" })).toBeInTheDocument()
  expect(onRun).not.toHaveBeenCalled()
})

test("no consent: Not now runs nothing and the sheet stays usable", async () => {
  const onRun = vi.fn()
  const f = mockApi(api({ consent: false }))
  open(onRun)
  const r = await row("Draft the trip, costs 4 credits")
  await consentRead(f)
  fireEvent.click(r)
  fireEvent.click(await screen.findByRole("button", { name: "Not now" }))
  expect(onRun).not.toHaveBeenCalled()
  expect(screen.getByRole("dialog", { name: "Plan with AI" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Explain, costs 1 credit" })).toBeEnabled()
})

test("a rate limit from the action shows the slow down line", async () => {
  mockApi(api())
  open(vi.fn(() => "rate"))
  fireEvent.click(await row("Explain, costs 1 credit"))
  expect(await screen.findByRole("alert")).toHaveTextContent("Slow down a little. Try again in a few seconds.")
})

test("Escape closes the sheet", async () => {
  const onClose = vi.fn()
  mockApi(api())
  open(vi.fn(), onClose)
  await row("Explain, costs 1 credit")
  fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" })
  expect(onClose).toHaveBeenCalled()
})
