import { Link, Navigate } from "react-router"
import { Icon, RoutePattern } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { isOnboarded, useMe, useTrips, type TripSummary } from "../onboarding/trips"
import { TripCard, tripStatus } from "./TripCard"
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

/** 05 6.5: sections of trip cards, and the loading, empty, error and offline states. Swipe actions and the "+" menu come with WF-019.3. */
export function TripsHome() {
  const { token, persona } = useAuth()
  const online = useOnline()
  // Dev personas are bootstrapped by the API. A real sign-in is checked once with GET /me: an existing user goes
  // straight to Trips, a new one goes through the age gate and profile first.
  const check = !!token && !persona && !isOnboarded()
  const me = useMe(token, check)
  const ready = !check || me.data === true
  const trips = useTrips(!!token && ready)
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
      {(check ? me.isPending : trips.isPending) && (
        <>
          <p className="h-soft" aria-live="polite">
            {t("trips.loading")}
          </p>
          <div className="trips__list trips__section">
            {[0, 1, 2].map((i) => (
              <div key={i} className="trips__skel" aria-hidden="true" />
            ))}
          </div>
        </>
      )}
      {(trips.isError || me.isError) && (
        <div className="trips__stack">
          <p role="alert" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("trips.error")}
          </p>
          <button type="button" className="h-btn h-btn--secondary" onClick={() => void (me.isError ? me.refetch() : trips.refetch())}>
            {t("trips.retry")}
          </button>
        </div>
      )}
      {trips.data?.length === 0 && (
        <section className="trips__empty">
          <RoutePattern a="M10 70 C60 10 120 10 170 50" b="M10 90 C70 40 130 60 170 50" viewBox="0 0 180 100" className="trips__route" />
          <h2 className="h-heading">{t("trips.emptyTitle")}</h2>
          <p className="h-soft">{t("trips.emptyBody")}</p>
          <Link to="/trips/new" className="h-btn h-btn--primary">
            {t("trips.newTrip")}
          </Link>
        </section>
      )}
      {group(trips.data ?? []).map((s) => (
        <section key={s.key} className="trips__section" aria-labelledby={`trips-${s.key}`}>
          <h2 className="h-heading h-heading--section" id={`trips-${s.key}`}>
            {t(s.title)}
          </h2>
          <ul className="trips__list">
            {s.trips.map((tr) => (
              <li key={tr.id}>
                <TripCard trip={tr} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </AppShell>
  )
}
