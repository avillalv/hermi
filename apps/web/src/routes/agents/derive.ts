import { AGENT_RUN_MINIMUM_CHARGE, CREDIT_PRICES } from "../../../../../packages/shared/src/credits"

// shortcut: hand-written from apps/api/hermi/modules/ai/router.py until gen:api is real.
export type RunEventType = "run.started" | "turn" | "tool.search" | "tool.fetch" | "fare.saved" | "note.saved" | "fare.rejected" | "budget" | "warning" | "run.finished"
export type RunEvent = { seq: number; ts: string; type: RunEventType; tool_name: string | null; summary: string; payload: Record<string, unknown> | null }

export type Finding = {
  seq: number
  kind: "fare" | "note"
  title: string
  url: string
  site: string
  checkedAt: string
  priceMinor?: number
  currency?: string
}
export type View = {
  fares: Finding[]
  notes: Finding[]
  notSaved: { seq: number; reason: string }[]
  /** Highest stage reached: 0 Searching, 1 Reading, 2 Checking, 3 Saving, 4 Done. -1 before any step. */
  stage: number
  /** Seconds from the first event to the first time each stage was reached. */
  stageAt: Record<number, number>
  turns: number
  finished: boolean
  recent: RunEvent[]
}

const str = (v: unknown) => (typeof v === "string" ? v : "")
const host = (u: string) => {
  try {
    return new URL(u).hostname.replace(/^www\./, "")
  } catch {
    return ""
  }
}

/** The server's ingest errors are written for the model. This maps them to the plain reasons in 05 6.16. */
export function reasonOf(errors: unknown): string {
  const text = Array.isArray(errors) ? errors.map(str).join(" ") : ""
  if (/needs at least one source link|source_url (is|must|missing)|no source/i.test(text)) return "No page link"
  if (/not on the page you fetched/i.test(text)) return "Page did not show that fare"
  if (/did not open in this run/i.test(text)) return "Page was not opened in this run"
  return "Did not pass the checks"
}

/** Folds the event list into what the screen draws. Events are deduplicated by seq, so a replay after a reconnect is safe. */
export function buildView(events: RunEvent[]): View {
  const seen = new Set<number>()
  const v: View = { fares: [], notes: [], notSaved: [], stage: -1, stageAt: {}, turns: 0, finished: false, recent: [] }
  const t0 = events.length ? Date.parse(events[0]!.ts) : 0
  const reach = (stage: number, e: RunEvent) => {
    v.stage = Math.max(v.stage, stage)
    v.stageAt[stage] ??= Math.max(0, Math.round((Date.parse(e.ts) - t0) / 1000))
  }
  let fetched = false
  for (const e of events) {
    if (seen.has(e.seq)) continue
    seen.add(e.seq)
    const p = e.payload ?? {}
    if (e.type === "tool.search") reach(0, e)
    else if (e.type === "tool.fetch") {
      fetched = true
      reach(1, e)
    } else if (e.type === "turn") {
      v.turns = Math.max(v.turns, Number(p.turn) || 0)
      if (fetched) reach(2, e)
    } else if (e.type === "fare.saved") {
      const url = str(p.source_url)
      const major = Number.parseFloat(str(p.price_total))
      const origin = str(p.origin)
      const destination = str(p.destination)
      reach(3, e)
      v.fares.push({
        seq: e.seq, kind: "fare", url, checkedAt: e.ts, site: str(p.seen_on) || host(url),
        title: `${origin} to ${destination}`.trim(),
        priceMinor: Number.isFinite(major) ? Math.round(major * 100) : undefined,
        currency: str(p.currency) || undefined,
      })
    } else if (e.type === "note.saved") {
      const urls = Array.isArray(p.source_urls) ? p.source_urls.map(str).filter(Boolean) : []
      reach(3, e)
      v.notes.push({ seq: e.seq, kind: "note", url: urls[0] ?? "", checkedAt: e.ts, site: host(urls[0] ?? ""), title: str(p.title) || e.summary })
    } else if (e.type === "fare.rejected") v.notSaved.push({ seq: e.seq, reason: reasonOf(p.errors) })
    else if (e.type === "run.finished") {
      v.finished = true
      v.stage = 4
      v.stageAt[4] ??= Math.max(0, Math.round((Date.parse(e.ts) - t0) / 1000))
    }
    if (e.type === "tool.search" || e.type === "tool.fetch" || e.type === "fare.saved" || e.type === "note.saved") v.recent.push(e)
  }
  v.recent = v.recent.slice(-6)
  return v
}

const FULL_PRICE = CREDIT_PRICES.agent_run[0] // table price of an agent run, over MAX_TURNS
// shortcut: the 20 turn cap is repeated from apps/api credits/prices.py (AGENT_RUN_MAX_TURNS). Upgrade when the API sends the estimate.
const MAX_TURNS = 20
const MINIMUM = AGENT_RUN_MINIMUM_CHARGE

/**
 * The credits a stop would bill. Same rule as the server's pro rata settle (minimum 8, never above the reservation),
 * computed from the turns seen so far, so it is an estimate: the server settles on its own turn count.
 */
export function estimateStopCredits({ reserved, turns }: { reserved: number; turns: number }): number {
  return Math.min(reserved, Math.max(MINIMUM, Math.ceil((FULL_PRICE * Math.max(turns, 0)) / MAX_TURNS)))
}

export const mmss = (seconds: number) => {
  const s = Math.max(0, Math.floor(seconds))
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`
}
