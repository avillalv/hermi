import { useState } from "react"
import { Navigate, useNavigate, useParams } from "react-router"
import { EmptyState } from "../../components/EmptyState"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Btn, Icon, SegItem, SegmentedControl } from "../../components/kit"
import { formatDateRange } from "../../lib/dates"
import { t } from "../../lib/i18n"
import { formatDuration, formatMoney } from "../../lib/money"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { useTrip } from "../trips/api"
import { tripStrip } from "../trips/TripStrip"
import "../trips/trips.css"
import { AddRoute } from "./AddRoute"
import { AlertList, AlertSwitch } from "./Alerts"
import { chooseFare, refreshRoute, useAirportsPerSide, useOptions, useRoutes, useSummary, type Fare, type FareSort, type Route, type RouteSummary } from "./api"
import { DateGrid } from "./DateGrid"
import { PriceChart } from "./PriceChart"
import "./flights.css"

/** 05 4.5 source tags are Live, Cached, Agent and Google history; an indicative fare is an agent one. */
export const tagOf = (f: Fare) => (f.confidence === "indicative" ? "agent" : f.confidence) as "live" | "cached" | "agent" | "google"
export const ageOf = (f: Fare) => (f.age_label.startsWith(f.confidence) ? f.age_label.slice(f.confidence.length).trim() : f.age_label)
const STALE_MS = 24 * 3600_000
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
const stopsText = (n: number | null) => (n === null ? "" : n === 0 ? t("flights.nonstop") : n === 1 ? t("flights.stop") : t("flights.stops", { n }))
const routeName = (r: Route) => `${r.origin_codes.join(", ")} ${t("flights.to").toLowerCase()} ${r.destination_codes.join(", ")}`

/** 05 4.5 fare chip: code, price in mono, source tag and age. Stale (over 24 h) adds a clock and "Check again". Says "Lowest in this list" only on the computed minimum. */
function FareChip({ fare, lowest }: { fare: Fare; lowest?: boolean }) {
  const stale = Date.now() - Date.parse(fare.observed_at) > STALE_MS
  const age = ageOf(fare)
  const kind = tagOf(fare)
  const nav = useNavigate()
  const { id = "" } = useParams()
  return (
    <>
      {lowest && <span className="h-label">{t("flights.lowest")}</span>}
      <button type="button" className={`flights__chip${stale ? " flights__chip--stale" : ""}`} onClick={() => {
          track("fare_chip_tapped", { source: kind })
          nav(`/trips/${id}/flights/${fare.route_id}/fares/${fare.id}`, { state: { fare } })
        }}
      >
        <span className="h-mono flights__code">{fare.destination}</span>
        <span className="h-mono">{formatMoney(fare.price.amount_minor, fare.price.currency)}</span>
        <span className={`flights__tag flights__tag--${kind}`}>{cap(kind)}</span>
        <span>{age}</span>
        {stale && (
          <>
            <Icon name="clock" size={14} />
            <span>{t("flights.stale")}</span>
          </>
        )}
      </button>
    </>
  )
}

const SORTS: { key: FareSort; label: string; said: string }[] = [
  { key: "price", label: "flights.sortPrice", said: "flights.sortedPrice" },
  { key: "duration", label: "flights.sortDuration", said: "flights.sortedDuration" },
  { key: "stops", label: "flights.sortStops", said: "flights.sortedStops" },
]

function Options({ tripId, route, chosen, canEdit, online }: { tripId: string; route: Route; chosen: string | undefined; canEdit: boolean; online: boolean }) {
  const [sort, setSort] = useState<FareSort>("price")
  const [failed, setFailed] = useState(false)
  const q = useOptions(tripId, route.id, sort, true)
  const pick = async (id: string) => setFailed(!(await chooseFare(tripId, route.id, id)).ok)
  return (
    <div className="flights__options">
      <SegmentedControl aria-label={t("flights.sortBy")}>
        {SORTS.map((s) => (
          <SegItem key={s.key} selected={sort === s.key} onClick={() => setSort(s.key)}>
            {t(s.label)}
          </SegItem>
        ))}
      </SegmentedControl>
      <p className="h-soft">{t(SORTS.find((s) => s.key === sort)!.said)}</p>
      {q.isPending && <div className="flights__chartskel" aria-hidden="true" />}
      {q.isError && !q.data && (
        <p role="alert" className="h-soft">
          {t("flights.optionsError")}
        </p>
      )}
      {q.data?.length === 0 && <p className="h-soft">{t("flights.optionsEmpty")}</p>}
      {failed && (
        <p role="alert" className="h-input__error">
          {t("flights.chooseFailed")}
        </p>
      )}
      <ul className="flights__list">
        {q.data?.map((f) => (
          <li key={f.id} className="flights__fare">
            <FareChip fare={f} />
            <span className="flights__meta">
              {[f.airlines.join(", "), f.depart_at_local?.slice(11, 16), formatDuration(f.duration_out_min), stopsText(f.stops_out)].filter(Boolean).join(", ")}
            </span>
            {chosen === f.id ? (
              <span className="h-chip">{t("flights.chosen")}</span>
            ) : (
              canEdit && (
                <Btn variant="secondary" mod={["sm"]} disabled={!online} onClick={() => void pick(f.id)}>
                  {t("flights.choose")}
                </Btn>
              )
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

type View = "chart" | "grid" | "options"

/** One route card (05 6.9): codes, window, travelers, chips, then Chart, Grid or Options. */
function RouteCard({ tripId, route, sum, canEdit, online, home }: { home: string; tripId: string; route: Route; sum: RouteSummary | undefined; canEdit: boolean; online: boolean }) {
  const [view, setView] = useState<View>("chart")
  const [busy, setBusy] = useState(false)
  const [checkFail, setCheckFail] = useState<"failed" | "rate" | null>(null)
  const cheapest = sum?.cheapest ?? null
  const dates = formatDateRange(route.depart_from, route.return_to ?? route.depart_to)
  const people = route.adults + route.children
  return (
    <article className="h-listcard flights__card" aria-label={routeName(route)}>
      <header className="flights__head">
        <h2 className="flights__title">{routeName(route)}</h2>
        <p className="h-soft">
          {dates}, {people === 1 ? t("flights.traveler") : t("flights.travelers", { n: people })}
          {route.trip_type === "one_way" && `, ${t("flights.oneWay").toLowerCase()}`}
        </p>
      </header>
      <div className="flights__chips">{cheapest ? <FareChip fare={cheapest} lowest /> : <span className="h-chip">{t("flights.noFare")}</span>}</div>
      <SegmentedControl aria-label={t("flights.views")}>
        {(["chart", "grid", "options"] as View[]).map((v) => (
          <SegItem key={v} selected={view === v} onClick={() => setView(v)}>
            {t(`flights.${v}`)}
          </SegItem>
        ))}
      </SegmentedControl>
      {view === "chart" && <PriceChart tripId={tripId} routeId={route.id} />}
      {view === "grid" && <DateGrid tripId={tripId} routeId={route.id} />}
      {view === "options" && <Options tripId={tripId} route={route} chosen={sum?.chosen?.id} canEdit={canEdit} online={online} />}
      <AlertSwitch tripId={tripId} routeId={route.id} currency={cheapest?.price.currency ?? home} canEdit={canEdit} online={online} />
      <p className="h-soft">{t("flights.disclosure")}</p>
      <p className="h-soft">{t("flights.cachedFrom")}</p>
      {canEdit && (
        <Btn
          variant="secondary"
          busy={busy}
          disabled={!online}
          onClick={async () => {
            setBusy(true)
            const r = await refreshRoute(tripId, route.id)
            setBusy(false)
            setCheckFail(r.ok ? null : r.reason === "rate" ? "rate" : "failed")
          }}
        >
          {t("flights.checkNow")}
        </Btn>
      )}
      {checkFail && (
        <p role="alert" className="h-input__error">
          {t(checkFail === "rate" ? "flights.checkLimited" : "flights.checkFailed")}
        </p>
      )}
    </article>
  )
}

/** 05 6.9 Flights: route cards for the trip with cached fares. Live checks arrive with WF-051; alerts are in Alerts.tsx. */
export function Flights() {
  const { token } = useAuth()
  const { id = "" } = useParams()
  const online = useOnline()
  const nav = useNavigate()
  const [adding, setAdding] = useState(false)
  const trip = useTrip(id, !!token)
  const routes = useRoutes(id, !!token)
  const sums = useSummary(id, !!token)
  const perSide = useAirportsPerSide(!!token)
  if (!token) return <Navigate to="/welcome" replace />
  const canEdit = !!trip.data && trip.data.my_role !== "viewer"
  const failed = (routes.isError && !routes.data) || trip.isError
  const pending = !failed && (routes.isPending || trip.isPending)
  const retry = () => void Promise.all([routes.refetch(), trip.refetch(), sums.refetch()])
  return (
    <AppShell active="trips" strip={tripStrip(nav, id, "flights")}>
      <div className="overview">
        {!online && (
          <p role="status" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("flights.offline")}
          </p>
        )}
        <div className="flights__bar">
          <h1 className="h-title">{t("flights.title")}</h1>
          {canEdit && !adding && (
            <Btn variant="secondary" mod={["sm"]} disabled={!online} onClick={() => setAdding(true)}>
              <Icon name="plus" size={18} />
              {t("flights.addRoute")}
            </Btn>
          )}
        </div>
        {adding && <AddRoute tripId={id} start={trip.data?.start_date ?? null} end={trip.data?.end_date ?? null} maxPerSide={perSide} onClose={() => setAdding(false)} />}
        {pending && <Skeleton shape="routeCard" onRetry={retry} />}
        {failed && <QueryError error={trip.error ?? routes.error} message={t("flights.error")} onRetry={retry} />}
        {routes.data?.length === 0 && !adding && (
          <>
            <EmptyState
              icon="globe"
              title={t("flights.emptyTitle")}
              body={t("flights.emptyBody")}
              action={canEdit && online ? { label: t("flights.addFirst"), onClick: () => setAdding(true) } : undefined}
            />
            {trip.data && !canEdit && <p className="h-soft">{t("flights.viewerNote")}</p>}
          </>
        )}
        {trip.data && routes.data?.map((r) => <RouteCard key={r.id} tripId={id} route={r} sum={sums.data?.find((s) => s.route_id === r.id)} canEdit={canEdit} online={online} home={trip.data.home_currency} />)}
        {canEdit && !!routes.data?.length && <AlertList tripId={id} routes={routes.data} name={routeName} />}
      </div>
    </AppShell>
  )
}
