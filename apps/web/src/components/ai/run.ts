import { useRef, useState } from "react"
import { queryClient } from "../../lib/queryClient"
import { api } from "../../routes/auth/api"
import { planKey, type Category } from "../../routes/itinerary/api"
import { refreshCredits } from "./useCredits"

// shortcut: hand-written from apps/api/hermi/modules/ai/router.py and features/*.py until `npm run gen:api` is real.
export type Receipt = { action: string; reserved: number; charged: number | null; from_cache: boolean; balance_after: number | null; reservation_id: string | null }
export type Explained = { answer: string; confidence: "high" | "medium" | "low"; needs_source_check: boolean; sources: { url: string; title?: string | null }[]; label: string; run_id: string; credits: Receipt }
export type PackItem = { label: string; group: string; qty: number | null; reason: string | null }
export type Packed = { items: PackItem[]; label: string; run_id: string; credits: Receipt }
export type DraftItem = {
  title: string
  day: string
  start_time: string | null
  end_time: string | null
  category: Category
  status: "idea"
  location_name: string | null
  notes: string
  saved_place_id: string | null
  verify: boolean
}
export type DraftedDay = { day: string; title: string; items: DraftItem[]; rationale: string }
/** What the draft preview shows: a day is a trip draft of one day. */
export type TripDraft = { days: DraftedDay[]; overview?: string; label: string; run_id: string; credits: Receipt }
type DayDraft = DraftedDay & { label: string; run_id: string; credits: Receipt }
type Job = { id: string; kind: "draft_trip"; status: string; result: { days: DraftedDay[]; overview: string; label: string } | null; error_code: string | null; credits: Receipt }

export const RESEARCH_TOPICS = ["destination_brief", "events_and_closures", "reservations_needed", "getting_around", "seasonal_notes"] as const
export type ResearchTopic = (typeof RESEARCH_TOPICS)[number]
export type ResearchNote = { title: string; topic: string; body: string; urls: string[] }
/** The notes of one research run. `from_cache` notes came from the shared cache and are `checked_days_ago` old. */
export type Researched = {
  topic: string
  notes: ResearchNote[]
  sources: { url: string; retrieved_at?: string | null }[]
  from_cache: boolean
  stale: boolean
  checked_days_ago: number | null
  label: string
  run_id: string
  credits: Receipt
}
type ResearchJob = { id: string; kind: "research"; status: string; result: Omit<Researched, "run_id" | "credits"> | null; error_code: string | null; credits: Receipt }

/** Why an AI call did not give a result. `paused` carries the server's own sentence (it names the date AI is back). */
export type Fail = {
  reason: "credits" | "blocked" | "consent" | "aiOff" | "forbidden" | "invalid" | "rate" | "paused" | "unavailable" | "failed"
  message?: string
  retryAfter?: number
  /** No response came back, so the request may have run: a retry keeps its Idempotency-Key and never charges twice. */
  network?: boolean
}
export type Outcome<T> = { ok: true; data: T } | ({ ok: false } & Fail)

/** 422 codes whose server sentence tells the person what to fix (research needs a destination, dates and a short question). */
const USER_FIXABLE = new Set(["destination_required", "dates_required", "invalid_topic", "question_too_long"])
type Problem = { code?: string; detail?: string; message?: string; blocked?: boolean; credits?: { needed: number; balance: number } }

/** POST one AI action. `key` is the Idempotency-Key: one per tap, reused only after a dropped connection. */
export async function postAi<T>(path: string, body: unknown, key: string): Promise<Outcome<T>> {
  try {
    const r = await api.post<T>(path, body, { headers: { "Idempotency-Key": key } })
    const s = r.response.status
    const e = (r.error ?? {}) as Problem
    const message = e.detail ?? e.message
    if (s === 402) return { ok: false, reason: e.blocked ? "blocked" : "credits" }
    if (s === 403) return { ok: false, reason: e.code === "ai_consent_required" ? "consent" : e.code === "ai_disabled_for_trip" ? "aiOff" : "forbidden" }
    if (s === 422 && (e.code === "validation_failed" || USER_FIXABLE.has(e.code ?? ""))) return { ok: false, reason: "invalid", message }
    if (s === 429) {
      if (e.code === "provider_budget_exhausted") return { ok: false, reason: "paused", message }
      const wait = Number(r.response.headers.get("Retry-After"))
      return { ok: false, reason: "rate", retryAfter: wait > 0 ? wait : undefined }
    }
    if (s === 503) return { ok: false, reason: "unavailable" }
    if (r.error !== undefined || r.data === undefined) return { ok: false, reason: "failed" }
    return { ok: true, data: r.data }
  } catch {
    return { ok: false, reason: "failed", network: true }
  }
}

const base = (id: string) => `/v1/trips/${encodeURIComponent(id)}/ai`
export const explain = (id: string, body: { question: string; context?: { item_id?: string; lodging_id?: string; place_id?: string } }, key: string) =>
  postAi<Explained>(`${base(id)}/explain`, body, key)
export const packingList = (id: string, body: { preferences?: string }, key: string) => postAi<Packed>(`${base(id)}/packing-list`, body, key)
export async function draftDay(id: string, body: { day: string; preferences?: string }, key: string): Promise<Outcome<TripDraft>> {
  const r = await postAi<DayDraft>(`${base(id)}/draft-day`, body, key)
  if (!r.ok) return r
  const { day, title, items, rationale, label, run_id, credits } = r.data
  return { ok: true, data: { days: [{ day, title, items, rationale }], label, run_id, credits } }
}
/** 202 with the finished job (the API runs it inline); a job that is not `done` with a result is a failure. */
export async function draftTrip(id: string, body: { style?: string; from_day?: string }, key: string): Promise<Outcome<TripDraft>> {
  const r = await postAi<Job>(`${base(id)}/draft-trip`, body, key)
  if (!r.ok) return r
  const { status, result, credits, id: run_id } = r.data
  return status === "done" && result ? { ok: true, data: { ...result, run_id, credits } } : { ok: false, reason: "failed" }
}

/** 202 with the finished job, like draft-trip. A cache hit charges 1 and has `from_cache`. */
export async function research(id: string, body: { topic: ResearchTopic; question?: string }, key: string): Promise<Outcome<Researched>> {
  const r = await postAi<ResearchJob>(`${base(id)}/research`, body, key)
  if (!r.ok) return r
  const { status, result, credits, id: run_id } = r.data
  return status === "done" && result ? { ok: true, data: { ...result, run_id, credits } } : { ok: false, reason: "failed" }
}

export type SaveResult = { result: "ok" | "forbidden" | "invalid" | "failed"; saved: number }
const BULK = 50 // POST /items/bulk takes at most 50 items; a 14 day draft is sent in blocks
/** POST /items/bulk with `source: ai_draft`: free, one transaction per block. Only the picked items are sent. */
export async function saveDraft(tripId: string, items: DraftItem[]): Promise<SaveResult> {
  let saved = 0
  try {
    for (let at = 0; at < items.length; at += BULK) {
      const body = {
        source: "ai_draft",
        items: items.slice(at, at + BULK).map((i) => ({
          title: i.title, category: i.category, status: i.status, day: i.day, start_time: i.start_time, end_time: i.end_time,
          ...(i.location_name ? { location_name: i.location_name } : {}), notes: i.notes,
        })),
      }
      const r = await api.post(`/v1/trips/${encodeURIComponent(tripId)}/items/bulk`, body)
      const s = r.response.status
      if (s === 403) return { result: "forbidden", saved }
      if (s === 422) return { result: "invalid", saved }
      if (r.error !== undefined) return { result: "failed", saved }
      saved += body.items.length
    }
    return { result: "ok", saved }
  } catch {
    return { result: "failed", saved }
  } finally {
    if (saved > 0) await queryClient.invalidateQueries({ queryKey: planKey(tripId) })
  }
}

export type RunState<T> = { phase: "idle" } | { phase: "running" } | { phase: "done"; data: T } | { phase: "failed"; fail: Fail }

/**
 * One AI call at a time. The Idempotency-Key is made on the tap and kept only while no answer came back, so tapping again
 * after a dropped connection cannot charge twice, and a refusal or a failed run starts clean.
 */
export function useAiRun<T>(send: (key: string) => Promise<Outcome<T>>) {
  const [state, setState] = useState<RunState<T>>({ phase: "idle" })
  const key = useRef<string | null>(null)
  const busy = useRef(false)
  const run = async () => {
    if (busy.current) return
    busy.current = true
    key.current ??= crypto.randomUUID()
    setState({ phase: "running" })
    const r = await send(key.current)
    busy.current = false
    if (r.ok) {
      key.current = null
      setState({ phase: "done", data: r.data })
      void refreshCredits()
    } else {
      if (!r.network) key.current = null
      setState({ phase: "failed", fail: r })
    }
    return r
  }
  const reset = () => {
    key.current = null
    setState({ phase: "idle" })
  }
  return { state, run, reset }
}
