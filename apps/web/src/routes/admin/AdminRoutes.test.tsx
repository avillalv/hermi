import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { MemoryRouter, Route, Routes } from "react-router"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import AdminRoutes from "./AdminRoutes"
import { adminRequest, resetAdminClient } from "./adminClient"

type Handler = (init: RequestInit | undefined, url: URL) => Response | Promise<Response>
const json = (body: unknown, status = 200) => Response.json(body, { status })
const problem = (status: number, code: string, message = "Something") => json({ code, detail: message, request_id: "req-1" }, status)

const SESSION = {
  admin: { user_id: "u1", email: "admin@hermi.test", role: "owner", mfa_enrolled: true },
  permissions: { "overview.read": "R", "users.read": "R", "killswitch.set": "X", "killswitch.read": "R", "audit.read": "R" },
  two_factor: { enrolled: true, fresh: false },
  signed_in: true,
  expires_at: new Date(Date.now() + 3600_000).toISOString(),
  fresh_until: null,
  factors: { passkeys: 0, totp: true, recovery_codes_left: 10 },
}
const SIGNED_OUT = { ...SESSION, signed_in: false, expires_at: null }

let routes: Record<string, Handler>
const calls: string[] = []
beforeEach(() => {
  routes = {}
  calls.length = 0
  sessionStorage.clear()
  resetAdminClient()
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost")
      const key = `${init?.method ?? "GET"} ${url.pathname}`
      calls.push(key)
      const h = routes[key]
      return h ? h(init, url) : problem(404, "not_found")
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

const show = (path = "/admin") =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/admin/*" element={<AdminRoutes />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
const withSession = (over: Record<string, unknown> = {}, role = "owner") =>
  (routes["GET /v1/admin/auth/session"] = () => json({ ...SESSION, ...over, admin: { ...SESSION.admin, role } }))

test("loading then the overview inside the shell, with the environment bar and the signed in admin", async () => {
  withSession()
  show()
  expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument()
  expect(screen.getByRole("status", { name: "Environment" })).toHaveTextContent("Local")
  expect(screen.getByText("admin@hermi.test")).toBeInTheDocument()
  expect(screen.getByText("owner")).toBeInTheDocument()
  expect(calls).toContain("GET /v1/admin/auth/session")
})

test("the environment bar tells production and staging apart from the rest", async () => {
  const { envLabel } = await import("./AdminShell")
  expect(envLabel("production")).toEqual({ label: "Production", tone: "production" })
  expect(envLabel("staging")).toEqual({ label: "Staging", tone: "staging" })
  expect(envLabel("local").tone).toBe("local")
})

test("the menu shows only what the role may open, and a typed address for the rest says so", async () => {
  withSession({ permissions: { "overview.read": "r", "users.read": "R", "audit.read": "r", "killswitch.read": "R" } }, "support")
  show("/admin/finance")
  expect(await screen.findByRole("heading", { name: "You cannot open this page" })).toBeInTheDocument()
  const nav = screen.getByRole("navigation", { name: "Admin" })
  expect(within(nav).getByRole("link", { name: "Users" })).toBeInTheDocument()
  expect(within(nav).queryByRole("link", { name: "Finance" })).toBeNull()
  expect(within(nav).queryByRole("link", { name: "Admin users" })).toBeNull()
})

test("an allowed section that is not built yet is an empty state, not a blank page", async () => {
  withSession()
  show("/admin/users")
  expect(await screen.findByRole("heading", { name: "Users" })).toBeInTheDocument()
  expect(screen.getByText("This screen is not built yet.")).toBeInTheDocument()
})

test("a failed session read is an error state with retry", async () => {
  routes["GET /v1/admin/auth/session"] = () => problem(500, "internal_error")
  show()
  expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong on our side")
  withSession()
  fireEvent.click(screen.getByRole("button", { name: "Try again" }))
  expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument()
})

test("offline: the session read cannot reach the server and says so", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))))
  show()
  expect(await screen.findByRole("alert")).toHaveTextContent("You are offline")
})

test("an identity with no admin row sees the 403 screen with no way in", async () => {
  routes["GET /v1/admin/auth/session"] = () => problem(403, "admin_not_enabled")
  show()
  expect(await screen.findByRole("heading", { name: "No admin access" })).toBeInTheDocument()
  expect(screen.getByText(/does not have admin access/i)).toBeInTheDocument()
  expect(screen.queryByRole("navigation")).toBeNull()
})

test("local runs with no Access assertion offer the fake-Access signer, then load the session", async () => {
  let assertion = ""
  routes["GET /v1/admin/auth/session"] = (init) => {
    assertion = new Headers(init?.headers).get("Cf-Access-Jwt-Assertion") ?? ""
    return assertion ? json(SESSION) : problem(401, "token_missing", "Sign in to continue.")
  }
  routes["POST /v1/dev/admin-session"] = () => json({ assertion: "signed-by-fake-access" })
  show()
  fireEvent.click(await screen.findByRole("button", { name: "Continue as this admin" }))
  expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument()
  expect(assertion).toBe("signed-by-fake-access")
})

test("an enrolled admin with no live session signs in with an authenticator code", async () => {
  let body: unknown
  routes["GET /v1/admin/auth/session"] = () => json(SIGNED_OUT)
  routes["POST /v1/admin/auth/signin"] = (init) => {
    body = JSON.parse(String(init?.body))
    return json(SESSION)
  }
  show()
  fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "123456" } })
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }))
  expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument()
  expect(body).toEqual({ method: "totp", code: "123456" })
})

test("a wrong code shows the one generic message and keeps the field", async () => {
  routes["GET /v1/admin/auth/session"] = () => json(SIGNED_OUT)
  routes["POST /v1/admin/auth/signin"] = () => problem(401, "two_factor_failed", "That did not work. Check it and try again.")
  show()
  fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "000000" } })
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }))
  expect(await screen.findByText("That did not work. Check it and try again.")).toBeInTheDocument()
  expect(screen.getByLabelText("Authenticator code")).toBeInTheDocument()
})

test("a recovery code is a separate, labelled way in", async () => {
  let body: unknown
  routes["GET /v1/admin/auth/session"] = () => json(SIGNED_OUT)
  routes["POST /v1/admin/auth/signin"] = (init) => ((body = JSON.parse(String(init?.body))), json(SESSION))
  show()
  fireEvent.click(await screen.findByRole("button", { name: "Use a recovery code" }))
  fireEvent.change(screen.getByLabelText("Recovery code"), { target: { value: "abcd-efgh-ijkl" } })
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }))
  await screen.findByRole("heading", { name: "Overview" })
  expect(body).toEqual({ method: "recovery", code: "abcd-efgh-ijkl" })
})

test("session expiry: a 401 mid-session returns to sign in with a plain notice", async () => {
  withSession()
  routes["GET /v1/admin/overview"] = () => problem(401, "two_factor_required", "Confirm it is you to continue.")
  show()
  await screen.findByRole("heading", { name: "Overview" })
  routes["GET /v1/admin/auth/session"] = () => json(SIGNED_OUT)
  await act(async () => {
    await adminRequest("GET", "/v1/admin/overview")
  })
  expect(await screen.findByText("Your session ended. Sign in again.")).toBeInTheDocument()
  expect(screen.getByLabelText("Authenticator code")).toBeInTheDocument()
})

test("session expiry: the 8 hour clock on the session sends the admin back to sign in on its own", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  try {
    withSession({ expires_at: new Date(Date.now() + 5_000).toISOString() })
    show()
    await screen.findByRole("heading", { name: "Overview" })
    routes["GET /v1/admin/auth/session"] = () => json(SIGNED_OUT)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000)
    })
    expect(await screen.findByText("Your session ended. Sign in again.")).toBeInTheDocument()
  } finally {
    vi.useRealTimers()
  }
})

test("step-up: a 428 opens the dialog, a good code retries the call once and returns its answer", async () => {
  withSession()
  let tries = 0
  routes["POST /v1/admin/kill-switches"] = () => (++tries === 1 ? problem(428, "stepup_required", "Confirm it is you again to do that.") : json({ ok: true }))
  routes["POST /v1/admin/auth/stepup"] = () => json({ ...SESSION, two_factor: { enrolled: true, fresh: true } })
  show()
  await screen.findByRole("heading", { name: "Overview" })
  let result: Awaited<ReturnType<typeof adminRequest>> | undefined
  act(() => void adminRequest("POST", "/v1/admin/kill-switches", { key: "x" }).then((r) => (result = r)))
  const dialog = await screen.findByRole("dialog", { name: "Confirm it is you" })
  fireEvent.change(within(dialog).getByLabelText("Authenticator code"), { target: { value: "654321" } })
  fireEvent.click(within(dialog).getByRole("button", { name: "Confirm" }))
  await waitFor(() => expect(result).toEqual(expect.objectContaining({ ok: true })))
  expect(tries).toBe(2)
  expect(screen.queryByRole("dialog")).toBeNull()
})

test("step-up: cancelling leaves the original 428 with the caller and the action not run", async () => {
  withSession()
  let tries = 0
  routes["POST /v1/admin/kill-switches"] = () => (++tries, problem(428, "stepup_required"))
  show()
  await screen.findByRole("heading", { name: "Overview" })
  let result: Awaited<ReturnType<typeof adminRequest>> | undefined
  act(() => void adminRequest("POST", "/v1/admin/kill-switches", {}).then((r) => (result = r)))
  fireEvent.click(await screen.findByRole("button", { name: "Cancel" }))
  await waitFor(() => expect(result).toEqual(expect.objectContaining({ ok: false, status: 428 })))
  expect(tries).toBe(1)
})

test("step-up: a wrong code keeps the dialog open with the error, and offers no recovery code", async () => {
  withSession()
  routes["POST /v1/admin/kill-switches"] = () => problem(428, "stepup_required")
  routes["POST /v1/admin/auth/stepup"] = () => problem(401, "two_factor_failed", "That did not work. Check it and try again.")
  show()
  await screen.findByRole("heading", { name: "Overview" })
  act(() => void adminRequest("POST", "/v1/admin/kill-switches", {}))
  const dialog = await screen.findByRole("dialog")
  fireEvent.change(within(dialog).getByLabelText("Authenticator code"), { target: { value: "111111" } })
  fireEvent.click(within(dialog).getByRole("button", { name: "Confirm" }))
  expect(await within(dialog).findByText("That did not work. Check it and try again.")).toBeInTheDocument()
  expect(within(dialog).queryByText(/recovery/i)).toBeNull()
})

test("enrolment: no factor yet shows the factor choice, then recovery codes once, then sign in", async () => {
  const unenrolled = {
    ...SESSION,
    admin: { ...SESSION.admin, mfa_enrolled: false },
    two_factor: { enrolled: false, fresh: false },
    signed_in: false,
    expires_at: null,
    permissions: {},
    factors: { passkeys: 0, totp: false, recovery_codes_left: 0 },
  }
  routes["GET /v1/admin/auth/session"] = () => json(unenrolled)
  routes["POST /v1/admin/auth/totp/enrol"] = () => json({ secret: "JBSWY3DPEHPK3PXP", otpauth_uri: "otpauth://totp/Hermi:a?secret=JBSWY3DPEHPK3PXP" })
  routes["POST /v1/admin/auth/totp/confirm"] = () => json({ mfa_enrolled: false })
  routes["POST /v1/admin/auth/recovery-codes"] = () => json({ codes: ["aaaa-1111", "bbbb-2222"], mfa_enrolled: true })
  show()
  expect(await screen.findByRole("heading", { name: "Set up two-factor sign-in" })).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Use an authenticator app" }))
  expect(await screen.findByText("JBSWY3DPEHPK3PXP")).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText("Code from the app"), { target: { value: "123456" } })
  fireEvent.click(screen.getByRole("button", { name: "Confirm code" }))
  expect(await screen.findByText("aaaa-1111")).toBeInTheDocument()
  expect(screen.getByText("bbbb-2222")).toBeInTheDocument()
  // The session now reads as enrolled, but the codes stay on screen until the admin says they are saved.
  routes["GET /v1/admin/auth/session"] = () =>
    json({ ...unenrolled, admin: { ...unenrolled.admin, mfa_enrolled: true }, two_factor: { enrolled: true, fresh: false }, factors: { passkeys: 0, totp: true, recovery_codes_left: 2 } })
  fireEvent.click(screen.getByRole("button", { name: "I saved my codes" }))
  expect(await screen.findByLabelText("Authenticator code")).toBeInTheDocument()
})

test("a passkey sign in sends the assertion the browser made for the server challenge", async () => {
  routes["GET /v1/admin/auth/session"] = () => json({ ...SIGNED_OUT, factors: { passkeys: 1, totp: false, recovery_codes_left: 3 } })
  routes["POST /v1/admin/auth/webauthn/options"] = () =>
    json({ challenge_id: "c1", public_key: { challenge: "AAEC", rpId: "localhost", allowCredentials: [{ type: "public-key", id: "AQID" }], userVerification: "required" } })
  let body: { assertion?: Record<string, string>; challenge_id?: string } = {}
  routes["POST /v1/admin/auth/signin"] = (init) => ((body = JSON.parse(String(init?.body))), json(SESSION))
  const buf = (...b: number[]) => new Uint8Array(b).buffer
  vi.stubGlobal("PublicKeyCredential", class {})
  Object.defineProperty(navigator, "credentials", {
    configurable: true,
    value: {
      get: vi.fn(async () => ({ rawId: buf(1, 2, 3), response: { clientDataJSON: buf(255), authenticatorData: buf(254), signature: buf(253) } })),
    },
  })
  show()
  fireEvent.click(await screen.findByRole("button", { name: "Use a passkey" }))
  await screen.findByRole("heading", { name: "Overview" })
  expect(body.challenge_id).toBe("c1")
  expect(body.assertion).toEqual({ credential_id: "AQID", client_data_json: "_w", authenticator_data: "_g", signature: "_Q" })
})

test("step-up dialog: focus moves in, Tab stays inside, and focus returns to the opener on cancel", async () => {
  withSession()
  routes["POST /v1/admin/kill-switches"] = () => problem(428, "stepup_required")
  show()
  await screen.findByRole("heading", { name: "Overview" })
  const opener = screen.getByRole("button", { name: "Sign out" })
  opener.focus()
  act(() => void adminRequest("POST", "/v1/admin/kill-switches", {}))
  const dialog = await screen.findByRole("dialog")
  await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true))
  const cancel = within(dialog).getByRole("button", { name: "Cancel" })
  cancel.focus()
  fireEvent.keyDown(document, { key: "Tab" })
  expect(dialog.contains(document.activeElement)).toBe(true)
  expect(document.activeElement).not.toBe(cancel)
  fireEvent.click(cancel)
  await waitFor(() => expect(document.activeElement).toBe(opener))
})

test("the fake-Access signer path the console calls is the one the API serves", () => {
  const policy = readFileSync(resolve(__dirname, "../../../../api/tests/route_policy.py"), "utf8")
  const src = readFileSync(resolve(__dirname, "AdminRoutes.tsx"), "utf8")
  expect(policy).toContain('"POST /v1/dev/admin-session"')
  expect(src).toContain('"POST", "/v1/dev/admin-session"')
})
