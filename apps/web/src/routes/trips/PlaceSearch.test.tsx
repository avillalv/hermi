import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { mockApi, reset } from "../onboarding/testing"
import { PlaceSearch } from "./PlaceSearch"

const place = (name: string) => ({ name, country: "Portugal", lat: 1, lon: 2, timezone: "Europe/Lisbon" })

beforeEach(() => reset("free"))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const setup = () => {
  const onPick = vi.fn()
  const f = mockApi((u) => (u.includes("/v1/geo/destinations") ? Response.json([place("Porto"), place("Portimao")]) : undefined))
  render(<PlaceSearch label="Find" onPick={onPick} />)
  return { onPick, f, input: screen.getByRole("combobox", { name: "Find" }) }
}
const type = async (input: HTMLElement, v: string) => {
  fireEvent.change(input, { target: { value: v } })
  await screen.findByRole("listbox")
}

test("one character does not search; two do, and the attribution shows under the list", async () => {
  const { f, input } = setup()
  fireEvent.change(input, { target: { value: "P" } })
  await new Promise((r) => setTimeout(r, 400))
  expect(f).not.toHaveBeenCalled()
  await type(input, "Po")
  expect(f).toHaveBeenCalledTimes(1)
  expect(screen.getByText("Places by Geoapify, with OpenStreetMap data.")).toBeInTheDocument()
})

test("ArrowDown and ArrowUp move the active option and wrap; Enter picks it", async () => {
  const { onPick, input } = setup()
  await type(input, "Po")
  const [a, b] = screen.getAllByRole("option")
  fireEvent.keyDown(input, { key: "ArrowDown" })
  expect(a).toHaveAttribute("aria-selected", "true")
  expect(input).toHaveAttribute("aria-activedescendant", a.id)
  fireEvent.keyDown(input, { key: "ArrowDown" })
  expect(b).toHaveAttribute("aria-selected", "true")
  fireEvent.keyDown(input, { key: "ArrowDown" })
  expect(a).toHaveAttribute("aria-selected", "true")
  fireEvent.keyDown(input, { key: "ArrowUp" })
  expect(b).toHaveAttribute("aria-selected", "true")
  fireEvent.keyDown(input, { key: "Enter" })
  expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ name: "Portimao", timezone: "Europe/Lisbon" }))
  await waitFor(() => expect(screen.queryByRole("listbox")).not.toBeInTheDocument())
  expect(input).toHaveValue("")
})

test("Enter with no active option picks nothing, and Escape closes the list", async () => {
  const { onPick, input } = setup()
  await type(input, "Po")
  fireEvent.keyDown(input, { key: "Enter" })
  expect(onPick).not.toHaveBeenCalled()
  fireEvent.keyDown(input, { key: "Escape" })
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument()
  expect(input).toHaveAttribute("aria-expanded", "false")
})

test("clicking an option picks it", async () => {
  const { onPick, input } = setup()
  await type(input, "Po")
  fireEvent.click(screen.getByRole("option", { name: "Porto, Portugal" }))
  expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ name: "Porto" }))
})
