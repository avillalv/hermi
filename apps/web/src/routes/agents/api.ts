import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { ApiError } from "../../lib/api/client"
import { env } from "../../lib/env"
import { SseError, readSse } from "../../lib/api/sse"
import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"
import { authStore } from "../auth/authStore"
import type { RunEvent } from "./derive"

// shortcut: hand-written from apps/api/hermi/modules/ai/router.py until `npm run gen:api` is real.
export type RunKind = "fare_hunt" | "deep_research"
export type RunStatus = "queued" | "running" | "succeeded" | "partial" | "failed" | "timed_out" | "cancelled" | "interrupted"
export type AgentRun = {
  id: string
  trip_id: string
  kind: RunKind
  status: RunStatus
  started_by: { id: string; display_name: string | null } | null
  params: { topic?: string; instructions?: string; route_ids?: string[] }
  queued_at: string
  started_at: string | null
  finished_at: string | null
  summary: string | null
  error_code: string | null
  accepted_count: number
  rejected_count: number
  turns_used: number | null
  searches_used: number | null
  fetches_used: number | null
  from_cache: boolean
  is_taster: boolean
  /** The starter's receipt. Other members get null, which is also how this screen knows who may stop the run. */
  credits: { action: string; reserved: number; charged: number | null; from_cache: boolean; balance_after: number | null } | null
  cancel_requested: boolean
  events_url: string
}
export type Preview = { kind: RunKind; credits: number; price: number; taster: boolean; taster_used: boolean; balance: number; sufficient: boolean; from_cache: boolean }
export type Taster = { used: boolean; used_at: string | null; run_id: string | null; available: boolean; credits: number }
export type StartBody = { kind: RunKind; route_ids?: string[]; topic?: string; instructions?: string }

export const isActive = (s: RunStatus) => s === "queued" || s === "running"

const trip = (id: string) => `/v1/trips/${encodeURIComponent(id)}`
const run = (id: string) => `/v1/agent-runs/${encodeURIComponent(id)}`

function useRead<T>(queryKey: unknown[], path: string, enabled: boolean, query?: Record<string, string>, every?: (d: T | undefined) => number | false) {
  return useQuery(
    {
      queryKey,
      enabled,
      retry: 1,
      refetchInterval: (q) => (every && q.state.status !== "error" ? every(q.state.data as T | undefined) : false), // none after an error or a terminal run
      queryFn: async () => {
        const r = await api.get<T>(path, { query })
        if (r.error !== undefined || r.data === undefined) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )
}

export const useTaster = (on: boolean) => useRead<Taster>(["agents", "taster"], "/v1/me/agent-taster", on)
export const usePreview = (tripId: string, kind: RunKind, on: boolean) =>
  useRead<Preview>(["agents", tripId, "preview", kind], `${trip(tripId)}/agent-runs/preview`, on, { kind })
/** Polls every 3 s while the run is queued or running, so a dropped stream still ends in the right state. */
export const useRun = (runId: string, on: boolean) =>
  useRead<AgentRun>(["agents", "run", runId], run(runId), on, undefined, (d) => (d && !isActive(d.status) ? false : 3000))

export type StartResult =
  | { ok: true; run: AgentRun }
  | { ok: false; reason: "active"; activeRunId?: string }
  | { ok: false; reason: "credits" | "tasterUsed" | "forbidden" | "invalid" | "rate" | "unavailable" | "failed"; message?: string }

/** POST /trips/{id}/agent-runs. `key` is the Idempotency-Key: reuse it when the person retries the same confirm. */
export async function startRun(tripId: string, body: StartBody, key: string): Promise<StartResult> {
  try {
    const r = await api.post<AgentRun>(`${trip(tripId)}/agent-runs`, body, { headers: { "Idempotency-Key": key } })
    const s = r.response.status
    const e = r.error as { code?: string; detail?: string; active_run_id?: string | null } | undefined
    if (s === 409 && e?.code === "run_already_active") return { ok: false, reason: "active", activeRunId: e.active_run_id ?? undefined }
    if (s === 402) return { ok: false, reason: e?.code === "payment_required" ? "tasterUsed" : "credits", message: e?.detail }
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (s === 422) return { ok: false, reason: "invalid", message: e?.detail }
    if (s === 429) return { ok: false, reason: "rate" }
    if (s === 503) return { ok: false, reason: "unavailable" }
    if (r.error !== undefined || !r.data) return { ok: false, reason: "failed" }
    await queryClient.invalidateQueries({ queryKey: ["agents"] })
    return { ok: true, run: r.data }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

export type CancelResult = { ok: true; run: AgentRun } | { ok: false; reason: "forbidden" | "finished" | "failed" }

export async function cancelRun(runId: string): Promise<CancelResult> {
  try {
    const r = await api.post<AgentRun>(`${run(runId)}/cancel`, undefined, { headers: { "Idempotency-Key": crypto.randomUUID() } })
    const s = r.response.status
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (s === 409) {
      await queryClient.invalidateQueries({ queryKey: ["agents", "run", runId] })
      return { ok: false, reason: "finished" }
    }
    if (r.error !== undefined || !r.data) return { ok: false, reason: "failed" }
    queryClient.setQueryData(["agents", "run", runId], r.data)
    return { ok: true, run: r.data }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

type FollowOpts = { onEvents: (e: RunEvent[]) => void; onFinished?: () => void; retryMs?: number; pollMs?: number; fetch?: typeof fetch }

/**
 * Follows a run: the SSE stream with Last-Event-ID resume, and after two stream failures (or a 429 for too many
 * streams) the polling fallback on GET /events?after_seq. Offline it keeps retrying; the run goes on server side.
 * Events arrive once each, ordered by seq. Returns the stop function.
 */
export function followRun(runId: string, { onEvents, onFinished, retryMs = 1500, pollMs = 3000, fetch: f }: FollowOpts): () => void {
  const ctl = new AbortController()
  let after = -1
  let finished = false
  let failures = 0
  const take = (events: RunEvent[]) => {
    const fresh = events.filter((e) => e.seq > after).sort((a, b) => a.seq - b.seq)
    if (!fresh.length) return
    after = fresh[fresh.length - 1]!.seq
    onEvents(fresh)
    if (fresh.some((e) => e.type === "run.finished")) finished = true
  }
  const sleep = (ms: number) =>
    new Promise<void>((done) => {
      const id = setTimeout(done, ms)
      ctl.signal.addEventListener("abort", () => (clearTimeout(id), done()), { once: true })
    })
  void (async () => {
    while (!ctl.signal.aborted && !finished) {
      if (failures < 2) {
        const before = after
        try {
          await readSse(`${env.apiBaseUrl}${run(runId)}/stream`, {
            token: authStore.get().token,
            lastEventId: after >= 0 ? String(after) : undefined,
            signal: ctl.signal,
            fetch: f,
            onMessage: (m) => {
              try {
                take([JSON.parse(m.data) as RunEvent])
              } catch {
                /* a frame that is not a RunEvent is skipped */
              }
            },
          })
          failures = after > before ? 0 : failures + 1
        } catch (e) {
          if (ctl.signal.aborted) return
          failures = e instanceof SseError && e.status === 429 ? 2 : failures + 1
        }
        if (!finished && failures < 2) await sleep(retryMs)
      } else {
        try {
          const r = await api.get<RunEvent[]>(`${run(runId)}/events`, { query: { after_seq: after }, signal: ctl.signal })
          if (r.data) take(r.data)
        } catch {
          /* offline or a blip: the next round tries again */
        }
        if (!finished) await sleep(pollMs)
      }
    }
    if (finished && !ctl.signal.aborted) onFinished?.()
  })()
  return () => ctl.abort()
}

/** The events of a run, live. Resets when `runId` changes. */
export function useRunEvents(runId: string, enabled: boolean): RunEvent[] {
  const [events, setEvents] = useState<RunEvent[]>([])
  useEffect(() => {
    if (!enabled) return
    setEvents([])
    return followRun(runId, {
      onEvents: (e) => setEvents((prev) => [...prev, ...e]),
      onFinished: () => void queryClient.invalidateQueries({ queryKey: ["agents", "run", runId] }),
    })
  }, [runId, enabled])
  return events
}
