import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { afterEach, describe, expect, it, vi } from "vitest"
import { AppRoutes } from "../shell/routes"

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe("not found catch-all", () => {
  it("renders for an unknown path, with Back and Home that work", () => {
    vi.stubGlobal("fetch", async () => Response.json({ items: [], next_cursor: null, has_more: false }))
    render(
      <MemoryRouter initialEntries={["/activity", "/no/such/page"]} initialIndex={1}>
        <AppRoutes />
      </MemoryRouter>,
    )
    expect(screen.getByRole("alert")).toHaveTextContent("This page is not available. It may have moved or the address may be wrong.")
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/")
    fireEvent.click(screen.getByRole("button", { name: "Back" }))
    expect(screen.queryByRole("alert")).toBeNull()
  })
})
