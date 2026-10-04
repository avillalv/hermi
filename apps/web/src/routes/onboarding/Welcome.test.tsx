import { screen } from "@testing-library/react"
import { expect, test } from "vitest"
import { Welcome } from "./Welcome"
import { authStore } from "../auth/authStore"
import { show } from "./testing"

test("shows the headline, the support line and both buttons", () => {
  show(<Welcome />, "/welcome")
  expect(screen.getByRole("heading", { level: 1, name: "Plan together. Know the fare." })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Plan a trip" })).toHaveAttribute("href", "/sign-in")
  expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in")
  expect(screen.getByText(/By continuing you agree to the/).textContent).toBe("By continuing you agree to the Terms and the Privacy policy.")
  expect(screen.getByRole("link", { name: "Terms" })).toHaveClass("h-link")
  expect(screen.getByRole("link", { name: "Privacy policy" })).toHaveClass("h-link")
  expect(screen.getByRole("img", { name: /Illustrated map/ })).toBeInTheDocument()
})

test("a signed-in visitor goes to Trips", () => {
  authStore.signIn("tok", "free")
  show(<Welcome />, "/welcome")
  expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/)
  authStore.signOut()
})
