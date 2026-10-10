import { expect, test, vi } from "vitest"
import { SseError, readSse } from "./sse"

const enc = new TextEncoder()
const body = (...chunks: string[]) =>
  new Response(new ReadableStream({ start(c) { chunks.forEach((x) => c.enqueue(enc.encode(x))); c.close() } }), { headers: { "Content-Type": "text/event-stream" } })

test("frames split across chunks parse into id, event and data; heartbeats are ignored", async () => {
  const f = vi.fn(async () => body(": heartbeat\n\nid: 3\nevent: turn\nda", "ta: {\"seq\":3}\n\n", "id: 4\r\nevent: run.finished\r\ndata: {\"seq\":4}\r\n\r\n"))
  const got: unknown[] = []
  await readSse("http://x/s", { token: "tok", lastEventId: "2", fetch: f as never, onMessage: (m) => got.push(m) })
  expect(got).toEqual([
    { id: "3", event: "turn", data: '{"seq":3}' },
    { id: "4", event: "run.finished", data: '{"seq":4}' },
  ])
  const init = (f.mock.calls[0] as unknown as [string, RequestInit])[1]
  const h = new Headers(init.headers)
  expect(h.get("Authorization")).toBe("Bearer tok")
  expect(h.get("Last-Event-ID")).toBe("2")
  expect(h.get("Accept")).toBe("text/event-stream")
  expect(init.credentials).toBe("omit")
})

test("a non 2xx answer throws SseError with the status", async () => {
  const f = vi.fn(async () => new Response("{}", { status: 429 }))
  await expect(readSse("http://x/s", { token: null, fetch: f as never, onMessage: () => {} })).rejects.toMatchObject({ status: 429 })
  await expect(readSse("http://x/s", { token: null, fetch: f as never, onMessage: () => {} })).rejects.toBeInstanceOf(SseError)
})
