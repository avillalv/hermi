import { screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { authStore } from "../auth/authStore"
import { bodyOf, mockApi, reset, show } from "../onboarding/testing"
import { Claim } from "./Claim"

const ok = (u: string, init?: RequestInit) => (u.endsWith("/v1/me/legacy-claim") && init?.method === "POST" ? Response.json({ id: "u1" }) : undefined)
const problem = (status: number, code: string) => (u: string) =>
  u.endsWith("/v1/me/legacy-claim") ? Response.json({ code, status }, { status, headers: { "Content-Type": "application/problem+json" } }) : undefined

beforeEach(() => {
  reset()
  sessionStorage.clear()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

const open = () => show(<Claim />, "/claim/:token", "/claim/abc123")

test("signed out: remembers the link and goes to sign in", async () => {
  authStore.signOut()
  const f = mockApi(ok)
  open()
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/sign-in"))
  expect(sessionStorage.getItem("hermi.claim")).toBe("abc123")
  expect(f).not.toHaveBeenCalled()
})

test("redeeming shows a busy status, then success opens Trips", async () => {
  const f = mockApi(ok)
  open()
  expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true")
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/))
  expect(bodyOf(f, "/v1/me/legacy-claim")).toEqual({ token: "abc123" })
  expect(f).toHaveBeenCalledTimes(1)
  expect(sessionStorage.getItem("hermi.onboarded")).toBe("1")
  expect(sessionStorage.getItem("hermi.claim")).toBeNull()
})

test("an expired or used link says to ask for a new one", async () => {
  mockApi(problem(410, "claim_link_expired"))
  open()
  expect(await screen.findByRole("alert")).toHaveTextContent("Ask for a new link")
  expect(screen.getByTestId("where")).toHaveTextContent("/claim/abc123")
})

test("a sign-in that already has an account is told so", async () => {
  mockApi(problem(409, "email_in_use"))
  open()
  expect(await screen.findByRole("alert")).toHaveTextContent("already has its own account")
})

test("a failure offers Try again, which redeems again", async () => {
  let calls = 0
  mockApi((u) => (u.endsWith("/v1/me/legacy-claim") ? (calls++ === 0 ? new Response("{}", { status: 500 }) : Response.json({ id: "u1" })) : undefined))
  open()
  expect(await screen.findByRole("alert")).toHaveTextContent("could not claim")
  screen.getByRole("button", { name: "Try again" }).click()
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/))
})
