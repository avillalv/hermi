import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

vi.mock("../ai/api", () => ({ sendReport: vi.fn(async () => "ok") }))
import { sendReport } from "../ai/api"
import { EvidenceLabel } from "./EvidenceLabel"

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] }) // only the clock: waitFor and promises keep running
  vi.setSystemTime(new Date("2026-10-10T12:00:00Z"))
  vi.mocked(sendReport).mockClear()
})
afterEach(() => {
  cleanup()
  vi.useRealTimers()
})
const ago = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString()

test("an AI note shows Found on site, checked date, as a link with an accessible name", () => {
  const { container } = render(<EvidenceLabel kind="note" url="https://www.example.com/p" site="example.com" checkedAt="2026-10-09T12:00:00.000Z" />)
  const a = screen.getByRole("link", { name: /Found on example\.com, checked .*Open example\.com/ })
  expect(a).toHaveAttribute("rel", "noopener noreferrer")
  expect(container).toMatchSnapshot()
})

test("an imported confirmation says From your pasted text and has no link", () => {
  const { container } = render(<EvidenceLabel kind="import" />)
  expect(screen.getByText("From your pasted text")).toBeInTheDocument()
  expect(screen.queryByRole("link")).toBeNull()
  expect(container).toMatchSnapshot()
})

test("an AI fact with no source still renders a label, never a blank", () => {
  render(<EvidenceLabel kind="research" url="" />)
  expect(screen.getByText("No source recorded")).toBeInTheDocument()
})

test("a fare shows its age", () => {
  render(<EvidenceLabel kind="fare" url="https://example.com/f" site="example.com" checkedAt={ago(3)} />)
  expect(screen.getByText("Seen 3 days ago")).toBeInTheDocument()
})

test("Price was different files a wrong info report on the run, once, and says thanks", async () => {
  render(<EvidenceLabel kind="fare" url="https://example.com/f" site="example.com" checkedAt={ago(0)} runId="r1" fareId="f1" priceMinor={68400} currency="USD" />)
  expect(screen.getByText("Seen today")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Price was different" }))
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Thanks. We will look at it."))
  expect(sendReport).toHaveBeenCalledWith({ runId: "r1" }, "wrong_info", "Price was different: fare f1, https://example.com/f, 68400 USD")
  expect(screen.queryByRole("button", { name: "Price was different" })).toBeNull()
})

test("a note has no Price was different button", () => {
  render(<EvidenceLabel kind="note" url="https://example.com/f" checkedAt={ago(0)} runId="r1" />)
  expect(screen.queryByRole("button")).toBeNull()
})

test("a repeat report (200) says thanks and fires no analytics event", async () => {
  vi.mocked(sendReport).mockResolvedValueOnce("repeat")
  const seen = vi.fn()
  window.addEventListener("hermi:event", seen)
  render(<EvidenceLabel kind="fare" url="https://example.com/f" checkedAt={ago(0)} runId="r1" fareId="f1" />)
  fireEvent.click(screen.getByRole("button", { name: "Price was different" }))
  await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument())
  expect(seen).not.toHaveBeenCalled()
  window.removeEventListener("hermi:event", seen)
})
