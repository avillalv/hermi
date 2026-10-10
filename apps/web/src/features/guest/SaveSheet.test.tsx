import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

vi.mock("../../lib/track", () => ({ track: vi.fn() }))

import { authStore } from "../../routes/auth/authStore"
import type { IdentityAdapter } from "../../routes/auth/identity"
import { SaveSheet } from "./SaveSheet"
import { closeSavePrompt, showSavePrompt, useSavePrompt } from "./prompts"

const adapter = (oauth: IdentityAdapter["oauth"]): IdentityAdapter => ({ oauth, sendCode: vi.fn(), verifyCode: vi.fn() })
const Open = () => <p data-testid="open">{String(useSavePrompt().open)}</p>
const show = (a: IdentityAdapter) =>
  render(
    <MemoryRouter>
      <Open />
      <SaveSheet adapter={a} />
    </MemoryRouter>,
  )

beforeEach(() => {
  authStore.signOut()
  showSavePrompt("banner")
})
afterEach(() => {
  closeSavePrompt()
  authStore.signOut()
})

test.each([
  ["Apple", "apple"],
  ["Google", "google"],
] as const)("%s sign in stores the session and closes the sheet", async (name, provider) => {
  const oauth = vi.fn().mockResolvedValue("tok")
  show(adapter(oauth))
  fireEvent.click(screen.getByRole("button", { name: new RegExp(name, "i") }))
  await waitFor(() => expect(authStore.get().token).toBe("tok"))
  expect(oauth).toHaveBeenCalledWith(provider)
  await waitFor(() => expect(screen.getByTestId("open")).toHaveTextContent("null"))
})

test("a failed sign in shows an error line and keeps the sheet open", async () => {
  show(adapter(vi.fn().mockRejectedValue(new Error("x"))))
  fireEvent.click(screen.getByRole("button", { name: /apple/i }))
  expect(await screen.findByRole("alert")).toBeInTheDocument()
  expect(authStore.get().token).toBeFalsy()
  expect(screen.getByTestId("open")).toHaveTextContent("banner")
})
