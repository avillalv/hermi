import { render, screen } from "@testing-library/react"
import { expect, test } from "vitest"
import { CreditChip, creditsLabel } from "./CreditChip"

test("cost: the coin, the number and the plural word", () => {
  const { container } = render(<CreditChip credits={4} />)
  expect(container.querySelector(".h-credit__n")).toHaveTextContent("4")
  expect(container).toHaveTextContent("4 credits")
  expect(container.querySelector(".h-credit--warn")).toBeNull()
})

test("one credit is singular", () => {
  const { container } = render(<CreditChip credits={1} />)
  expect(container).toHaveTextContent("1 credit")
  expect(container).not.toHaveTextContent("1 credits")
})

test("from cache says so in text", () => {
  render(<CreditChip credits={1} fromCache />)
  expect(screen.getByText("from shared cache")).toBeInTheDocument()
})

test("insufficient warns and says what you have", () => {
  const { container } = render(<CreditChip credits={40} available={12} />)
  expect(container.querySelector(".h-credit--warn")).not.toBeNull()
  expect(screen.getByText("You have 12")).toBeInTheDocument()
})

test("enough credits does not warn", () => {
  const { container } = render(<CreditChip credits={8} available={8} />)
  expect(container.querySelector(".h-credit--warn")).toBeNull()
  expect(screen.queryByText(/You have/)).toBeNull()
})

test("free shows Free and no number", () => {
  const { container } = render(<CreditChip credits={40} free />)
  expect(container).toHaveTextContent("Free")
  expect(container.querySelector(".h-credit__n")).toBeNull()
})

test("the Trip Pass pool is named under the chip", () => {
  render(<CreditChip credits={4} payer="trip_pass" />)
  expect(screen.getByText("Trip Pass credits")).toBeInTheDocument()
})

test("the spoken form carries price, shortfall, cache and pool", () => {
  expect(creditsLabel({ credits: 4 })).toBe("costs 4 credits")
  expect(creditsLabel({ credits: 1 })).toBe("costs 1 credit")
  expect(creditsLabel({ credits: 40, available: 12 })).toBe("costs 40 credits. You have 12")
  expect(creditsLabel({ credits: 1, fromCache: true })).toBe("costs 1 credit, from shared cache")
  expect(creditsLabel({ credits: 4, payer: "trip_pass" })).toBe("costs 4 credits. Trip Pass credits")
  expect(creditsLabel({ credits: 40, free: true })).toBe("free")
})
