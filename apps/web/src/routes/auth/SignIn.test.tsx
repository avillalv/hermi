import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { AuthError, type IdentityAdapter } from "./identity"
import { authStore } from "./authStore"
import { SignIn } from "./SignIn"

const PERSONAS = [
  { persona: "free", label: "Free user" },
  { persona: "plus", label: "Plus user" },
  { persona: "admin", label: "Admin" },
]

function mockFetch(personas: boolean) {
  const f = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
    const u = String(url)
    if (u.endsWith("/v1/dev/personas")) return personas ? Response.json(PERSONAS) : new Response("{}", { status: 404 })
    if (u.endsWith("/v1/dev/session")) {
      const { persona } = JSON.parse(String(init?.body))
      return Response.json({ access_token: `tok-${persona}`, token_type: "bearer", expires_in: 3600, persona })
    }
    return new Response("{}", { status: 404 })
  })
  vi.stubGlobal("fetch", f)
  return f
}

const adapter = (over: Partial<IdentityAdapter> = {}): IdentityAdapter => ({
  oauth: vi.fn(async () => "oauth-token"),
  sendCode: vi.fn(async () => {}),
  verifyCode: vi.fn(async () => "email-token"),
  ...over,
})
const failing = (code: ConstructorParameters<typeof AuthError>[0]) =>
  vi.fn(async () => {
    throw new AuthError(code)
  })

const show = (a: IdentityAdapter = adapter()) =>
  render(
    <MemoryRouter initialEntries={["/sign-in"]}>
      <Routes>
        <Route path="/sign-in" element={<SignIn adapter={a} />} />
        <Route path="/" element={<h1>Trips</h1>} />
      </Routes>
    </MemoryRouter>,
  )

const click = (name: string) => fireEvent.click(screen.getByRole("button", { name }))
const type = (el: HTMLElement, value: string) => fireEvent.change(el, { target: { value } })

async function toCodeStep() {
  click("Continue with email")
  type(screen.getByLabelText("Email"), "maya@example.com")
  click("Send code")
  return screen.findByLabelText("Six digit code")
}

beforeEach(() => authStore.signOut())
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("shows title and the three sign-in buttons, no persona picker outside dev mode", async () => {
  const f = mockFetch(false)
  show()
  expect(screen.getByRole("heading", { level: 1, name: "Sign in to Hermi" })).toBeInTheDocument()
  for (const n of ["Continue with Apple", "Continue with Google", "Continue with email"])
    expect(screen.getByRole("button", { name: n })).toBeInTheDocument()
  await waitFor(() => expect(f).toHaveBeenCalled())
  expect(screen.queryByText("Dev personas")).not.toBeInTheDocument()
})

test("dev mode shows the persona picker and the Free persona signs in and lands on Trips", async () => {
  const f = mockFetch(true)
  show()
  const free = await screen.findByRole("button", { name: "Free user" })
  expect(screen.getByRole("button", { name: "Plus user" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Admin" })).toBeInTheDocument()
  fireEvent.click(free)
  expect(await screen.findByRole("heading", { name: "Trips" })).toBeInTheDocument()
  expect(authStore.get()).toEqual({ token: "tok-free", persona: "free" })
  expect(f).toHaveBeenCalledWith(expect.stringContaining("/v1/dev/session"), expect.objectContaining({ method: "POST" }))
})

test("Apple sign-in stores the token and goes to Trips", async () => {
  mockFetch(false)
  const a = adapter()
  show(a)
  click("Continue with Apple")
  expect(a.oauth).toHaveBeenCalledWith("apple")
  expect(await screen.findByRole("heading", { name: "Trips" })).toBeInTheDocument()
  expect(authStore.get().token).toBe("oauth-token")
})

test("an unconfigured provider shows the unavailable error", async () => {
  mockFetch(false)
  show(adapter({ oauth: failing("unavailable") }))
  click("Continue with Google")
  expect(await screen.findByRole("alert")).toHaveTextContent("Sign in is not available right now. Try again in a moment.")
})

test("email path: send code, then six digits auto-submit", async () => {
  mockFetch(false)
  const a = adapter()
  show(a)
  click("Continue with email")
  expect(screen.getByText("We will send a six digit code. No password needed.")).toBeInTheDocument()
  type(screen.getByLabelText("Email"), "maya@example.com")
  click("Send code")
  expect(a.sendCode).toHaveBeenCalledWith("maya@example.com")
  const code = await screen.findByLabelText("Six digit code")
  expect(code).toHaveAttribute("autocomplete", "one-time-code")
  expect(code).toHaveAttribute("inputmode", "numeric")
  expect(screen.getByRole("button", { name: /Resend code in \d+ s/ })).toBeDisabled()
  type(code, "12345")
  expect(a.verifyCode).not.toHaveBeenCalled()
  type(code, "123456")
  expect(a.verifyCode).toHaveBeenCalledWith("maya@example.com", "123456")
  expect(await screen.findByRole("heading", { name: "Trips" })).toBeInTheDocument()
})

test("a bad email is rejected before sending", () => {
  mockFetch(false)
  const a = adapter()
  show(a)
  click("Continue with email")
  type(screen.getByLabelText("Email"), "nope")
  click("Send code")
  expect(a.sendCode).not.toHaveBeenCalled()
  expect(screen.getByRole("alert")).toHaveTextContent("Enter an email like name@example.com.")
})

test.each([
  ["wrong_code", "That code is not right. Check the email we sent and try again."],
  ["expired", "That code expired. Send a new one."],
  ["rate_limited", "Too many tries. Wait 10 minutes, then send a new code."],
  ["offline", "You are offline. Connect to sign in."],
] as const)("code error %s shows its copy, linked to the field", async (code, copy) => {
  mockFetch(false)
  show(adapter({ verifyCode: failing(code) }))
  const field = await toCodeStep()
  type(field, "000000")
  const alert = await screen.findByRole("alert")
  expect(alert).toHaveTextContent(copy)
  expect(field.getAttribute("aria-describedby")).toContain(alert.id)
  expect(authStore.get().token).toBeNull()
})

test("three wrong codes add a gentle warning", async () => {
  mockFetch(false)
  show(adapter({ verifyCode: failing("wrong_code") }))
  const field = await toCodeStep()
  for (const c of ["000001", "000002", "000003"]) {
    type(field, c)
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument())
    await act(async () => {})
  }
  expect(await screen.findByText(/Five wrong tries cancel the code/)).toBeInTheDocument()
})

test("use a different email goes back to the email field", async () => {
  mockFetch(false)
  show()
  await toCodeStep()
  click("Use a different email")
  expect(screen.getByLabelText("Email")).toBeInTheDocument()
})

test("offline disables the buttons and says why", () => {
  mockFetch(false)
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  show()
  expect(screen.getByRole("status")).toHaveTextContent("You are offline. Connect to sign in.")
  expect(screen.getByRole("button", { name: "Continue with Apple" })).toBeDisabled()
})

test("a busy button sets aria-busy, keeps its label and ignores a second tap", async () => {
  mockFetch(false)
  let release: (t: string) => void = () => {}
  const a = adapter({ oauth: vi.fn(() => new Promise<string>((r) => (release = r))) })
  show(a)
  click("Continue with Google")
  const btn = screen.getByRole("button", { name: "Continue with Google" })
  expect(btn).toHaveAttribute("aria-busy", "true")
  expect(btn.querySelector(".h-btn__spin")).toBeTruthy()
  fireEvent.click(btn)
  fireEvent.click(btn)
  expect(a.oauth).toHaveBeenCalledTimes(1)
  expect(screen.getByRole("button", { name: "Continue with Apple" })).toBeDisabled()
  await act(async () => release("tok"))
  expect(await screen.findByRole("heading", { name: "Trips" })).toBeInTheDocument()
})

test("an invalid email moves focus to the email field and marks it invalid", () => {
  mockFetch(false)
  show()
  click("Continue with email")
  type(screen.getByLabelText("Email"), "nope")
  click("Send code")
  const field = screen.getByLabelText("Email")
  expect(field).toHaveFocus()
  expect(field).toHaveAttribute("aria-invalid", "true")
  expect(field.getAttribute("aria-describedby")).toContain(screen.getByRole("alert").id)
})

test("a signed-in user who opens sign in goes to Trips", async () => {
  mockFetch(false)
  authStore.signIn("tok")
  show()
  expect(await screen.findByRole("heading", { name: "Trips" })).toBeInTheDocument()
})

test("a session the provider already holds (after an OAuth redirect) signs in", async () => {
  mockFetch(false)
  show(adapter({ restore: vi.fn(async () => "restored") }))
  expect(await screen.findByRole("heading", { name: "Trips" })).toBeInTheDocument()
  expect(authStore.get().token).toBe("restored")
})
