import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"
import { SourceChip } from "./SourceChip"

afterEach(cleanup)
const ago = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString()

test("a fresh source reads Found on site, checked date, and opens the source safely", () => {
  render(<SourceChip url="https://www.example.com/page" site="example.com" checkedAt={ago(2)} />)
  const a = screen.getByRole("link", { name: /example\.com/ })
  expect(a).toHaveAttribute("href", "https://www.example.com/page")
  expect(a).toHaveAttribute("target", "_blank")
  expect(a).toHaveAttribute("rel", "noopener noreferrer")
  expect(a).toHaveTextContent(/Found on example\.com, checked \d+ \w+/)
  expect(screen.queryByText(/May be out of date/)).toBeNull()
})

test("a source checked more than 14 days ago shows the amber stale chip and nothing is hidden", () => {
  const seen = vi.fn()
  window.addEventListener("hermi:event", seen)
  render(<SourceChip url="https://example.com/a" site="example.com" checkedAt={ago(30)} />)
  expect(screen.getByText(/Seen \d+ \w+\. May be out of date\./)).toBeInTheDocument()
  expect(screen.getByRole("link", { name: /example\.com/ })).toBeInTheDocument()
  expect((seen.mock.calls[0][0] as CustomEvent).detail.event).toBe("evidence_stale_shown")
  window.removeEventListener("hermi:event", seen)
})

test("the stale flag from the server also shows the chip", () => {
  render(<SourceChip url="https://example.com/a" site="example.com" checkedAt={ago(1)} stale />)
  expect(screen.getByText(/May be out of date/)).toBeInTheDocument()
})

test("a non-http url is plain text, never a link", () => {
  render(<SourceChip url="javascript:alert(1)" site="example.com" checkedAt={ago(1)} />)
  expect(screen.queryByRole("link")).toBeNull()
  expect(screen.getByText(/Found on example\.com/)).toBeInTheDocument()
})

test("evidence_stale_shown fires once, even when the chip re-renders", () => {
  const seen = vi.fn()
  window.addEventListener("hermi:event", seen)
  const p = { url: "https://example.com/a", site: "example.com", checkedAt: ago(30) }
  const { rerender } = render(<SourceChip {...p} />)
  rerender(<SourceChip {...p} />)
  expect(seen).toHaveBeenCalledTimes(1)
  window.removeEventListener("hermi:event", seen)
})

test("a user note (agent false) never shows the stale chip", () => {
  render(<SourceChip url="https://example.com/a" site="example.com" checkedAt={ago(60)} stale agent={false} />)
  expect(screen.queryByText(/May be out of date/)).toBeNull()
})
