import { useEffect, useState } from "react"
import { Link } from "react-router"
import { creditPrice, type CreditAction } from "../../../../../packages/shared/src/credits"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { useTaster } from "../../routes/agents/api"
import { useAuth } from "../../routes/auth/authStore"
import { Modal } from "../../routes/itinerary/Modal"
import { useTrip } from "../../routes/trips/api"
import { QueryError } from "../ErrorState"
import { Skeleton } from "../Skeleton"
import { Btn, Icon } from "../kit"
import { useAiConsentGate } from "./AiConsentGate"
import { AiOffNotice } from "./AiOffNotice"
import { CreditChip, creditsLabel } from "./CreditChip"
import { useAiConsent } from "./api"
import { useCredits } from "./useCredits"
import "./ai.css"

/** A confirm step is required at this many credits or more and never auto-confirms (05 4.11). */
export const CONFIRM_AT = 6

export type SheetAction = "explain" | "packing" | "day" | "trip" | "research" | "agent"
/** What the screen that handles a chosen action tells the sheet when it could not start it. */
export type RunOutcome = "rate" | "credits" | "failed"

type Row = { key: SheetAction; action: CreditAction; title: string; desc: string; start: string; cache?: boolean }
const ROWS: Row[] = [
  { key: "day", action: "draft_day", title: "ai.sheet.day", desc: "ai.sheet.dayDesc", start: "ai.sheet.startDay" },
  { key: "trip", action: "draft_trip", title: "ai.sheet.trip", desc: "ai.sheet.tripDesc", start: "ai.sheet.startTrip" },
  { key: "research", action: "research", title: "ai.sheet.research", desc: "ai.sheet.researchDesc", start: "ai.sheet.startResearch", cache: true },
  { key: "agent", action: "agent_run", title: "ai.sheet.agent", desc: "ai.sheet.agentDesc", start: "ai.sheet.startAgent", cache: true },
  { key: "explain", action: "explain", title: "ai.sheet.explain", desc: "ai.sheet.explainDesc", start: "ai.sheet.startExplain" },
  { key: "packing", action: "explain", title: "ai.sheet.packing", desc: "ai.sheet.packingDesc", start: "ai.sheet.startPacking" },
]

const OUTCOME_COPY: Record<RunOutcome, string> = { rate: "ai.sheet.rate", credits: "ai.sheet.short", failed: "ai.sheet.failed" }

/**
 * 05 6.15 the AI sheet: the balance and the pool that pays, one row per action with its price up front, the consent
 * gate on first use, a confirm step at 6 credits or more, and the disabled states (offline, AI off for the trip, viewer).
 * Choosing a row hands the action to `onRun`; what runs and what it shows belongs to the screen behind it (WF-132.2).
 * The agent row goes straight to `onRun`, because its start screen has its own confirm step.
 */
export function AiSheet({
  tripId,
  onClose,
  onRun,
}: {
  tripId: string
  onClose: () => void
  onRun: (a: SheetAction) => void | RunOutcome | Promise<void | RunOutcome>
}) {
  const { token } = useAuth()
  const online = useOnline()
  const trip = useTrip(tripId, !!token)
  const credits = useCredits(tripId, !!token)
  const viewer = trip.data?.my_role === "viewer"
  const aiOff = trip.data?.ai_enabled === false
  const consent = useAiConsent(!!token && !viewer)
  const taster = useTaster(!!token && !!trip.data && !viewer && !aiOff)
  const gate = useAiConsentGate()
  const [picked, setPicked] = useState<SheetAction | null>(null)
  const [outcome, setOutcome] = useState<{ kind: RunOutcome; credits: number } | null>(null)
  useEffect(() => {
    track("ai_sheet_opened")
  }, [])

  const c = credits.data
  const have = c?.available ?? 0
  const blocked = !!c?.blocked
  const disabled = !online || viewer || aiOff || blocked || !c
  const row = ROWS.find((r) => r.key === picked)
  const price = (r: Row) => creditPrice(r.action)
  const freeAgent = (r: Row) => r.key === "agent" && !!taster.data?.available

  const run = async (r: Row) => {
    setPicked(null)
    setOutcome(null)
    const out = await onRun(r.key)
    if (out) setOutcome({ kind: out, credits: price(r) })
  }
  /** Consent first (the gate resumes this same choice on Allow), then the short-balance check, then the confirm step. */
  const choose = (r: Row) => {
    const go = () => {
      setOutcome(null)
      if (!freeAgent(r) && price(r) > have) return setOutcome({ kind: "credits", credits: price(r) })
      if (r.key !== "agent" && price(r) >= CONFIRM_AT) return setPicked(r.key)
      void run(r)
    }
    if (consent.granted !== true) gate.request(go) // unknown (loading or failed) asks, never skips
    else go()
  }

  const left = row ? have - price(row) : 0
  const pool = c?.payer === "trip_pass" ? "ai.pool.tripPass" : "ai.pool.own"
  return (
    <>
      <Modal title={t("ai.sheet.title")} onClose={onClose}>
        <div className="ai-sheet">
          <div className="ai-sheet__bar">
            <span className="h-sheet__sub">{aiOff ? t("ai.tripOff") : t("ai.sheet.on", { trip: trip.data?.name ?? "" })}</span>
            {c && (
              <Link className="h-sheet__balance ai-sheet__balance" to="/account" aria-label={t("ai.sheet.balanceAria", { credits: c.available })}>
                <span className="h-credit h-credit--lg">
                  <Icon name="coins" size={14} />
                  <span className="h-credit__n">{c.available}</span> {t("ai.sheet.balanceText")}
                </span>
                <span className="h-sheet__sub">{t(pool)}</span>
              </Link>
            )}
          </div>
          {!online && (
            <p role="status" className="h-input__error">
              <Icon name="circle-alert" size={16} />
              {t("ai.sheet.offline")}
            </p>
          )}
          {viewer && <p className="h-soft">{t("ai.sheet.viewer")}</p>}
          {aiOff && trip.data && <AiOffNotice tripId={tripId} version={trip.data.version} isOwner={trip.data.my_role === "owner"} />}
          {blocked && (
            <p role="status" className="h-input__error">
              <Icon name="circle-alert" size={16} />
              {t("ai.sheet.blocked")}
            </p>
          )}
          {credits.isPending && <Skeleton shape="lines" />}
          {credits.isError && <QueryError error={credits.error} message={t("ai.sheet.loadError")} onRetry={() => void credits.refetch()} />}
          {c && (
            <div className="h-actionlist" role="group" aria-label={t("ai.sheet.actions")}>
              {ROWS.map((r) => {
                const free = freeAgent(r)
                const chip = { credits: price(r), available: free ? undefined : have, free, payer: c.payer }
                return (
                  <button
                    key={r.key}
                    type="button"
                    className="h-action"
                    aria-pressed={picked === r.key}
                    aria-label={`${t(r.title)}, ${creditsLabel(chip)}`}
                    disabled={disabled}
                    onClick={() => choose(r)}
                  >
                    <span className="h-action__text">
                      <span className="h-action__title">{t(r.title)}</span>
                      <span className={r.cache && !free ? "h-action__desc h-action__desc--cache" : "h-action__desc"}>
                        {free ? t("ai.sheet.agentFree") : r.cache ? t(creditPrice(r.action, true) === 1 ? "ai.sheet.cacheNoteOne" : "ai.sheet.cacheNote", { credits: creditPrice(r.action, true) }) : t(r.desc)}
                      </span>
                    </span>
                    <span className="h-action__side">
                      <CreditChip {...chip} />
                    </span>
                  </button>
                )
              })}
            </div>
          )}
          {outcome && (
            <p role="alert" className="h-input__error">
              <Icon name="circle-alert" size={16} />
              {t(OUTCOME_COPY[outcome.kind], { credits: outcome.credits, available: have })}{" "}
              {outcome.kind === "credits" && <Link to="/account">{t("ai.sheet.seePlans")}</Link>}
            </p>
          )}
          {row && (
            <div className="h-confirm" role="group" aria-labelledby="ai-confirm-h">
              <h3 className="h-confirm__title" id="ai-confirm-h">
                {t("ai.sheet.confirmTitle", { action: t(row.title) })}
              </h3>
              <p className="h-confirm__text">{t("ai.sheet.confirmText", { credits: price(row), balance: have, left })}</p>
              <div className="h-confirm__actions">
                <Btn
                  variant="primary"
                  mod={["spend"]}
                  aria-label={t("ai.sheet.confirmStartAria", { label: t(row.start), credits: price(row) })}
                  onClick={() => void run(row)}
                >
                  {t(row.start)}
                  <CreditChip credits={price(row)} />
                </Btn>
                <Btn variant="secondary" onClick={() => setPicked(null)}>
                  {t("ai.sheet.cancel")}
                </Btn>
              </div>
            </div>
          )}
        </div>
      </Modal>
      {gate.element}
    </>
  )
}
