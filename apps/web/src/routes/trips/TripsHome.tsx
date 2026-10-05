import { useEffect, useState } from "react"
import { Link, Navigate, useLocation, useNavigate } from "react-router"
import { EmptyState } from "../../components/EmptyState"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { isOnboarded, useMe, useTrips, type TripSummary } from "../onboarding/trips"
import { TripCard, tripStatus } from "./TripCard"
import { NoticeBar, TripActions, type Notice } from "./TripActions"
import "./trips.css"

const SECTIONS = [
  { key: "now", title: "trips.sectionNow" },
  { key: "upcoming", title: "trips.sectionUpcoming" },
  { key: "shared", title: "trips.sectionShared" },
  { key: "past", title: "trips.sectionPast" },
] as const
type Key = (typeof SECTIONS)[number]["key"]

const bucket = (tr: TripSummary): Key => {
  const s = tripStatus(tr)
  return s.past ? "past" : tr.my_role !== "owner" ? "shared" : s.now ? "now" : "upcoming"
}

/** Fixed, never commission related (05 6.5): upcoming ascending by start date, past descending by end date, undated last. */
const byDate = (key: Key) => (a: TripSummary, b: TripSummary) => {
  const [x, y] = key === "past" ? [a.end_date, b.end_date] : [a.start_date, b.start_date]
  if (x === y) return 0
  if (!x) return 1
  if (!y) return -1
  return key === "past" ? y.localeCompare(x) : x.localeCompare(y)
}

export const group = (trips: TripSummary[]) =>
  SECTIONS.map((s) => ({ ...s, trips: trips.filter((tr) => bucket(tr) === s.key).sort(byDate(s.key)) })).filter((s) => s.trips.length > 0)

/** 05 6.5: sections of trip cards, and the loading, empty, error and offline states. Per-card actions are a button, the tap alternative to swipe and long press. The "+" menu and the limit line come with the paywall and import tickets. */
export function TripsHome() {
  const { token, persona } = useAuth()
  // Arriving from a trip that was just moved to trash (Overview) shows the same Undo line.
  const arrived = (useLocation().state as { trashed?: { id: string; name: string } } | null)?.trashed
  const nav = useNavigate()
  const [notice, setNotice] = useState<Notice | null>(arrived ? { kind: "trashed", id: arrived.id, text: t("trips.noticeTrashed", { name: arrived.name }) } : null)
  const online = useOnline()
  // Dev personas are bootstrapped by the API. A real sign-in is checked once with GET /me: an existing user goes
  // straight to Trips, a new one goes through the age gate and profile first.
  // Read once, then clear it from history so a reload or Back does not show the Undo line again.
  useEffect(() => {
    if (arrived) nav(".", { replace: true, state: null })
  }, [arrived, nav])
  const check = !!token && !persona && !isOnboarded()
  const me = useMe(token, check)
  const ready = !check || me.data === true
  const trips = useTrips(!!token && ready)
  const retry = () => void (me.isError ? me.refetch() : trips.refetch())
  if (!token) return <Navigate to="/welcome" replace />
  if (check && me.data === false) return <Navigate to="/onboarding" replace />

  return (
    <AppShell active="trips">
      <header className="h-pagehead">
        <div className="h-pagehead__text">
          <h1 className="h-pagehead__title">{t("trips.title")}</h1>
        </div>
        <Link to="/trips/new" className="h-btn h-btn--primary h-btn--icon" aria-label={t("trips.newTrip")}>
          <Icon name="plus" bold />
        </Link>
      </header>
      {!online && (
        <p role="status" className="h-input__error trips__note">
          <Icon name="circle-alert" size={16} />
          {t("trips.offline")}
        </p>
      )}
      <NoticeBar notice={notice} onChange={setNotice} />
      {(check ? me.isPending : trips.isPending) && <Skeleton shape="tripCard" count={3} onRetry={retry} />}
      {(trips.isError || me.isError) && <QueryError error={me.isError ? me.error : trips.error} message={t("trips.error")} onRetry={retry} />}
      {trips.data?.length === 0 && (
        <EmptyState
          icon="luggage"
          title={t("trips.emptyTitle")}
          body={t("trips.emptyBody")}
          action={{ label: t("trips.newTrip"), onClick: () => nav("/trips/new") }}
        />
      )}
      {group(trips.data ?? []).map((s) => (
        <section key={s.key} className="trips__section" aria-labelledby={`trips-${s.key}`}>
          <h2 className="h-heading h-heading--section" id={`trips-${s.key}`}>
            {t(s.title)}
          </h2>
          <ul className="trips__list">
            {s.trips.map((tr) => (
              <li key={tr.id} className="trips__item">
                <TripCard trip={tr} />
                <TripActions trip={tr} role={tr.my_role} label={t("trips.actionsFor", { name: tr.name })} notify={setNotice} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </AppShell>
  )
}
