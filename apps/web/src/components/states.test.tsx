import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { EmptyState } from "./EmptyState"
import { ErrorState, ERROR_COPY } from "./ErrorState"
import { Skeleton } from "./Skeleton"

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe("EmptyState", () => {
  it("shows title, one sentence and one primary button that fires", () => {
    const onClick = vi.fn()
    render(<EmptyState icon="bed" title="No stays yet" body="Paste a link or search to start a shortlist." action={{ label: "Add a stay", onClick }} />)
    expect(screen.getByRole("heading", { name: "No stays yet" })).toBeInTheDocument()
    expect(screen.getByText("Paste a link or search to start a shortlist.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Add a stay" }))
    expect(onClick).toHaveBeenCalledOnce()
  })
  it("has a decorative route pattern and an optional quiet link", () => {
    const { container } = render(<EmptyState icon="bed" title="t" body="b" action={{ label: "Go", onClick() {} }} link={{ label: "Learn more", href: "/x" }} />)
    expect(container.querySelectorAll("path.h-route")).toHaveLength(2)
    expect(screen.getByRole("link", { name: "Learn more" })).toHaveAttribute("href", "/x")
  })
})

describe("ErrorState copy", () => {
  it.each([
    ["offline", "You are offline. Your trip is saved on this phone. Changes will sync when you reconnect."],
    ["server", "Something went wrong on our side. We are looking into it. Try again in a minute."],
    ["notFound", "This trip is not available. It may have been deleted or you may not have access."],
    ["permission", "You can view this trip but not edit it. Ask the owner to make you an editor."],
    ["conflict", "Someone changed this while you were editing. Review their version."],
  ] as const)("%s", (kind, text) => {
    render(<ErrorState kind={kind} />)
    expect(screen.getByRole("alert")).toHaveTextContent(text)
  })
  it("maintenance says Hermi is read only", () => {
    render(<ErrorState kind="maintenance" />)
    expect(screen.getByRole("alert")).toHaveTextContent("Hermi is read only for a short while. You can still look at your trips. Try again soon.")
  })
  it("shows an optional secondary link", () => {
    render(<ErrorState kind="offline" secondary={{ label: "Keep planning offline", href: "/" }} />)
    expect(screen.getByRole("link", { name: "Keep planning offline" })).toHaveAttribute("href", "/")
  })
  it("has copy with no dashes for every kind", () => {
    for (const text of Object.values(ERROR_COPY)) expect(text).not.toMatch(new RegExp("[\u2013\u2014]"))
    expect(Object.keys(ERROR_COPY).sort()).toEqual(
      ["conflict", "forcedUpdate", "limit", "maintenance", "notFound", "offline", "permission", "rateLimited", "server", "unauthorized"],
    )
  })
  it("lets the caller give the exact sentence", () => {
    render(<ErrorState kind="limit" message="You have used this month's 12 credits. They renew on 1 Nov." />)
    expect(screen.getByRole("alert")).toHaveTextContent("You have used this month's 12 credits. They renew on 1 Nov.")
  })
  it("tells a rate limited person how long to wait", () => {
    render(<ErrorState kind="rateLimited" retryAfter={30} />)
    expect(screen.getByRole("alert")).toHaveTextContent("Try again in 30 seconds.")
  })
})

describe("ErrorState actions", () => {
  it("shows the reference id in mono and omits it when absent", () => {
    const { rerender } = render(<ErrorState kind="server" requestId="7F3A" />)
    expect(screen.getByText("Reference 7F3A")).toHaveClass("h-mono")
    rerender(<ErrorState kind="server" />)
    expect(screen.queryByText(/Reference/)).toBeNull()
  })
  it("retries", () => {
    const onRetry = vi.fn()
    render(<ErrorState kind="server" onRetry={onRetry} />)
    fireEvent.click(screen.getByRole("button", { name: "Try again" }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
  it("sends a signed out person to sign in and a forced update to the store link", () => {
    const { rerender } = render(<ErrorState kind="unauthorized" />)
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in")
    rerender(<ErrorState kind="forcedUpdate" updateHref="https://example.com/app" />)
    expect(screen.getByRole("link", { name: "Update Hermi" })).toHaveAttribute("href", "https://example.com/app")
  })
  it("full screen has Back and Home that work", () => {
    render(
      <MemoryRouter initialEntries={["/a", "/b"]} initialIndex={1}>
        <Routes>
          <Route path="/a" element={<p>page a</p>} />
          <Route path="/b" element={<ErrorState kind="notFound" fullScreen />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/")
    fireEvent.click(screen.getByRole("button", { name: "Back" }))
    expect(screen.getByText("page a")).toBeInTheDocument()
  })
  it("Back falls back to Home when there is nothing to go back to", () => {
    render(
      <MemoryRouter initialEntries={["/b"]}>
        <Routes>
          <Route path="/b" element={<ErrorState kind="notFound" fullScreen />} />
          <Route path="/" element={<p>home</p>} />
        </Routes>
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByRole("button", { name: "Back" }))
    expect(screen.getByText("home")).toBeInTheDocument()
  })
  it("inline has no Back or Home and needs no router", () => {
    render(<ErrorState kind="server" />)
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull()
    expect(screen.queryByRole("link", { name: "Home" })).toBeNull()
  })
})

describe("Skeleton", () => {
  beforeEach(() => vi.useFakeTimers())
  it("shows nothing for 150 ms, then the shape, never a spinner", () => {
    const { container } = render(<Skeleton shape="tripCard" />)
    expect(container.firstChild).toBeNull()
    act(() => void vi.advanceTimersByTime(149))
    expect(container.firstChild).toBeNull()
    act(() => void vi.advanceTimersByTime(1))
    expect(screen.getByRole("status", { name: "Loading" })).toHaveAttribute("aria-busy", "true")
    expect(container.querySelector(".h-btn__spin")).toBeNull()
  })
  it.each(["lines", "block", "tripCard", "dayCard"] as const)("draws the %s shape", (shape) => {
    const { container } = render(<Skeleton shape={shape} delayMs={0} />)
    act(() => void vi.advanceTimersByTime(0))
    expect(container.querySelectorAll(".state-skel").length).toBeGreaterThan(0)
  })
  it("after 8 seconds becomes the error state with retry", () => {
    const onRetry = vi.fn()
    render(<Skeleton shape="lines" onRetry={onRetry} />)
    act(() => void vi.advanceTimersByTime(7_999))
    expect(screen.queryByRole("alert")).toBeNull()
    act(() => void vi.advanceTimersByTime(1))
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong on our side.")
    fireEvent.click(screen.getByRole("button", { name: "Try again" }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
  it("says offline when the timeout hits while offline", () => {
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
    render(<Skeleton shape="lines" />)
    act(() => void vi.advanceTimersByTime(8_000))
    expect(screen.getByRole("alert")).toHaveTextContent("You are offline.")
  })
})
