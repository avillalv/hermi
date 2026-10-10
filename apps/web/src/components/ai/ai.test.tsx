import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { __resetAnalytics, __sink } from "../../lib/analytics"
import { queryClient } from "../../lib/queryClient"
import { bodyOf, mockApi, reset } from "../../routes/onboarding/testing"
import { AiConsentGate, AiConsentSwitch, AiFeedback, AiLabel, AiOffNotice, TripAiSwitch } from "./index"

const sent = () => __sink.map((e) => e.event)
const event = (name: string) => __sink.find((e) => e.event === name)?.properties
const saved = { kind: "ai_processing", version: "1", granted: true, accepted_at: "2027-01-01T00:00:00Z" }

beforeEach(() => {
  reset("free")
  __resetAnalytics()
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

// --- consent gate ---------------------------------------------------------------------------------------------------

test("gate: shows the Anthropic sentence, what is sent and the two choices, and fires ai_consent_shown", () => {
  mockApi(() => undefined)
  render(<AiConsentGate onAllowed={vi.fn()} onDeclined={vi.fn()} />)
  const d = screen.getByRole("dialog", { name: "Allow AI on your trips?" })
  expect(within(d).getByText("Your trip details and questions are sent to Anthropic to generate suggestions.")).toBeInTheDocument()
  expect(within(d).getByText(/not used to train models/)).toBeInTheDocument()
  expect(within(d).getByRole("button", { name: "Allow" })).toBeEnabled()
  expect(within(d).getByRole("button", { name: "Not now" })).toBeEnabled()
  expect(sent()).toEqual(["ai_consent_shown"])
})

test("gate: Allow stores the version and calls onAllowed", async () => {
  const f = mockApi((u, i) => (u.endsWith("/v1/me/consents/ai_processing") && i?.method === "PUT" ? Response.json(saved) : undefined))
  const onAllowed = vi.fn()
  render(<AiConsentGate onAllowed={onAllowed} onDeclined={vi.fn()} />)
  fireEvent.click(screen.getByRole("button", { name: "Allow" }))
  await waitFor(() => expect(onAllowed).toHaveBeenCalledOnce())
  expect(bodyOf(f, "/v1/me/consents/ai_processing")).toEqual({ version: "1", granted: true })
  expect(event("ai_consent_granted")).toMatchObject({ version: "1" })
})

test("gate: Not now and Escape decline without saving anything", () => {
  const f = mockApi(() => undefined)
  const onDeclined = vi.fn()
  render(<AiConsentGate onAllowed={vi.fn()} onDeclined={onDeclined} />)
  fireEvent.click(screen.getByRole("button", { name: "Not now" }))
  expect(onDeclined).toHaveBeenCalledOnce()
  expect(sent()).toContain("ai_consent_declined")
  expect(f.mock.calls.some(([, i]) => (i as RequestInit | undefined)?.method === "PUT")).toBe(false)
})

test("gate: a failed save shows an error and stays open", async () => {
  mockApi(() => Response.json({ code: "internal_error" }, { status: 500 }))
  const onAllowed = vi.fn()
  render(<AiConsentGate onAllowed={onAllowed} onDeclined={vi.fn()} />)
  fireEvent.click(screen.getByRole("button", { name: "Allow" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("We could not save your choice. Try again.")
  expect(onAllowed).not.toHaveBeenCalled()
  expect(sent()).not.toContain("ai_consent_granted")
})

test("gate: offline disables Allow and says AI needs a connection", () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  render(<AiConsentGate onAllowed={vi.fn()} onDeclined={vi.fn()} />)
  expect(screen.getByText("AI needs a connection.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Allow" })).toBeDisabled()
  expect(screen.getByRole("button", { name: "Not now" })).toBeEnabled()
})

// --- label and off notice -------------------------------------------------------------------------------------------

test("label: says AI suggestion, check details before booking, and the found variant says check the source", () => {
  render(
    <>
      <AiLabel />
      <AiLabel found />
    </>,
  )
  expect(screen.getByText("AI suggestion, check details before booking")).toBeInTheDocument()
  expect(screen.getByText("Found by AI, check the source")).toBeInTheDocument()
})

test("off notice: an editor is told to ask the owner and has no way to turn it on", () => {
  render(<AiOffNotice tripId="t1" version={3} isOwner={false} ownerName="Sam" />)
  expect(screen.getByText("AI is off for this trip.")).toBeInTheDocument()
  expect(screen.getByText("Ask Sam to turn it on.")).toBeInTheDocument()
  expect(screen.queryByRole("button")).toBeNull()
})

test("off notice: the owner turns it back on with a PATCH carrying the version", async () => {
  const f = mockApi((u, i) => (u.endsWith("/v1/trips/t1") && i?.method === "PATCH" ? Response.json({ id: "t1", version: 4, ai_enabled: true }) : undefined))
  render(<AiOffNotice tripId="t1" version={3} isOwner />)
  fireEvent.click(screen.getByRole("button", { name: "Turn on AI for this trip" }))
  await waitFor(() => expect(bodyOf(f, "/v1/trips/t1")).toEqual({ ai_enabled: true, version: 3 }))
})

test("off notice: a failed change shows an error", async () => {
  mockApi(() => Response.json({ code: "forbidden" }, { status: 403 }))
  render(<AiOffNotice tripId="t1" version={3} isOwner />)
  fireEvent.click(screen.getByRole("button", { name: "Turn on AI for this trip" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("We could not change that. Try again.")
})

// --- switches -------------------------------------------------------------------------------------------------------

test("account switch: on when consent is granted, and turning it off withdraws ai_processing", async () => {
  const f = mockApi((u, i) => {
    if (u.endsWith("/v1/me/consents") && (i?.method ?? "GET") === "GET") return Response.json([saved])
    if (u.endsWith("/v1/me/consents/ai_processing") && i?.method === "PUT") return Response.json({ ...saved, granted: false })
    return undefined
  })
  render(<AiConsentSwitch />)
  const sw = await screen.findByRole("switch", { name: /Allow AI/ })
  expect(sw).toBeChecked()
  expect(screen.getByText(/Turning this off stops AI only/)).toBeInTheDocument()
  fireEvent.click(sw)
  await waitFor(() => expect(bodyOf(f, "/v1/me/consents/ai_processing")).toEqual({ version: "1", granted: false }))
  queryClient.clear()
})

test("trip switch: off sends ai_enabled false and a failure shows an error", async () => {
  const f = mockApi((u, i) => (u.endsWith("/v1/trips/t1") && i?.method === "PATCH" ? Response.json({ code: "version_conflict" }, { status: 409 }) : undefined))
  render(<TripAiSwitch tripId="t1" version={2} enabled />)
  fireEvent.click(screen.getByRole("switch", { name: /AI for this trip/ }))
  await waitFor(() => expect(bodyOf(f, "/v1/trips/t1")).toEqual({ ai_enabled: false, version: 2 }))
  expect(await screen.findByRole("alert")).toHaveTextContent("We could not change that. Try again.")
})

// --- thumbs ---------------------------------------------------------------------------------------------------------

test("thumbs: up thanks the person, fires the event and files no report", () => {
  const f = mockApi(() => undefined)
  render(<AiFeedback target={{ runId: "r1" }} action="explain" />)
  fireEvent.click(screen.getByRole("button", { name: "Helpful" }))
  expect(screen.getByText("Thanks for the feedback.")).toBeInTheDocument()
  expect(event("ai_feedback_given")).toMatchObject({ action: "explain", rating: "up" })
  expect(f).not.toHaveBeenCalled()
  expect(screen.getByRole("button", { name: "Helpful" })).toBeDisabled()
})

test("thumbs: down asks what was wrong, then files a report for the run", async () => {
  const f = mockApi((u, i) => (u.endsWith("/v1/reports") && i?.method === "POST" ? Response.json({ id: "rep1" }, { status: 201 }) : undefined))
  render(<AiFeedback target={{ runId: "r1" }} action="draft_day" />)
  fireEvent.click(screen.getByRole("button", { name: "Not helpful" }))
  expect(screen.getByText("What was wrong?")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Wrong or out of date" }))
  expect(await screen.findByText("Thanks. We will review it.")).toBeInTheDocument()
  expect(bodyOf(f, "/v1/reports")).toEqual({ run_id: "r1", reason: "wrong_info" })
  expect(event("content_reported")).toMatchObject({ surface: "ai_answer", reason: "wrong_info" })
  expect(event("ai_feedback_given")).toMatchObject({ action: "draft_day", rating: "down", reason: "wrong_info" })
})

test("thumbs: a note target sends note_id", async () => {
  const f = mockApi(() => Response.json({ id: "rep1" }, { status: 201 }))
  render(<AiFeedback target={{ noteId: "n1" }} action="agent_run" />)
  fireEvent.click(screen.getByRole("button", { name: "Not helpful" }))
  fireEvent.click(screen.getByRole("button", { name: "Unsafe or harmful" }))
  await screen.findByText("Thanks. We will review it.")
  expect(bodyOf(f, "/v1/reports")).toEqual({ note_id: "n1", reason: "harmful" })
})

test("thumbs: a failed report shows an error and the person can pick again", async () => {
  mockApi(() => Response.json({ code: "internal_error" }, { status: 500 }))
  render(<AiFeedback target={{ runId: "r1" }} action="explain" />)
  fireEvent.click(screen.getByRole("button", { name: "Not helpful" }))
  fireEvent.click(screen.getByRole("button", { name: "Wrong or out of date" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("We could not send that. Try again.")
  expect(screen.getByRole("button", { name: "Wrong or out of date" })).toBeEnabled()
  expect(sent()).not.toContain("content_reported")
})

test("thumbs: too many reports shows the rate message", async () => {
  mockApi(() => Response.json({ code: "rate_limited" }, { status: 429 }))
  render(<AiFeedback target={{ runId: "r1" }} action="explain" />)
  fireEvent.click(screen.getByRole("button", { name: "Not helpful" }))
  fireEvent.click(screen.getByRole("button", { name: "Copied content" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("You have sent a lot of reports today. Try again tomorrow.")
})

test("thumbs: offline disables both buttons and says feedback needs a connection", () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  render(<AiFeedback target={{ runId: "r1" }} action="explain" />)
  expect(screen.getByText("Feedback needs a connection.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Helpful" })).toBeDisabled()
  expect(screen.getByRole("button", { name: "Not helpful" })).toBeDisabled()
})

test("thumbs: a report on a target that is gone says thanks but fires no report event", async () => {
  mockApi(() => Response.json({ code: "not_found" }, { status: 404 }))
  render(<AiFeedback target={{ runId: "r1" }} action="explain" />)
  fireEvent.click(screen.getByRole("button", { name: "Not helpful" }))
  fireEvent.click(screen.getByRole("button", { name: "Wrong or out of date" }))
  expect(await screen.findByText("Thanks. We will review it.")).toBeInTheDocument()
  expect(sent()).not.toContain("content_reported")
  expect(sent()).not.toContain("ai_feedback_given")
})
