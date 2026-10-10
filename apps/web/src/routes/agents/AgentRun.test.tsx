import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { __resetAnalytics, __sink } from "../../lib/analytics"
import { mockApi, reset, show } from "../onboarding/testing"
import { AgentRunPage } from "./AgentRun"
import { FARE, NOTE, ev, run, runApi } from "./testing"

const open = () => show(<AgentRunPage />, "/trips/:id/agents/:runId", "/trips/t1/agents/r1")
const STARTED = ev(0, "run.started", "Run started", { kind: "deep_research" })
const finished = (status: string, accepted = 2) => ev(9, "run.finished", "", { status, accepted, credits: { reserved: 40, charged: 31, balance_after: null } })
const posted = (f: ReturnType<typeof mockApi>, part: string) => f.mock.calls.find(([u, i]) => String(u).includes(part) && (i as RequestInit | undefined)?.method === "POST")
const receipt = (charged: number | null, reserved = 40) => ({ action: "agent_run", reserved, charged, from_cache: false, balance_after: null })

beforeEach(() => {
  reset("free")
  __resetAnalytics()
  sessionStorage.clear()
  localStorage.clear()
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("a failed load shows the error state with Try again", async () => {
  mockApi(() => Response.json({}, { status: 500 }))
  open()
  expect(await screen.findByRole("alert", {}, { timeout: 4000 })).toHaveTextContent("We could not load this run. Try again.")
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
})

test("queued: says so, offers Cancel with no charge, and cancelling posts with an idempotency key", async () => {
  const f = mockApi(runApi({
    run: run({ status: "queued", started_at: null }),
    more: (u, i) => (u.endsWith("/v1/agent-runs/r1/cancel") && i?.method === "POST" ? Response.json(run({ status: "cancelled", cancel_requested: true })) : undefined),
  }))
  open()
  expect((await screen.findAllByText("In the queue. About 1 minute.")).length).toBeGreaterThan(0)
  expect(screen.getByText("No charge if you cancel.")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Cancel run" }))
  await waitFor(() => expect(posted(f, "/agent-runs/r1/cancel")).toBeTruthy())
  expect(new Headers((posted(f, "/cancel")![1] as RequestInit).headers).get("Idempotency-Key")).toBeTruthy()
})

test("running: the step list marks the current step and the live region announces it", async () => {
  mockApi(runApi({ events: [STARTED, ev(1, "tool.search", "Searching flights", null, "web_search"), ev(2, "tool.fetch", "Reading kayak.com", null, "web_fetch")], open: true }))
  open()
  const steps = await screen.findByRole("list", { name: "Steps of this run" })
  await waitFor(() => expect(within(steps).getByText("Reading").closest("li")).toHaveAttribute("aria-current", "step"))
  expect(within(steps).getByText("Searching").closest("li")).not.toHaveAttribute("aria-current")
  await waitFor(() => expect(screen.getAllByRole("status").some((s) => s.textContent === "Reading a page")).toBe(true))
  expect(screen.getAllByText("Running").length).toBeGreaterThan(0)
  expect(screen.getByText("40 credits, billed by use")).toBeInTheDocument()
})

test("findings show the evidence label, the open source link and the fare notice; Dismiss hides a row", async () => {
  mockApi(runApi({ events: [STARTED, FARE, NOTE], open: true }))
  open()
  expect(await screen.findByRole("heading", { level: 2, name: "Findings (2)" })).toBeInTheDocument()
  const row = screen.getByRole("group", { name: /^Fare: JFK to LIS/ })
  expect(within(row).getByText("Seen on a page during this run. Prices can change.")).toBeInTheDocument()
  expect(within(row).getByText(/^Found on kayak\.com, checked/)).toBeInTheDocument()
  const link = within(row).getByRole("link", { name: /^Open source, JFK to LIS, \$398, kayak\.com, opens in a browser$/ })
  expect(link).toHaveAttribute("href", "https://kayak.com/f")
  expect(link).toHaveAttribute("rel", "noopener noreferrer")
  fireEvent.click(within(screen.getByRole("group", { name: /^Note: Tram 28/ })).getByRole("button", { name: /^Dismiss/ }))
  expect(screen.queryByRole("group", { name: /^Note: Tram 28/ })).toBeNull()
  expect(screen.getByRole("heading", { level: 2, name: "Findings (1)" })).toBeInTheDocument()
})

test("a finding older than 14 days shows May be out of date", async () => {
  const old = { ...FARE, ts: new Date(Date.now() - 20 * 86_400_000).toISOString() }
  mockApi(runApi({ events: [STARTED, old], open: true }))
  open()
  expect(await screen.findByText(/May be out of date/)).toBeInTheDocument()
})

test("rejected items land in a collapsed Not saved list with the reason", async () => {
  mockApi(runApi({ events: [STARTED, ev(5, "fare.rejected", "x", { errors: ["the price is not on the page you fetched"] })], open: true }))
  open()
  const summary = await screen.findByText("Not saved (1)")
  expect(summary.closest("details")).not.toHaveAttribute("open")
  expect(screen.getByText("Page did not show that fare")).toBeInTheDocument()
})

test("done: the stub says what was saved and what it cost", async () => {
  mockApi(runApi({
    run: run({ status: "succeeded", finished_at: "2027-03-01T10:02:14Z", accepted_count: 2, credits: receipt(31) }),
    events: [STARTED, FARE, NOTE, finished("succeeded")],
  }))
  open()
  await waitFor(() => expect(screen.getAllByText("Done. 1 fare and 1 note saved. 31 credits used.").length).toBeGreaterThan(0))
  expect(screen.queryByRole("button", { name: "Stop" })).toBeNull()
  expect(screen.getByText("02:14")).toBeInTheDocument()
})

test("empty result says nothing was saved and not charged", async () => {
  mockApi(runApi({ run: run({ status: "succeeded", finished_at: "2027-03-01T10:01:00Z", credits: receipt(0) }), events: [STARTED, finished("succeeded", 0)] }))
  open()
  await waitFor(() => expect(screen.getAllByText("Nothing saved. You were not charged.").length).toBeGreaterThan(0))
})

test("failed says it stopped and that you were not charged", async () => {
  mockApi(runApi({ run: run({ status: "failed", finished_at: "2027-03-01T10:01:00Z", credits: receipt(0) }), events: [STARTED, finished("failed", 0)] }))
  open()
  await waitFor(() => expect(screen.getAllByText("The run stopped before it finished. You were not charged.").length).toBeGreaterThan(0))
  expect(screen.getAllByText("Failed").length).toBeGreaterThan(0)
})

test("stopped: partial saves are summarised as Stopped", async () => {
  mockApi(runApi({ run: run({ status: "cancelled", finished_at: "2027-03-01T10:01:00Z", credits: receipt(14) }), events: [STARTED, FARE, finished("cancelled", 1)] }))
  open()
  await waitFor(() => expect(screen.getAllByText("Stopped. 1 fare saved. 14 credits used.").length).toBeGreaterThan(0))
})

test("Stop asks first with the estimate, Keep running closes it, Stop run posts the cancel", async () => {
  const f = mockApi(runApi({
    events: [STARTED, ev(1, "turn", "Turn 7", { turn: 7 })],
    open: true,
    more: (u, i) => (u.endsWith("/v1/agent-runs/r1/cancel") && i?.method === "POST" ? Response.json(run({ cancel_requested: true })) : undefined),
  }))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Stop" }))
  const dialog = await screen.findByRole("dialog")
  expect(within(dialog).getByText("Stop this run? You will be billed 14 credits for the work done.")).toBeInTheDocument()
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep running" }))
  expect(screen.queryByRole("dialog")).toBeNull()
  expect(posted(f, "/cancel")).toBeUndefined()
  fireEvent.click(screen.getByRole("button", { name: "Stop" }))
  fireEvent.click(await screen.findByRole("button", { name: "Stop run" }))
  await waitFor(() => expect(posted(f, "/agent-runs/r1/cancel")).toBeTruthy())
  expect((await screen.findAllByText("Stopping")).length).toBeGreaterThan(0)
})

test("only the starter can stop: a member sees findings but no Stop", async () => {
  mockApi(runApi({ run: run({ credits: null }), events: [STARTED, FARE], open: true }))
  open()
  expect(await screen.findByRole("heading", { level: 2, name: "Findings (1)" })).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Stop" })).toBeNull()
  expect(screen.getByText("Only the person who started this run can stop it.")).toBeInTheDocument()
})

test("offline shows the banner and Stop is disabled; the run keeps going", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(runApi({ events: [STARTED], open: true }))
  open()
  expect(await screen.findByText("You are offline. The run keeps going.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Stop" })).toBeDisabled()
})

test("taster done shows the price card once, with equal See plans and Done, and fires the events", async () => {
  mockApi(runApi({
    run: run({ is_taster: true, status: "succeeded", finished_at: "2027-03-01T10:02:00Z", accepted_count: 1, credits: receipt(40, 40) }),
    events: [STARTED, FARE, finished("succeeded", 1)],
  }))
  open()
  expect(await screen.findByText("That was your free run. Runs cost 40 credits (8 when someone already researched it). Plus includes 60 credits a month.")).toBeInTheDocument()
  expect(screen.getByText("Taster run")).toBeInTheDocument()
  const plans = screen.getByRole("link", { name: "See plans" })
  const done = screen.getByRole("button", { name: "Done" })
  expect(plans.className).toBe(done.className)
  const sent = __sink.map((e) => e.event)
  expect(sent).toContain("taster_upsell_shown")
  expect(sent).toContain("ai_action_completed")
  expect(__sink.find((e) => e.event === "ai_action_completed")!.properties).toMatchObject({ action: "agent_run", taster: true, outcome: "ok" })
  expect(__sink.find((e) => e.event === "agent_finding_saved")!.properties).toMatchObject({ kind: "fare" })
})

test("taster that saved nothing keeps the free run available and shows no price card", async () => {
  mockApi(runApi({
    run: run({ is_taster: true, status: "failed", finished_at: "2027-03-01T10:01:00Z", credits: receipt(0, 0) }),
    events: [STARTED, finished("failed", 0)],
  }))
  open()
  expect(await screen.findByText("That did not finish, so your free run is still available.")).toBeInTheDocument()
  expect(screen.queryByText(/That was your free run/)).toBeNull()
})

test("the price card is muted for 7 days after Done", async () => {
  mockApi(runApi({
    run: run({ is_taster: true, status: "succeeded", finished_at: "2027-03-01T10:02:00Z", accepted_count: 1, credits: receipt(40, 40) }),
    events: [STARTED, FARE, finished("succeeded", 1)],
  }))
  const first = open()
  fireEvent.click(await screen.findByRole("button", { name: "Done" }))
  expect(Number(localStorage.getItem("hermi.taster.mute"))).toBeGreaterThan(Date.now() + 6 * 86_400_000)
  first.unmount()
  sessionStorage.clear()
  open()
  await screen.findByText("Taster run")
  expect(screen.queryByText(/That was your free run/)).toBeNull()
})

test("when the stream fails twice the screen falls back to polling /events", async () => {
  const f = mockApi(runApi({
    events: [STARTED, FARE],
    more: (u) => (u.endsWith("/stream") ? new Response("{}", { status: 500 }) : undefined),
  }))
  open()
  expect(await screen.findByRole("heading", { level: 2, name: "Findings (1)" }, { timeout: 8000 })).toBeInTheDocument()
  expect(f.mock.calls.some(([u]) => String(u).includes("/events?after_seq=-1"))).toBe(true)
}, 15_000)

test("the route drawing checks each finished stop and puts the plane at the current stage", async () => {
  mockApi(runApi({ events: [STARTED, ev(1, "tool.search", "s", null, "web_search"), ev(2, "tool.fetch", "f", null, "web_fetch")], open: true }))
  const { container } = open()
  await waitFor(() => expect(container.querySelectorAll(".h-run__route .h-run__stop-check")).toHaveLength(1)) // stage 1: stop 0 is done
  const svg = container.querySelector(".h-run__route")!
  expect(svg).toHaveAttribute("aria-hidden", "true")
  expect(svg.querySelectorAll(".h-run__plane")).toHaveLength(1)
})

test("a finished run checks every stop", async () => {
  mockApi(runApi({ run: run({ status: "succeeded", finished_at: "2027-03-01T10:02:14Z", credits: receipt(31) }), events: [STARTED, finished("succeeded")] }))
  const { container } = open()
  await waitFor(() => expect(container.querySelectorAll(".h-run__route .h-run__stop-check")).toHaveLength(4))
})

test("a taster summary never mentions credits", async () => {
  mockApi(runApi({
    run: run({ is_taster: true, status: "succeeded", finished_at: "2027-03-01T10:02:00Z", accepted_count: 1, credits: receipt(40, 40) }),
    events: [STARTED, FARE, finished("succeeded", 1)],
  }))
  open()
  await waitFor(() => expect(screen.getAllByText("Done. 1 fare saved.").length).toBeGreaterThan(0))
  expect(screen.queryByText(/credits used/)).toBeNull()
})

test("a timed out failure says why", async () => {
  mockApi(runApi({ run: run({ status: "timed_out", error_code: "deadline", finished_at: "2027-03-01T10:08:00Z", credits: receipt(0) }), events: [STARTED, finished("timed_out", 0)] }))
  open()
  await waitFor(() => expect(screen.getAllByText("The run took too long, so it was stopped. You were not charged.").length).toBeGreaterThan(0))
})

test("findings carry the found by AI label, and thumbs down on a finished run files a report", async () => {
  const f = mockApi(
    runApi({
      run: run({ status: "succeeded", finished_at: "2027-03-01T10:05:00Z", accepted_count: 2, credits: receipt(31) }),
      events: [STARTED, FARE, NOTE, finished("succeeded")],
      more: (u, i) => (u.endsWith("/v1/reports") && i?.method === "POST" ? Response.json({ id: "rep1" }, { status: 201 }) : undefined),
    }),
  )
  open()
  expect(await screen.findByText("Found by AI, check the source")).toBeInTheDocument()
  fireEvent.click(await screen.findByRole("button", { name: "Not helpful" }))
  fireEvent.click(screen.getByRole("button", { name: "Wrong or out of date" }))
  expect(await screen.findByText("Thanks. We will review it.")).toBeInTheDocument()
  expect(JSON.parse(String((posted(f, "/v1/reports")![1] as RequestInit).body))).toEqual({ run_id: "r1", reason: "wrong_info" })
})
