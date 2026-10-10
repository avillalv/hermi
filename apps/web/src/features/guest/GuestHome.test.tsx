import { fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

const track = vi.hoisted(() => vi.fn())
vi.mock("../../lib/track", () => ({ track }))

import { authStore } from "../../routes/auth/authStore"
import { GuestHome } from "./GuestHome"
import { SaveSheetHost } from "./SaveSheet"
import { closeSavePrompt } from "./prompts"
import { clearGuest, readGuest, reloadGuest } from "./store"

const ui = () =>
  render(
    <MemoryRouter>
      <GuestHome />
      <SaveSheetHost />
    </MemoryRouter>,
  )

beforeEach(() => {
  localStorage.clear()
  authStore.signOut()
  clearGuest()
  reloadGuest()
  closeSavePrompt()
  track.mockClear()
  vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 404 })))
})
afterEach(() => vi.unstubAllGlobals())

test("a signed-out visitor creates a trip and plans on the device with no request", () => {
  ui()
  fireEvent.change(screen.getByLabelText("Where are you going?"), { target: { value: "Lisbon" } })
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  expect(screen.getByRole("heading", { level: 1, name: "Lisbon" })).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText("What are you doing?"), { target: { value: "Castelo walk" } })
  fireEvent.click(screen.getByRole("button", { name: "Add to plan" }))
  expect(screen.getByText("Castelo walk")).toBeInTheDocument()
  expect(readGuest()?.trip.items).toHaveLength(1)
  expect(track.mock.calls.filter(([n]) => n === "guest_trip_created")).toHaveLength(1)
  expect(fetch).not.toHaveBeenCalled()
})

test("Create asks for a place first", () => {
  ui()
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  expect(screen.getByRole("alert")).toHaveTextContent("Try a city, region or country.")
  expect(readGuest()).toBeNull()
})

test("invite, AI, export, alerts and import open the Save sheet with their trigger", () => {
  ui()
  fireEvent.change(screen.getByLabelText("Where are you going?"), { target: { value: "Lisbon" } })
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  const cases: [string, string][] = [
    ["Invite people", "invite"],
    ["Ask AI", "ai"],
    ["Export", "export"],
    ["Price alerts", "alert"],
    ["Import a trip", "sync"],
  ]
  for (const [label, trigger] of cases) {
    fireEvent.click(screen.getByRole("button", { name: label }))
    expect(screen.getByRole("dialog", { name: "Save your trip" })).toBeInTheDocument()
    expect(track).toHaveBeenLastCalledWith("save_prompt_shown", { trigger })
    closeSavePrompt()
  }
})

test("a second trip shows the one trip limit", () => {
  ui()
  fireEvent.change(screen.getByLabelText("Where are you going?"), { target: { value: "Lisbon" } })
  fireEvent.click(screen.getByRole("button", { name: "Create trip" }))
  fireEvent.click(screen.getByRole("button", { name: "New trip" }))
  expect(screen.getByRole("status")).toHaveTextContent("Guests can plan one trip. Create a free account to add more.")
})
