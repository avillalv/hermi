import type { ReactNode } from "react"
import { Link, Navigate, useParams } from "react-router"
import { creditPrice, type CreditAction } from "../../../../../packages/shared/src/credits"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { AiOffNotice, CreditChip, useAiConsent, useAiConsentGate, useCredits, type Credits } from "../../components/ai"
import { Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { useTrip, type Trip } from "../trips/api"
import "../../components/ai/ai.css"

export type Frame = {
  tripId: string
  trip: Trip
  credits: Credits | undefined
  price: number
  /** The price chip with the pool that pays, for the action button and its accessible name. */
  chip: ReactNode
  /** Online, allowed to edit, AI on, not blocked: the action button may be pressed. */
  canRun: boolean
  /** Consent first (the gate resumes `go` on Allow), then `go`. An unknown answer asks, never skips. */
  start: (go: () => void) => void
  openGate: (go: () => void) => void
}

/**
 * The shell every AI result screen shares (05 6.15): title and back link, then the states that stop an action before it
 * starts (loading the trip, error, offline, viewer, AI off, refund debt), the consent gate, and the credit chip. The
 * screen itself is the render prop and only runs when the person may.
 */
export function ActionFrame({ action, title, children }: { action: CreditAction; title: string; children: (f: Frame) => ReactNode }) {
  const { token } = useAuth()
  const { id = "" } = useParams()
  const online = useOnline()
  const trip = useTrip(id, !!token)
  const credits = useCredits(id, !!token)
  const consent = useAiConsent(!!token && trip.data?.my_role !== "viewer")
  const gate = useAiConsentGate()
  if (!token) return <Navigate to="/welcome" replace />

  const t0 = trip.data
  const viewer = t0?.my_role === "viewer"
  const aiOff = t0?.ai_enabled === false
  const c = credits.data
  const price = creditPrice(action)
  const canRun = !!t0 && !viewer && !aiOff && online && !c?.blocked
  const chip = <CreditChip credits={price} available={c?.available} payer={c?.payer} />
  const start = (go: () => void) => (consent.granted === true ? go() : gate.request(go))
  const back = `/trips/${encodeURIComponent(id)}`

  return (
    <AppShell active="trips">
      <div className="overview ai-screen">
        <Link className="h-btn h-btn--text h-btn--sm" to={`${back}/ai`}>
          <Icon name="chevron-left" size={16} />
          {t("ai.act.back")}
        </Link>
        <h1 className="h-title">{title}</h1>
        {c && (
          <p className="h-soft">
            {t("ai.act.balance", { credits: c.available })} {t(c.payer === "trip_pass" ? "ai.pool.tripPass" : "ai.pool.own")}
          </p>
        )}
        {!online && (
          <p role="status" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("ai.sheet.offline")}
          </p>
        )}
        {trip.isPending && <Skeleton shape="lines" />}
        {trip.isError && <QueryError error={trip.error} message={t("ai.act.tripError")} onRetry={() => void trip.refetch()} />}
        {viewer && <p className="h-soft">{t("ai.sheet.viewer")}</p>}
        {aiOff && t0 && <AiOffNotice tripId={id} version={t0.version} isOwner={t0.my_role === "owner"} />}
        {c?.blocked && (
          <p role="status" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("ai.sheet.blocked")}
          </p>
        )}
        {t0 && !viewer && !aiOff && children({ tripId: id, trip: t0, credits: c, price, chip, canRun, start, openGate: gate.request })}
      </div>
      {gate.element}
    </AppShell>
  )
}
