import { fireEvent, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { Onboarding } from "./Onboarding"
import { bodyOf, mockApi, reset, show } from "./testing"

const boot = (u: string, init?: RequestInit) => (u.endsWith("/v1/me/bootstrap") && init?.method === "POST" ? Response.json({ id: "u1" }, { status: 201 }) : undefined)

beforeEach(() => reset())
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("the age gate blocks until confirmed", () => {
  const f = mockApi(boot)
  show(<Onboarding />, "/onboarding")
  fireEvent.click(screen.getByRole("button", { name: "Save and continue" }))
  expect(screen.getByRole("alert")).toHaveTextContent("Confirm your age to continue.")
  expect(f).not.toHaveBeenCalled()
})

test("saving bootstraps with age_confirmed and the profile, then opens Create trip", async () => {
  const f = mockApi(boot)
  show(<Onboarding />, "/onboarding")
  fireEvent.click(screen.getByLabelText(/I am 13 or older/))
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Maya" } })
  fireEvent.change(screen.getByLabelText("Home airport"), { target: { value: "lis" } })
  fireEvent.click(screen.getByRole("button", { name: "Save and continue" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/trips/new"))
  expect(bodyOf(f, "/v1/me/bootstrap")).toMatchObject({ age_confirmed: true, display_name: "Maya", home_airports: ["LIS"] })
  expect(sessionStorage.getItem("hermi.onboarded")).toBe("1")
})

test("Skip for now still bootstraps without a profile", async () => {
  const f = mockApi(boot)
  show(<Onboarding />, "/onboarding")
  fireEvent.click(screen.getByLabelText(/I am 13 or older/))
  fireEvent.click(screen.getByRole("button", { name: "Skip for now" }))
  await waitFor(() => expect(bodyOf(f, "/v1/me/bootstrap")).toBeDefined())
  expect(bodyOf(f, "/v1/me/bootstrap")).toEqual({ age_confirmed: true })
})

test("EU and UK locales ask for 16", () => {
  vi.spyOn(navigator, "language", "get").mockReturnValue("de-DE")
  mockApi(boot)
  show(<Onboarding />, "/onboarding")
  expect(screen.getByLabelText(/I am 16 or older/)).toBeInTheDocument()
})

test("a failed bootstrap shows an error and stays", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  show(<Onboarding />, "/onboarding")
  fireEvent.click(screen.getByLabelText(/I am 13 or older/))
  fireEvent.click(screen.getByRole("button", { name: "Skip for now" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("We could not set up your account. Try again.")
})

test("an invalid airport or currency shows an inline error and sends nothing", () => {
  const f = mockApi(boot)
  show(<Onboarding />, "/onboarding")
  fireEvent.click(screen.getByLabelText(/I am 13 or older/))
  fireEvent.change(screen.getByLabelText("Home airport"), { target: { value: "L1" } })
  fireEvent.change(screen.getByLabelText("Currency"), { target: { value: "US" } })
  fireEvent.click(screen.getByRole("button", { name: "Save and continue" }))
  expect(screen.getByText("Use a 3 letter airport code, like LIS.")).toBeInTheDocument()
  expect(screen.getByText("Use a 3 letter currency code, like USD.")).toBeInTheDocument()
  expect(f).not.toHaveBeenCalled()
})

test("409 email_in_use says the email already has an account", async () => {
  mockApi(() => Response.json({ code: "email_in_use" }, { status: 409 }))
  show(<Onboarding />, "/onboarding")
  fireEvent.click(screen.getByLabelText(/I am 13 or older/))
  fireEvent.click(screen.getByRole("button", { name: "Skip for now" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("That email already has an account. Sign in with the method you used before.")
})
