import type { Handler } from "../onboarding/testing"

export const run = (over: Record<string, unknown> = {}) => ({
  id: "r1", trip_id: "t1", kind: "deep_research", status: "running", started_by: { id: "u1", display_name: "Ana" },
  params: { topic: "Lisbon in March" }, queued_at: "2027-03-01T10:00:00Z", started_at: "2027-03-01T10:00:00Z", finished_at: null,
  summary: null, error_code: null, accepted_count: 0, rejected_count: 0, turns_used: 7, searches_used: 2, fetches_used: 1,
  from_cache: false, is_taster: false, cancel_requested: false, events_url: "/v1/agent-runs/r1/events",
  credits: { action: "agent_run", reserved: 40, charged: null, from_cache: false, balance_after: null }, ...over,
})

export const ev = (seq: number, type: string, summary = "", payload: unknown = null, tool_name: string | null = null) => ({
  seq, ts: `2027-03-01T10:00:${String(seq).padStart(2, "0")}Z`, type, tool_name, summary, payload,
})

export const FARE = ev(3, "fare.saved", "Saved JFK to LIS", { source_url: "https://kayak.com/f", seen_on: "kayak.com", origin: "JFK", destination: "LIS", price_total: "398.00", currency: "USD" })
export const NOTE = ev(4, "note.saved", "Saved note", { title: "Tram 28 is crowded", source_urls: ["https://lisbon-guide.org/t"] })

const enc = new TextEncoder()
/** An SSE response that sends `events` and then ends (or stays open when `open`). */
export const sse = (events: unknown[], open = false) =>
  new Response(
    new ReadableStream({
      start(c) {
        for (const e of events) c.enqueue(enc.encode(`id: ${(e as { seq: number }).seq}\nevent: x\ndata: ${JSON.stringify(e)}\n\n`))
        if (!open) c.close()
      },
    }),
    { headers: { "Content-Type": "text/event-stream" } },
  )

export const trip = (over: Record<string, unknown> = {}) => ({
  id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null, home_currency: "USD", my_role: "owner",
  destinations: [], travelers: [], ...over,
})

export type Over = { run?: unknown; events?: unknown[]; open?: boolean; more?: Handler }
/** Handler for the run screen: the run row, its stream and its polling fallback. */
export const runApi = ({ run: r = run(), events = [], open = false, more }: Over = {}): Handler => (u, i) => {
  const m = i?.method ?? "GET"
  const x = more?.(u, i)
  if (x) return x
  if (u.endsWith("/v1/trips/t1") && m === "GET") return Response.json(trip())
  if (u.endsWith("/v1/agent-runs/r1") && m === "GET") return Response.json(r)
  if (u.endsWith("/v1/agent-runs/r1/stream")) return sse(events, open)
  if (u.includes("/v1/agent-runs/r1/events")) return Response.json(events)
  return undefined
}
