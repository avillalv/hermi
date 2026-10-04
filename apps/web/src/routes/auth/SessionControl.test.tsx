import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { beforeEach, expect, test } from "vitest"
import { queryClient } from "../../lib/queryClient"
import { authStore } from "./authStore"
import { SessionControl } from "./SessionControl"

beforeEach(() => authStore.signOut())
const show = () =>
  render(
    <MemoryRouter>
      <SessionControl />
    </MemoryRouter>,
  )

test("signed out shows a sign-in link", () => {
  show()
  expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in")
})

test("signed in shows Sign out, which clears state", async () => {
  authStore.signIn("tok", "free")
  queryClient.setQueryData(["me"], { id: 1 })
  show()
  fireEvent.click(screen.getByRole("button", { name: "Sign out" }))
  await waitFor(() => expect(authStore.get().token).toBeNull())
  expect(queryClient.getQueryData(["me"])).toBeUndefined()
  expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument()
})

test("a sign-out from elsewhere (a failed refresh) updates the control", () => {
  authStore.signIn("tok")
  show()
  expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument()
  act(() => authStore.signOut())
  expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument()
})
