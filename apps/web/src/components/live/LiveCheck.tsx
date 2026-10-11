import { useEffect, useRef, useState } from "react"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { api } from "../../routes/auth/api"
import { ageText, useEntitlements } from "../../routes/flights/api"
import { Btn, Icon } from "../kit"
import "./live.css"

/** What every live search answers with (04 sections 5.8 and 5.9): the shared cache label, never a guess. */
export type LiveMeta = { cached: boolean; checked_at: string; age_seconds: number; credits_charged: number }
export type LiveFail = "credits" | "limit" | "busy" | "paused" | "rate" | "forbidden" | "failed"
export type LiveOutcome<T> = { ok: true; data: T } | { ok: false; reason: LiveFail; message?: string }

// shortcut: hand-written from apps/api/hermi/modules/flights/router.py and lodging/router.py until `npm run gen:api` is real.
/** POST one live search. `key` is the Idempotency-Key, one per tap, kept only until an answer comes back. */
export async function postLive<T extends LiveMeta>(path: string, body: unknown, key: string): Promise<LiveOutcome<T>> {
  try {
    const r = await api.post<T>(path, body, { headers: { "Idempotency-Key": key } })
    const s = r.response.status
    const e = (r.error ?? {}) as { code?: string; detail?: string }
    if (s === 402) return e.code === "limit_reached" ? { ok: false, reason: "limit", message: e.detail } : { ok: false, reason: "credits" }
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (s === 429) return { ok: false, reason: "rate" }
    if (s === 503 && e.code === "live_search_busy") return { ok: false, reason: "busy" }
    if (s === 503 && e.code === "feature_disabled") return { ok: false, reason: "paused" }
    if (r.error !== undefined || r.data === undefined) return { ok: false, reason: "failed" }
    return { ok: true, data: r.data }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

/** Whether `serpapi_live_fares` is on for this person. Off (or still loading) hides every live control. */
export const useLiveSearchOn = (on: boolean) => useEntitlements(on)?.flags?.live_search === true

/** "From a shared check 2 h ago, free", or "Checked just now, 1 credit used". */
export function resultLabel(m: LiveMeta): string {
  if (m.cached) return t("live.cached", { age: ageText(new Date(Date.now() - m.age_seconds * 1000).toISOString()) })
  return t(m.credits_charged > 0 ? "live.fresh" : "live.freshFree")
}

type Props<T extends LiveMeta> = {
  /** Names the control for a screen reader: "Live check: JFK to LIS". */
  subject: string
  search: (key: string) => Promise<LiveOutcome<T>>
  onResult: (data: T) => void
  /** Whether the answer had nothing in it (a free, empty result says so). */
  isEmpty?: (data: T) => boolean
  /** The provider-down sentence: fares and rentals each have their own (05 6.9). */
  pausedKey?: "live.paused" | "live.pausedRentals"
}

/**
 * 05 6.9 and 6.11 "Live check, 1 credit": one tap shows the price, a second confirms it. The label under it says whether
 * the answer was fresh (1 credit) or a shared check under 6 hours old (free). The caller renders the data and mounts this
 * only when `useLiveSearchOn` is true and the person can edit.
 */
export function LiveCheck<T extends LiveMeta>({ subject, search, onResult, isEmpty, pausedKey = "live.paused" }: Props<T>) {
  const online = useOnline()
  const key = useRef<string | null>(null)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [label, setLabel] = useState<string | null>(null)
  const [error, setError] = useState<LiveFail | null>(null)
  const [message, setMessage] = useState<string | undefined>()
  const box = useRef<HTMLDivElement>(null)
  const moved = useRef(false)
  useEffect(() => {
    if (!moved.current) return void (moved.current = true) // not on first render
    box.current?.querySelector<HTMLElement>(confirm ? ".live__actions button" : ":scope > button")?.focus() // Use 1 credit on open, the trigger on cancel
  }, [confirm])

  const go = async () => {
    if (busy) return
    key.current ??= crypto.randomUUID()
    setBusy(true)
    setError(null)
    const r = await search(key.current)
    setBusy(false)
    if (!r.ok) {
      if (r.reason !== "failed") key.current = null // a refusal is final; only a failed call keeps its key for a retry
      // shortcut: the 0 credit state shows inline text until the `out_of_credits_verify` paywall exists (WF-132)
      setLabel(null)
      setMessage(r.message)
      return setError(r.reason)
    }
    key.current = null
    setConfirm(false)
    track("ai_action_started", { action: "live_search", credits: r.data.credits_charged, from_cache: r.data.cached })
    setLabel(isEmpty?.(r.data) ? t("live.none") : resultLabel(r.data))
    onResult(r.data)
  }

  return (
    <div className="live" ref={box}>
      {confirm ? (
        <div role="group" aria-label={t("live.confirmTitle")} className="live__confirm">
          <p>{t("live.confirmBody")}</p>
          <div className="live__actions">
            <Btn variant="primary" busy={busy} disabled={!online} onClick={() => void go()}>
              {busy ? t("live.checking") : t("live.confirm")}
            </Btn>
            <Btn variant="secondary" disabled={busy} onClick={() => setConfirm(false)}>
              {t("live.cancel")}
            </Btn>
          </div>
        </div>
      ) : (
        <Btn variant="secondary" disabled={!online} aria-label={t("live.buttonAria", { subject })} onClick={() => { setError(null); setConfirm(true) }}>
          {t("live.button")}
          <span className="h-credit">
            <Icon name="coins" size={14} />
            <span className="h-credit__n">1</span> {t("live.credit")}
          </span>
        </Btn>
      )}
      {!online && <p role="status" className="h-soft">{t("live.offline")}</p>}
      {label && <p role="status" className="h-soft live__label">{label}</p>}
      {error && (
        <p role="alert" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {error === "limit" && message ? message : error === "paused" ? t(pausedKey) : t(`live.${error}`)}
        </p>
      )}
    </div>
  )
}
