import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react"
import type { ReactElement } from "react"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"
import { t } from "../lib/i18n"
import { Activity } from "./activity/Activity"
import { Flights } from "./flights/Flights"
import { Plan } from "./itinerary/Plan"
import { Stays } from "./lodging/Stays"
import { Notes } from "./notes/Notes"
import { mockApi, reset, show, type Handler } from "./onboarding/testing"
import { TripGroup } from "./trips/TripGroup"
import { TripOverview } from "./trips/TripOverview"
import { TripsHome } from "./trips/TripsHome"

/** WF-036.2: every main route shows the shared Skeleton, ErrorState and EmptyState (05 4.16 to 4.18). */
const page = (items: unknown[]) => Response.json({ items, next_cursor: null, has_more: false })
const trip = { id: "t1", version: 1, name: "La Fortuna", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: "owner", destinations: [], travelers: [] }
const empty = (u: string) => {
  if (u.endsWith("/v1/me")) return Response.json({ id: "u1" })
  if (u.endsWith("/v1/trips")) return page([])
  if (u.endsWith("/v1/trips/t1")) return Response.json(trip)
  if (/\/trips\/t1\/(days|routes)/.test(u)) return Response.json([])
  if (/\/trips\/t1\/(notes|lodging|items|activity)/.test(u)) return page([])
  return undefined
}

const ROUTES: { name: string; ui: ReactElement; path: string; url: string; emptyTitle?: string; errorKey: string; gate: (u: string) => boolean }[] = [
  { name: "trips home", errorKey: "trips.error", ui: <TripsHome />, path: "/", url: "/", emptyTitle: t("trips.emptyTitle"), gate: (u) => u.endsWith("/v1/trips") },
  { name: "overview", errorKey: "overview.error", ui: <TripOverview />, path: "/trips/:id", url: "/trips/t1", gate: (u) => u.endsWith("/v1/trips/t1") },
  { name: "group", errorKey: "group.error", ui: <TripGroup />, path: "/trips/:id/group", url: "/trips/t1/group", gate: (u) => u.endsWith("/v1/trips/t1") },
  { name: "plan", errorKey: "plan.error", ui: <Plan />, path: "/trips/:id/plan", url: "/trips/t1/plan", emptyTitle: t("plan.emptyTripTitle"), gate: (u) => u.endsWith("/v1/trips/t1") },
  { name: "stays", errorKey: "stays.error", ui: <Stays />, path: "/trips/:id/stays", url: "/trips/t1/stays", emptyTitle: t("stays.emptyTitle"), gate: (u) => u.endsWith("/v1/trips/t1") },
  { name: "flights", errorKey: "flights.error", ui: <Flights />, path: "/trips/:id/flights", url: "/trips/t1/flights", emptyTitle: t("flights.emptyTitle"), gate: (u) => u.endsWith("/v1/trips/t1") },
  { name: "notes", errorKey: "notes.error", ui: <Notes />, path: "/trips/:id/notes", url: "/trips/t1/notes", emptyTitle: t("notes.emptyTitle"), gate: (u) => u.endsWith("/v1/trips/t1") },
  { name: "activity", errorKey: "activity.error", ui: <Activity />, path: "/activity", url: "/activity", emptyTitle: t("activity.emptyTitle"), gate: (u) => u.endsWith("/v1/trips") },
]

beforeEach(() => reset("free"))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe.each(ROUTES)("$name", ({ ui, path, url, emptyTitle, errorKey, gate }) => {
  test("loading shows the shared skeleton", async () => {
    mockApi((() => new Promise(() => {})) as unknown as Handler)
    show(ui, path, url)
    expect(await screen.findByRole("status", { name: t("states.loading") })).toHaveAttribute("aria-busy", "true")
  })

  test("a server failure shows the screen's error copy in the shared error state with a retry that reloads", async () => {
    let fail = true
    mockApi((u) => (fail && gate(u) ? new Response("{}", { status: 500 }) : empty(u)))
    show(ui, path, url)
    expect(await screen.findByText(t(errorKey), {}, { timeout: 4000 })).toBeInTheDocument()
    fail = false
    fireEvent.click(screen.getByRole("button", { name: t("states.retry") }))
    await waitFor(() => expect(screen.queryByText(t(errorKey))).not.toBeInTheDocument(), { timeout: 4000 })
  }, 15_000)

  test("a 429 shows the rate limit copy with the wait", async () => {
    mockApi((u) => (gate(u) ? new Response("{}", { status: 429, headers: { "Retry-After": "7" } }) : empty(u)))
    show(ui, path, url)
    expect(await screen.findByText(new RegExp(t("states.error.rateLimited")), {}, { timeout: 4000 })).toHaveTextContent(t("states.waitSeconds", { seconds: 7 }))
  })

  if (emptyTitle)
    test("no data shows the shared empty state", async () => {
      mockApi(empty)
      const { container } = show(ui, path, url)
      expect(await screen.findByRole("heading", { name: emptyTitle })).toBeInTheDocument()
      expect(container.querySelector(".state")).not.toBeNull()
    })
})

test("a 404 trip shows the not found copy with no retry", async () => {
  mockApi((u) => (u.endsWith("/v1/trips/t1") ? new Response("{}", { status: 404 }) : empty(u)))
  show(<Notes />, "/trips/:id/notes", "/trips/t1/notes")
  expect(await screen.findByText(t("states.error.notFound"))).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: t("states.retry") })).not.toBeInTheDocument()
})
