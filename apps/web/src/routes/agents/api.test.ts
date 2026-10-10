import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { reset } from "../onboarding/testing"
import { followRun } from "./api"
import { FARE, ev, sse } from "./testing"

beforeEach(() => reset("free"))
afterEach(() => vi.unstubAllGlobals())

const started = ev(0, "run.started")
const finish = ev(9, "run.finished", "", { status: "succeeded" })

test("a dropped stream reconnects with Last-Event-ID and each event arrives once", async () => {
  const calls: Headers[] = []
  const f = vi.fn(async (_u: string, init?: RequestInit) => {
    calls.push(new Headers(init?.headers))
    return calls.length === 1 ? sse([started, FARE]) : sse([FARE, finish]) // the replay repeats FARE
  })
  const got: number[] = []
  await new Promise<void>((done) => {
    followRun("r1", { fetch: f as never, retryMs: 1, onEvents: (e) => got.push(...e.map((x) => x.seq)), onFinished: done })
  })
  expect(got).toEqual([0, 3, 9])
  expect(calls[0]!.get("Last-Event-ID")).toBeNull()
  expect(calls[1]!.get("Last-Event-ID")).toBe("3")
})

test("two failed streams switch to polling /events with after_seq", async () => {
  const f = vi.fn(async (u: string) => {
    if (u.endsWith("/stream")) return new Response("{}", { status: 500 })
    return Response.json([started, FARE, finish])
  })
  vi.stubGlobal("fetch", f)
  const got: number[] = []
  await new Promise<void>((done) => {
    followRun("r1", { fetch: f as never, retryMs: 1, pollMs: 1, onEvents: (e) => got.push(...e.map((x) => x.seq)), onFinished: done })
  })
  expect(got).toEqual([0, 3, 9])
  expect(f.mock.calls.filter(([u]) => String(u).endsWith("/stream"))).toHaveLength(2)
  expect(f.mock.calls.some(([u]) => String(u).includes("/events?after_seq=-1"))).toBe(true)
})

test("a 429 on the stream goes straight to polling", async () => {
  const f = vi.fn(async (u: string) => (u.endsWith("/stream") ? new Response("{}", { status: 429 }) : Response.json([started, finish])))
  vi.stubGlobal("fetch", f)
  await new Promise<void>((done) => followRun("r1", { fetch: f as never, retryMs: 1, pollMs: 1, onEvents: () => {}, onFinished: done }))
  expect(f.mock.calls.filter(([u]) => String(u).endsWith("/stream"))).toHaveLength(1)
})
