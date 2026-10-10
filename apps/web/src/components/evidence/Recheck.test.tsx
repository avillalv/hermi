import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { mockApi, reset, type Handler } from "../../routes/onboarding/testing"
import { Recheck } from "./Recheck"

const SRC = { url: "https://guide.example.com/tram", title: null, site: "guide.example.com" }
const reply = (result: string, value: string | null = null, charged = 1) =>
  Response.json({ result, current_value: value, source: SRC, checked_at: "2026-10-10T12:00:00Z", credits: { charged } })
const ui = (over: Partial<React.ComponentProps<typeof Recheck>> = {}) =>
  render(<Recheck kind="note" id="n1" tripId="t1" subject="Tram 28 is often crowded" canRecheck {...over} />)
const handler = (res: Response | (() => Response)): Handler => (u, i) =>
  u.includes("/notes/n1/recheck") && i?.method === "POST" ? (typeof res === "function" ? res() : res) : u.endsWith("/trips/t1/notes") && i?.method === "POST" ? Response.json({ id: "n9" }, { status: 201 }) : undefined
const press = () => fireEvent.click(screen.getByRole("button", { name: "Recheck: Tram 28 is often crowded" }))

beforeEach(() => reset("free"))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("an editor sees a Recheck button named for its subject with a 1 credit chip", () => {
  ui()
  const b = screen.getByRole("button", { name: "Recheck: Tram 28 is often crowded" })
  expect(within(b).getByText("1")).toBeInTheDocument()
  expect(b).toHaveTextContent("credit")
})

test("a viewer gets no button, and AI off for the trip hides it", () => {
  ui({ canRecheck: false })
  expect(screen.queryByRole("button")).toBeNull()
  cleanup()
  ui({ aiOn: false })
  expect(screen.queryByRole("button")).toBeNull()
})

test("confirmed says Still the same and sends one Idempotency-Key", async () => {
  const f = mockApi(handler(() => reply("confirmed")))
  ui()
  press()
  expect(await screen.findByText("Still the same. Checked today.")).toBeInTheDocument()
  const post = f.mock.calls.find(([u]) => String(u).includes("/notes/n1/recheck"))!
  expect(new Headers((post[1] as RequestInit).headers).get("Idempotency-Key")).toBeTruthy()
  expect(screen.queryByRole("button", { name: "Save as a note" })).toBeNull()
})

test("changed shows the new value with its source, keeps the old text and saves as a note on tap", async () => {
  const f = mockApi(handler(() => reply("changed", "every 20 minutes")))
  ui()
  press()
  expect(await screen.findByText("It now says: every 20 minutes")).toBeInTheDocument()
  expect(screen.getByText("Source: guide.example.com")).toBeInTheDocument()
  expect(screen.getByText("The saved text stays as it is.")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Save as a note" }))
  expect(await screen.findByText("Saved as a note.")).toBeInTheDocument()
  const call = f.mock.calls.find(([u, i]) => String(u).endsWith("/trips/t1/notes") && (i as RequestInit).method === "POST")!
  expect(JSON.parse(String((call[1] as RequestInit).body))).toMatchObject({ body: "every 20 minutes", source_url: SRC.url })
})

test("not shown and unreachable use the spec copy", async () => {
  mockApi(handler(() => reply("not_shown")))
  ui()
  press()
  expect(await screen.findByText("The page no longer shows this.")).toBeInTheDocument()
  cleanup()
  mockApi(handler(() => reply("unreachable", null, 0)))
  ui()
  press()
  expect(await screen.findByText("We could not reach the page. You were not charged.")).toBeInTheDocument()
})

test("loading turns the button into Checking and blocks a second tap", async () => {
  let release!: (r: Response) => void
  const f = mockApi((u, i) => (u.includes("/recheck") && i?.method === "POST" ? (new Promise<Response>((r) => (release = r)) as never) : undefined))
  ui()
  press()
  const b = await screen.findByRole("button", { name: "Recheck: Tram 28 is often crowded" })
  expect(b).toHaveAttribute("aria-busy", "true")
  expect(b).toHaveTextContent("Checking")
  fireEvent.click(b)
  release(reply("confirmed"))
  await screen.findByText("Still the same. Checked today.")
  expect(f.mock.calls.filter(([u]) => String(u).includes("/recheck"))).toHaveLength(1)
})

test("an error says nothing was charged, and no credits says so", async () => {
  mockApi(handler(() => new Response("{}", { status: 500 })))
  ui()
  press()
  expect(await screen.findByRole("alert")).toHaveTextContent("That did not finish. You were not charged.")
  cleanup()
  mockApi(handler(() => Response.json({ code: "insufficient_credits" }, { status: 402 })))
  ui()
  press()
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("You do not have a credit to spend on this."))
})

test("offline disables the button and says it needs a connection", () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  ui()
  expect(screen.getByRole("button", { name: /Recheck:/ })).toBeDisabled()
  expect(screen.getByText("Recheck needs a connection.")).toBeInTheDocument()
})
