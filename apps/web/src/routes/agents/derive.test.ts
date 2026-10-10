import { expect, test } from "vitest"
import { buildView, estimateStopCredits, reasonOf, type RunEvent } from "./derive"

const ev = (seq: number, type: RunEvent["type"], summary = "", payload: RunEvent["payload"] = null, tool_name: string | null = null): RunEvent => ({
  seq, ts: `2027-03-01T10:00:${String(seq).padStart(2, "0")}Z`, type, tool_name, summary, payload,
})

test("findings come from saved events; rejections go to notSaved; stage follows the latest tool", () => {
  const v = buildView([
    ev(0, "run.started"),
    ev(1, "tool.search", "Searching flights", null, "web_search"),
    ev(2, "tool.fetch", "Reading a page", null, "web_fetch"),
    ev(3, "fare.saved", "Saved JFK to LIS", { source_url: "https://kayak.com/x", seen_on: "kayak.com", origin: "JFK", destination: "LIS", price_total: "398.00", currency: "USD" }),
    ev(4, "note.saved", "Saved note", { title: "Tram 28", source_urls: ["https://lisbon-guide.org/t"] }),
    ev(5, "fare.rejected", "rejected", { errors: ["the price is not on the page you fetched"] }),
  ])
  expect(v.fares).toHaveLength(1)
  expect(v.fares[0]).toMatchObject({ kind: "fare", url: "https://kayak.com/x", site: "kayak.com", priceMinor: 39800, currency: "USD" })
  expect(v.notes[0]).toMatchObject({ kind: "note", title: "Tram 28", url: "https://lisbon-guide.org/t" })
  expect(v.notSaved).toEqual([{ seq: 5, reason: "Page did not show that fare" }])
  expect(v.stage).toBe(3)
  expect(v.finished).toBe(false)
})

test("run.finished marks the view finished and the last stage done", () => {
  const v = buildView([ev(0, "run.started"), ev(9, "run.finished", "", { status: "succeeded" })])
  expect(v.finished).toBe(true)
  expect(v.stage).toBe(4)
})

test("reasons map to the 05 6.16 wording and fall back to a plain sentence", () => {
  expect(reasonOf(["a note needs at least one source link"])).toBe("No page link")
  expect(reasonOf(["source_url cited a page you did not open in this run"])).toBe("Page was not opened in this run")
  expect(reasonOf(["departure is in the past"])).toBe("Did not pass the checks")
})

test("stop estimate is pro rata by turns, at least 8, never above what was reserved", () => {
  expect(estimateStopCredits({ reserved: 40, turns: 7 })).toBe(14)
  expect(estimateStopCredits({ reserved: 40, turns: 1 })).toBe(8)
  expect(estimateStopCredits({ reserved: 8, turns: 15 })).toBe(8)
  expect(estimateStopCredits({ reserved: 40, turns: 30 })).toBe(40)
})
