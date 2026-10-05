import { expect, test } from "vitest"
import { TRAVELER_COLORS } from "@hermi/tokens"
import css from "@hermi/tokens/tokens.css?raw"

test("TRAVELER_COLORS equals --tp-traveler-1 to 8 in tokens.css", () => {
  const found = TRAVELER_COLORS.map((_, i) => new RegExp(String.raw`--tp-traveler-${i + 1}:\s*(#[0-9A-Fa-f]{6})`).exec(css)?.[1].toUpperCase())
  expect(found).toEqual([...TRAVELER_COLORS])
})
