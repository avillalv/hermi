import { Link, Navigate } from "react-router"
import { Icon, RoutePattern } from "../../components/kit"
import { formatDateRange } from "../../lib/dates"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { isOnboarded, useMe, useTrips, type TripSummary } from "./trips"
import "./onboarding.css"

const when = (tr: TripSummary) => (tr.start_date && tr.end_date ? formatDateRange(tr.start_date, tr.end_date) : t("trips.datesNone"))

/** 05 6.5, the first slice: the list, loading, empty, error and offline states. Sections and swipe actions come with WF-019. */
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
      <div className="trips__head">
        <h1 className="h-title">{t("trips.title")}</h1>
        <Link to="/trips/new" className="h-btn h-btn--primary h-btn--sm">
          {t("trips.newTrip")}
        </Link>
      </div>
      {!online && (
        <p role="status" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {t("trips.offline")}
        </p>
      )}
      {(check ? me.isPending : trips.isPending) && (
        // shortcut: three plain placeholders and a status line. WF-019 owns the real skeletons and trip tickets (05 6.5).
        <>
          <p className="h-soft" aria-live="polite">
            {t("trips.loading")}
          </p>
          {[0, 1, 2].map((i) => (
            <div key={i} className="trips__card trips__skel" aria-hidden="true" />
          ))}
        </>
      )}
      {(trips.isError || me.isError) && (
        <div className="trips__stack">
          <p role="alert" className="h-input__error">
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
          <h2 className="h-title">{t("trips.emptyTitle")}</h2>
          <p className="h-soft">{t("trips.emptyBody")}</p>
          <Link to="/trips/new" className="h-btn h-btn--primary">
            {t("trips.newTrip")}
          </Link>
        </section>
      )}
      {!!trips.data?.length && (
        <ul className="trips__list" aria-label={t("trips.upcoming")}>
          {trips.data.map((tr) => (
            <li key={tr.id} className="trips__card">
              <strong>{tr.name}</strong>
              <span className="h-soft">
                {tr.destinations_label} · {when(tr)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}
