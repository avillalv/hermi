import { act, fireEvent, render, screen, within } from "@testing-library/react"
import { MemoryRouter, Route, Routes, useLocation } from "react-router"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

const track = vi.hoisted(() => vi.fn())
vi.mock("../../lib/track", () => ({ track }))

import { authStore } from "../../routes/auth/authStore"
import { GuestBanner } from "./GuestBanner"
import { SaveSheetHost } from "./SaveSheet"
import { closeSavePrompt, isMuted, requireAccount } from "./prompts"
import { createGuestTrip, reloadGuest } from "./store"

const Where = () => <p data-testid="where">{useLocation().pathname}</p>
const ui = () =>
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Where />
      <Routes>
        <Route
          path="*"
          element={
            <>
              <GuestBanner />
              <SaveSheetHost />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
const events = (n: string) => track.mock.calls.filter(([e]) => e === n).map(([, p]) => p)

beforeEach(() => {
  localStorage.clear()
  authStore.signOut()
  reloadGuest()
  closeSavePrompt()
  track.mockClear()
})
afterEach(() => vi.restoreAllMocks())

test("the banner shows only for a signed-out guest with a trip, and Save opens the sheet", () => {
  const { unmount } = ui()
  expect(screen.queryByText("Guest trip, saved on this phone")).not.toBeInTheDocument()
  unmount()
  createGuestTrip({ name: "Lisbon" })
  ui()
  expect(screen.getByText("Guest trip, saved on this phone")).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  expect(screen.getByRole("dialog", { name: "Save your trip" })).toBeInTheDocument()
  expect(events("save_prompt_shown")).toEqual([{ trigger: "banner" }])
})

test("a signed-in person sees no banner", () => {
  createGuestTrip({ name: "Lisbon" })
  authStore.signIn("tok")
  ui()
  expect(screen.queryByText("Guest trip, saved on this phone")).not.toBeInTheDocument()
})

test("the sheet has the copy and the buttons in the 05 6.2 order", () => {
  ui()
  act(() => void requireAccount("invite"))
  const dialog = screen.getByRole("dialog", { name: "Save your trip" })
  expect(within(dialog).getByText("Create a free account so your trip is safe and you can share it. Nothing you built will be lost.")).toBeInTheDocument()
  const names = within(dialog).getAllByRole("button").map((b) => b.textContent)
  expect(names).toEqual(["Continue with Apple", "Continue with Google", "Continue with email", "Not now"])
  expect(within(dialog).getByRole("button", { name: "Continue with Apple" })).toHaveClass("h-btn--apple")
})

test("Not now emits dismissed and mutes that trigger for 7 days, other triggers still show", () => {
  ui()
  act(() => void requireAccount("export"))
  fireEvent.click(screen.getByRole("button", { name: "Not now" }))
  expect(events("save_prompt_dismissed")).toEqual([{ trigger: "export" }])
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  expect(isMuted("export")).toBe(true)
  expect(isMuted("export", Date.now() + 8 * 86_400_000)).toBe(false)
  // a muted trigger does not reopen the sheet, but the tap is not silent
  act(() => void requireAccount("export"))
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  expect(screen.getByRole("status")).toHaveTextContent("Create a free account to use this.")
  expect(events("save_prompt_shown")).toHaveLength(1)
  act(() => void requireAccount("alert"))
  expect(screen.getByRole("dialog", { name: "Save your trip" })).toBeInTheDocument()
})

test("the banner is never muted", () => {
  createGuestTrip({ name: "Lisbon" })
  ui()
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  fireEvent.click(screen.getByRole("button", { name: "Not now" }))
  expect(isMuted("banner")).toBe(false)
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
  expect(screen.getByRole("dialog")).toBeInTheDocument()
})

test("offline the sign-in buttons are disabled and the line says the trip stays on the phone", () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  ui()
  act(() => void requireAccount("sync"))
  const dialog = screen.getByRole("dialog")
  for (const n of ["Continue with Apple", "Continue with Google", "Continue with email"]) expect(within(dialog).getByRole("button", { name: n })).toBeDisabled()
  expect(within(dialog).getByRole("status")).toHaveTextContent("Connect to the internet to create your account. Your trip stays on this phone.")
  expect(within(dialog).getByRole("button", { name: "Not now" })).toBeEnabled()
})

test("Continue with email goes to the sign-in screen without counting as a dismissal", () => {
  ui()
  act(() => void requireAccount("ai"))
  fireEvent.click(screen.getByRole("button", { name: "Continue with email" }))
  expect(screen.getByTestId("where")).toHaveTextContent("/sign-in")
  expect(events("save_prompt_dismissed")).toEqual([])
})

test("requireAccount lets a signed-in caller through and maps import to the sync trigger", () => {
  authStore.signIn("tok")
  expect(requireAccount("invite")).toBe(true)
  authStore.signOut()
  expect(requireAccount("import")).toBe(false)
  expect(events("save_prompt_shown")).toEqual([{ trigger: "sync" }])
})
