import { render } from "@testing-library/react"
import { MemoryRouter, Route, Routes, useLocation } from "react-router"
import { vi } from "vitest"
import { queryClient } from "../../lib/queryClient"
import { authStore } from "../auth/authStore"

export type Handler = (url: string, init?: RequestInit) => Response | Promise<Response> | undefined

/** Mocks fetch with a route handler; an unhandled call is a 404. Returns the mock to assert on. */
export function mockApi(handler: Handler) {
  const f = vi.fn(async (url: string | URL | Request, init?: RequestInit) => handler(String(url), init) ?? new Response("{}", { status: 404 }))
  vi.stubGlobal("fetch", f)
  return f
}

export const bodyOf = (f: ReturnType<typeof mockApi>, path: string) => {
  const call = f.mock.calls.find(([u]) => String(u).endsWith(path))
  return call ? JSON.parse(String((call[1] as RequestInit).body)) : undefined
}

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>
}

/** Renders `ui` at `path`. Any other route renders "elsewhere", and `where` shows the current path. */
export function show(ui: React.ReactElement, path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Where />
      <Routes>
        <Route path={path} element={ui} />
        <Route path="*" element={<p>elsewhere</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

export function reset(persona?: string) {
  queryClient.setDefaultOptions({ queries: { retry: false } })
  queryClient.clear()
  authStore.signOut()
  authStore.signIn("tok", persona)
}
