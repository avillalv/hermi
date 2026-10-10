import { useCallback, useEffect, useRef, useState } from "react"
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router"
import { EvidenceLabel } from "../../components/evidence"
import { Btn, Field, Icon, RoutePath, TextField, TicketStub, TripTicket } from "../../components/kit"
import { formatDateRange } from "../../lib/dates"
import { t } from "../../lib/i18n"
import { formatDuration, formatMoney, toMinor } from "../../lib/money"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { useTrip } from "../trips/api"
import { tripStrip } from "../trips/TripStrip"
import "../trips/trips.css"
import { AlertSwitch } from "./Alerts"
import { ageText, chooseFare, refreshRoute, useHistory, useRoutes, useRouteFares, useSummary, type Fare, type Money } from "./api"
import { PriceChart, daily, shortDay } from "./PriceChart"
import "./flights.css"

const HOUR = 3600_000
const bucket = (h: number) => (h < 6 ? "0-6" : h < 24 ? "6-24" : "24+")
const stopsText = (n: number | null) => (n === null ? "" : n === 0 ? t("flights.nonstop") : n === 1 ? t("flights.stop") : t("flights.stops", { n }))

/** 6.32 "What did you pay?": the total in the fare's currency, Save or Skip. Both mark the flight booked; Skip sends no amount. */
function PaySheet({ currency, travelers, onSave, onClose }: { currency: string; travelers: number; onSave: (paid: Money | null) => Promise<boolean>; onClose: () => void }) {
  const [v, setV] = useState("")
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const first = useRef<HTMLInputElement>(null)
  useEffect(() => {
    first.current?.focus()
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    document.addEventListener("keydown", esc)
    return () => document.removeEventListener("keydown", esc)
  }, [onClose])
  const send = async (paid: Money | null) => {
    setBusy(true)
    setErr((await onSave(paid)) ? null : t("flights.detail.saveFailed"))
    setBusy(false)
  }
  return (
    <form
      className="flights__sheet"
      role="group"
      aria-label={t("flights.detail.payTitle")}
      onSubmit={(e) => {
        e.preventDefault()
        const minor = toMinor(v, currency)
        if (minor === null) return setErr(t("flights.detail.payBad"))
        void send({ amount_minor: minor, currency })
      }}
    >
      <h2 className="h-title">{t("flights.detail.payTitle")}</h2>
      <TextField
        label={travelers === 1 ? t("flights.detail.payLabelOne") : t("flights.detail.payLabel", { n: travelers })}
        helper={`${t("flights.detail.payCurrency")}: ${currency}`}
        inputRef={first}
        inputMode="decimal"
        autoComplete="off"
        value={v}
        error={err}
        onChange={(e) => setV(e.target.value)}
      />
      <p className="h-soft">{t("flights.detail.payNote")}</p>
      <Btn variant="primary" type="submit" busy={busy}>
        {t("flights.detail.paySave")}
      </Btn>
      <Btn variant="secondary" type="button" disabled={busy} onClick={() => void send(null)}>
        {t("flights.detail.paySkip")}
      </Btn>
      <Btn variant="secondary" type="button" disabled={busy} onClick={onClose}>
        {t("flights.cancel")}
      </Btn>
    </form>
  )
}

/** 05 6.10 Fare detail. No partner price or click API exists yet, so Book this fare lists only the airline's site; Explain this fare waits for its AI endpoint. */
export function FareDetail() {
  const { token } = useAuth()
  const { id = "", routeId = "", fareId = "" } = useParams()
  const online = useOnline()
  const nav = useNavigate()
  const on = !!token
  const trip = useTrip(id, on)
  const fares = useRouteFares(id, routeId, on)
  const hist = useHistory(id, routeId, on)
  const routes = useRoutes(id, on)
  const tapped = (useLocation().state as { fare?: Fare } | null)?.fare
  const closeSheet = useCallback(() => {
    setPaying(false)
    document.getElementById("fare-mark")?.focus()
  }, [])
  const sums = useSummary(id, on)
  const [paying, setPaying] = useState(false)
  // shortcut: no read API exposes booked_at yet, so Booked shows for this visit only. Read it from the route once the API returns it.
  const [booked, setBooked] = useState(false)
  const [failed, setFailed] = useState(false)
  const [checking, setChecking] = useState(false)
  // The list read is the first 100 cheapest; a fare past that comes from the tapped chip (router state) instead.
  const fare = fares.data?.items.find((f) => f.id === fareId) ?? (tapped?.id === fareId && tapped.route_id === routeId ? tapped : undefined)
  const viewed = useRef(false)
  useEffect(() => {
    if (!fare || viewed.current) return
    viewed.current = true
    track("fare_detail_viewed", { age_hours_bucket: bucket((Date.now() - Date.parse(fare.observed_at)) / HOUR) })
  }, [fare])
  if (!token) return <Navigate to="/welcome" replace />
  const canEdit = !!trip.data && trip.data.my_role !== "viewer"
  const failedLoad = (fares.isError && !fares.data) || trip.isError
  const pending = !failedLoad && (fares.isPending || trip.isPending)
  const chosen = sums.data?.find((s) => s.route_id === routeId)?.chosen?.id === fareId
  const lowest = !!fare && fares.data?.items.find((f) => !f.hidden && !f.suspect)?.id === fare.id
  const stale = !!fare && Date.now() - Date.parse(fare.observed_at) > 24 * HOUR
  const pts = hist.data ? daily(hist.data) : []
  const delta = pts.length > 1 ? pts[pts.length - 1]!.minor - pts[pts.length - 2]!.minor : null
  const money = (n: number) => formatMoney(n, fare?.price.currency ?? "USD")
  const prevDay = pts.length > 1 ? shortDay(pts[pts.length - 2]!.day) : ""
  const travelers = Math.max(1, fare?.passengers ?? 1)
  const url = fare?.airline_search_url?.startsWith("https://") ? fare.airline_search_url : null
  const age = fare ? ageText(fare.observed_at) : ""
  const cabin = t(`flights.detail.cabin.${routes.data?.find((r) => r.id === routeId)?.cabin ?? "economy"}`)

  const save = async (paid: Money | null) => {
    const r = await chooseFare(id, routeId, fareId, { ...(paid ? { paid } : {}), booked_at: new Date().toISOString() })
    if (r.ok) {
      setBooked(true)
      setPaying(false)
      track("fare_marked_booked", { price_entered: paid !== null })
    }
    return r.ok
  }
  const trend =
    delta === null ? null : delta < 0 ? (
      <span className="h-trend h-trend--down">
        <Icon name="arrow-down" size={16} />
        {t("flights.detail.down", { amount: money(-delta), day: prevDay })}
      </span>
    ) : delta > 0 ? (
      <span className="h-trend h-trend--up">
        <Icon name="arrow-up" size={16} />
        {t("flights.detail.up", { amount: money(delta), day: prevDay })}
      </span>
    ) : (
      <span className="h-trend">{t("flights.detail.flat", { day: prevDay })}</span>
    )

  return (
    <AppShell active="trips" strip={tripStrip(nav, id, "flights")}>
      <div className="overview">
        <Link to={`/trips/${id}/flights`} className="h-soft flights__note">
          <Icon name="chevron-left" size={18} />
          {t("flights.detail.back")}
        </Link>
        {!online && (
          <p role="status" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("flights.offline")}
          </p>
        )}
        {pending && (
          <>
            <p className="h-soft" aria-live="polite">
              {t("flights.detail.loading")}
            </p>
            <div className="flights__skel" aria-hidden="true">
              <div className="flights__chartskel" />
            </div>
          </>
        )}
        {(failedLoad || (fares.data && !fare)) && (
          <div className="trips__stack">
            <p role="alert" className="h-input__error trips__note">
              <Icon name="circle-alert" size={16} />
              {failedLoad ? t("flights.detail.error") : t("flights.detail.notFound")}
            </p>
            {failedLoad && (
              <Btn variant="secondary" onClick={() => void Promise.all([fares.refetch(), trip.refetch()])}>
                {t("trips.retry")}
              </Btn>
            )}
          </div>
        )}
        {fare && (
          <>
            {/* shortcut: the kit map header of 05-fare-detail.html is deferred; add it with the map component. */}
            <TripTicket mod={["fare"]}>
              <section aria-label={`${t("flights.detail.fareLabel")}, ${fare.origin} ${t("flights.to").toLowerCase()} ${fare.destination}, ${formatMoney(fare.price.amount_minor, fare.price.currency)}`}>
                <div className="h-ticket__body h-ticket__body--fare">
                  <h1 className="h-sr-only">
                    {fare.origin} {t("flights.to").toLowerCase()} {fare.destination}, {formatDateRange(fare.depart_date, fare.return_date ?? fare.depart_date)}
                  </h1>
                  <div className="h-codes h-codes--md">
                    <span className="h-codes__code">{fare.origin}</span>
                    <svg className="h-codes__route" viewBox="0 0 140 34" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">
                      <RoutePath traveler="a" size="sm" d="M5 27C26 27 42 11 61 11" />
                      <RoutePath traveler="b" size="sm" d="M79 11C98 11 114 27 135 27" />
                      <circle className="h-codes__start--a" cx="5" cy="27" r="3.4" />
                      <circle className="h-codes__start--b" cx="135" cy="27" r="3.4" />
                      <use className="h-codes__plane" href="#h-plane-path" transform="translate(70 11) rotate(90) scale(.3) translate(-50 -50)" />
                    </svg>
                    <span className="h-codes__code">{fare.destination}</span>
                  </div>
                  <p className="h-soft">
                    {formatDateRange(fare.depart_date, fare.return_date ?? fare.depart_date)}
                    {fare.depart_at_local && `, ${t("flights.detail.leaves").toLowerCase()} ${fare.depart_at_local.slice(11, 16)}`}
                  </p>
                  <dl className="h-ticket__fields">
                    <Field label={t("flights.detail.airline")} text>
                      {fare.airlines.join(", ") || "-"}
                    </Field>
                    <Field label={t("flights.detail.stops")} text>
                      {stopsText(fare.stops_out) || "-"}
                    </Field>
                    <Field label={t("flights.detail.duration")}>{formatDuration(fare.duration_out_min)}</Field>
                  </dl>
                </div>
              </section>
              <TicketStub>
                <div className="h-ticket__figure">
                  <span className="h-label">{t("flights.detail.fareLabel")}</span>
                  <span className="h-figure">{formatMoney(fare.price.amount_minor, fare.price.currency)}</span>
                </div>
                <span className="h-ticket__note h-ticket__note--stack">
                  <span>{travelers === 1 ? t("flights.detail.perAdult", { cabin, age }) : t("flights.detail.perFare", { n: travelers, cabin, age })}</span>
                  {trend}
                </span>
              </TicketStub>
            </TripTicket>
            <section className="flights__card" aria-label={t("flights.detail.fareLabel")}>
              {lowest && <span className="h-label">{t("flights.detail.lowest")}</span>}
              {fare.source === "agent" && (
                <EvidenceLabel kind="fare" url={fare.source_url} site={fare.source_domain} checkedAt={fare.observed_at} runId={fare.run_id ?? undefined} fareId={fare.id} priceMinor={fare.price.amount_minor} currency={fare.price.currency} onOpen={() => track("evidence_opened", { surface: "fare" })} />
              )}
              {stale && (
                <p className="flights__warn">
                  <Icon name="clock" size={16} />
                  {t("flights.detail.staleLine", { age })}
                  {!canEdit && ` ${t("flights.detail.staleCheck")}`}
                  {canEdit && (
                    <Btn
                      variant="secondary"
                      mod={["sm"]}
                      busy={checking}
                      disabled={!online}
                      onClick={async () => {
                        setChecking(true)
                        await refreshRoute(id, routeId)
                        setChecking(false)
                      }}
                    >
                      {t("flights.checkNow")}
                    </Btn>
                  )}
                </p>
              )}
              {canEdit &&
                (booked ? (
                  <div className="flights__row">
                    <span className="h-chip">{t("flights.detail.booked")}</span>
                    <Link to={`/trips/${id}`}>{t("flights.detail.planDays")}</Link>
                  </div>
                ) : (
                  <div className="flights__row">
                    {chosen ? (
                      <span className="h-chip">{t("flights.detail.chosen")}</span>
                    ) : (
                      <Btn variant="primary" disabled={!online} onClick={async () => setFailed(!(await chooseFare(id, routeId, fareId)).ok)}>
                        {t("flights.detail.choose")}
                      </Btn>
                    )}
                    <Btn id="fare-mark" variant="secondary" disabled={!online} onClick={() => setPaying(true)}>
                      {t("flights.detail.markBooked")}
                    </Btn>
                  </div>
                ))}
              <AlertSwitch tripId={id} routeId={routeId} currency={fare.price.currency} canEdit={canEdit} online={online} />
              {failed && (
                <p role="alert" className="h-input__error">
                  {t("flights.chooseFailed")}
                </p>
              )}
              {trip.data && !canEdit && <p className="h-soft">{t("flights.detail.viewerNote")}</p>}
            </section>
            {paying && <PaySheet currency={fare.price.currency} travelers={travelers} onSave={save} onClose={closeSheet} />}
            <PriceChart tripId={id} routeId={routeId} />
            <section className="flights__card" aria-label={t("flights.detail.bookTitle")}>
              <h2 className="h-label">{t("flights.detail.bookTitle")}</h2>
              <p className="h-soft">{t("flights.detail.sortLine")}</p>
              <p className="h-soft">{t("flights.detail.noPartner")}</p>
              <TripTicket mod={["side", "stub-wide"]} role="group" aria-label={`${t("flights.detail.airlineBookName")}, ${fare.airlines.join(", ")}, ${t("flights.detail.airlineRow")}`}>
                <div className="h-ticket__body">
                  <span className="h-provider__name">{t("flights.detail.airlineBookName")}</span>
                  <span className="h-provider__price">{[fare.airlines.join(", "), t("flights.detail.airlineRow")].filter(Boolean).join(", ")}</span>
                </div>
                <TicketStub>
                  {url && online ? (
                    <a className="h-btn h-btn--secondary h-btn--stub h-btn--wrap" href={url} target="_blank" rel="noopener noreferrer" aria-label={t("flights.detail.airlineBookLabel")}>
                      {t("flights.detail.airlineBtn")}
                      <Icon name="external-link" size={14} />
                    </a>
                  ) : (
                    <button type="button" className="h-btn h-btn--secondary h-btn--stub h-btn--wrap" disabled aria-label={t("flights.detail.airlineBookLabel")}>
                      {t("flights.detail.airlineBtn")}
                      <Icon name="external-link" size={14} />
                    </button>
                  )}
                </TicketStub>
              </TripTicket>
              {!online && <p className="h-soft">{t("flights.detail.offlineBook")}</p>}
              <p className="h-soft">{t("flights.disclosure")}</p>
            </section>
          </>
        )}
      </div>
    </AppShell>
  )
}
