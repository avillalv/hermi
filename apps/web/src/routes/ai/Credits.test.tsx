import { cleanup, fireEvent, screen, within } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { __resetAnalytics } from "../../lib/analytics"
import { trip } from "../agents/testing"
import { mockApi, reset, show, type Handler } from "../onboarding/testing"
import { Credits } from "./Credits"

const balance = (over: Record<string, unknown> = {}) => ({
  available: 19, own: 19, pool: 0, payer: "own", blocked: false, version: 3, total: 19, monthly: 12, trip_pass: 0, purchased: 7, next_monthly_grant_at: "2027-06-01T00:00:00Z",
  grants: [
    { kind: "monthly", remaining: 12, expires_at: "2027-06-01T00:00:00Z", trip_id: null },
    { kind: "purchase", remaining: 7, expires_at: "2028-01-15T12:00:00Z", trip_id: null },
  ],
  ...over,
})
const entry = (kind: string, delta: number, over: Record<string, unknown> = {}) => ({
  reservation_id: null, at: "2027-05-02T10:00:00Z", kind, delta, charged: null, action: null, trip_id: null, run_id: null, note: null, ...over,
})
const page = (items: unknown[], next: string | null = null) => ({ items, next_cursor: next, has_more: next !== null })

const api = (ledger: (u: string) => Response | Promise<Response>, bal: Response | null = null): Handler => (u) => {
  if (u.endsWith("/v1/trips/t1")) return Response.json(trip({ name: "Lisbon" }))
  if (u.includes("/v1/me/credits/ledger")) return ledger(u)
  if (u.includes("/v1/me/credits")) return bal?.clone() ?? Response.json(balance())
  return undefined
}
const open = () => show(<Credits />, "/account/credits")

beforeEach(() => {
  reset("free")
  __resetAnalytics()
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("balance by pool and a history that matches the ledger: spends, refunds and grants, newest first", async () => {
  const res = "11111111-1111-4111-8111-111111111111"
  const items = [
    entry("settle", 0, { charged: 0, action: "research", reservation_id: res, at: "2027-05-03T09:00:00Z" }),
    entry("refund", 8, { action: "research", reservation_id: res, at: "2027-05-03T09:00:00Z" }),
    entry("reserve", -8, { action: "research", reservation_id: res, at: "2027-05-03T08:59:00Z" }),
    entry("reserve", -1, { action: "explain", reservation_id: "r2", at: "2027-05-02T10:00:00Z" }),
    entry("grant", 12, { at: "2027-05-01T00:00:00Z" }),
  ]
  mockApi(api(() => Response.json(page(items))))
  open()
  expect(await screen.findByText("19 credits left")).toBeInTheDocument()
  expect(screen.getByText(/12 monthly, they do not roll over/)).toBeInTheDocument()
  expect(screen.getByText(/^7 bought, last until 15 Jan 2028. Spent last.$/)).toBeInTheDocument()
  const list = await screen.findByRole("list", { name: "Credit history" })
  const rows = within(list).getAllByRole("listitem")
  expect(rows).toHaveLength(4) // the settle row moves nothing and is not listed
  expect(rows[0]).toHaveTextContent("Refund, 8 credits returned")
  expect(rows[0]).toHaveTextContent("+8")
  expect(rows[1]).toHaveTextContent("Research")
  expect(rows[1]).toHaveTextContent("-8")
  expect(rows[2]).toHaveTextContent("Explain")
  expect(rows[2]).toHaveTextContent("-1")
  expect(within(rows[2]).getByLabelText("Minus 1 credit")).toBeInTheDocument()
  expect(within(rows[0]).getByLabelText("Plus 8 credits")).toBeInTheDocument()
  expect(rows[3]).toHaveTextContent("Credits added")
  expect(rows[3]).toHaveTextContent("+12")
})

test("history loading shows a skeleton while the ledger is on its way", async () => {
  mockApi(api(() => new Promise<Response>(() => undefined)))
  open()
  expect(await screen.findByText("19 credits left")).toBeInTheDocument()
  expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument()
})

test("history empty: says there is nothing yet", async () => {
  mockApi(api(() => Response.json(page([]))))
  open()
  expect(await screen.findByText("No credit activity yet. Credits you add or use will show up here.")).toBeInTheDocument()
})

test("history error: says what happened and Try again loads it", async () => {
  let n = 0
  mockApi(api(() => (n++ < 2 ? new Response("{}", { status: 500 }) : Response.json(page([entry("grant", 12)])))))
  open()
  expect(await screen.findByText("We could not load your credit history. Your credits have not changed. Try again.")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Try again" }))
  expect(await screen.findByText("Credits added")).toBeInTheDocument()
})

test("history offline: says to connect", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  mockApi(api(() => Response.json(page([entry("grant", 12)]))))
  open()
  expect(await screen.findByText("Connect to see your credits.")).toBeInTheDocument()
})

test("history paging: Show more loads the next page with the cursor", async () => {
  const f = mockApi(
    api((u) =>
      u.includes("cursor=c2")
        ? Response.json(page([entry("grant", 5, { at: "2027-04-01T00:00:00Z" })]))
        : Response.json(page([entry("reserve", -1, { action: "explain", reservation_id: "r" })], "c2")),
    ),
  )
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Show more" }))
  expect(await screen.findByText("Credits added")).toBeInTheDocument()
  expect(f.mock.calls.some(([u]) => String(u).includes("cursor=c2"))).toBe(true)
  expect(screen.queryByRole("button", { name: "Show more" })).toBeNull()
})

test("a balance of zero is shown plainly, with the free path and no purchase button", async () => {
  mockApi(api(() => Response.json(page([])), Response.json(balance({ available: 0, own: 0, total: 0, monthly: 0, purchased: 0, next_monthly_grant_at: null }))))
  open()
  expect(await screen.findByText("0 credits left")).toBeInTheDocument()
  expect(screen.getByText("You can add credits or upgrade in the iOS app.")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: /buy|purchase/i })).toBeNull()
})

test("Trip Pass credits are a separate trip pool, and promo credits show their expiry", async () => {
  const bal = balance({
    total: 27, trip_pass: 8, monthly: 12, purchased: 0, available: 19,
    grants: [
      { kind: "monthly", remaining: 12, expires_at: "2027-06-01T00:00:00Z", trip_id: null },
      { kind: "promo", remaining: 7, expires_at: "2027-09-30T12:00:00Z", trip_id: null },
      { kind: "trip_pass", remaining: 8, expires_at: null, trip_id: "t1" },
    ],
  })
  mockApi(api(() => Response.json(page([])), Response.json(bal)))
  open()
  expect(await screen.findByRole("heading", { name: "19 credits left" })).toBeInTheDocument()
  expect(screen.getByText(/^7 promo credits, expire 30 Sep/)).toBeInTheDocument()
  expect(await screen.findByText("Trip Pass credits, Lisbon: 8. Only for that trip.")).toBeInTheDocument()
})
