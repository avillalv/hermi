import { useEffect, useState } from "react"
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Icon, StatusStub, TicketStub, TripTicket, Field } from "../../components/kit"
import { timingLabel, tripTiming } from "../../lib/dates"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { SyncIndicator } from "../../components/sync-indicator/SyncIndicator"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { useTrip, type Trip } from "./api"
import { nights, tripStatus, when } from "./TripCard"
import { tripStrip } from "./TripStrip"
import { NoticeBar, TripActions, type Notice } from "./TripActions"
import "./trips.css"

/** Local time at a destination from its IANA zone, or null when it has none or the zone is unknown. */
function localTime(timeZone: string | null): string | null {
  if (!timeZone) return null
  try {
    return new Intl.DateTimeFormat(undefined, { timeZone, hour: "numeric", minute: "2-digit" }).format(new Date())
  } catch {
    return null
  }
}

/** 05 6.7 "Happening now": a state of the Overview during the trip dates, not a tab. Items, stay and confirmations join it with the itinerary and lodging tickets. */
function HappeningNow({ trip }: { trip: Trip }) {
  const place = trip.destinations.find((d) => d.timezone) // shortcut: the first destination with a zone; the stop you are at needs the itinerary (WF-032)
  const time = localTime(place?.timezone ?? null)
  const timing = trip.start_date && trip.end_date ? tripTiming(trip.start_date, trip.end_date) : null
  return (
    <section className="h-listcard" aria-labelledby="overview-now">
      <h2 className="h-label h-listcard__title" id="overview-now">
        {t("overview.nowTitle")}
      </h2>
      {timing && (
        <div className="h-listcard__row">
          <span className="h-listcard__text">{timingLabel(timing)}</span>
        </div>
      )}
      {time && place && (
        <div className="h-listcard__row">
          <span className="h-listcard__text">{t("overview.nowLocalTime", { place: place.name })}</span>
          <span className="h-mono">{time}</span>
        </div>
      )}
      <div className="h-listcard__row">
        <span className="h-listcard__text">{t("overview.nowEmpty")}</span>
      </div>
      <Link className="h-listcard__row" to={`/trips/${trip.id}/plan`}>
        <span className="h-listcard__text">{t("overview.nowPlan")}</span>
        <Icon name="chevron-right" size={20} className="h-listcard__go" />
      </Link>
    </section>
  )
}

/** Up to three suggestions derived from missing data (05 6.7). Hidden for viewers. */
function NextSteps({ trip }: { trip: Trip }) {
  const edit = `/trips/${trip.id}/edit`
  const steps = [
    !trip.start_date && { label: t("overview.stepDates"), to: edit },
    !trip.destinations.length && { label: t("overview.stepDestination"), to: edit },
    !!trip.start_date && { label: t("overview.stepPlan"), to: `/trips/${trip.id}/plan` },
  ].filter((s): s is { label: string; to: string } => !!s)
  return (
    <section className="h-listcard" aria-labelledby="overview-next">
      <h2 className="h-label h-listcard__title" id="overview-next">
        {t("overview.nextSteps")}
      </h2>
      {steps.map((s) => (
        <Link key={s.to + s.label} className="h-listcard__row" to={s.to}>
          <Icon name="circle" size={22} className="h-listcard__check" />
          <span className="h-listcard__text">{s.label}</span>
          <Icon name="chevron-right" size={20} className="h-listcard__go" />
        </Link>
      ))}
    </section>
  )
}

function Hero({ trip }: { trip: Trip }) {
  const s = tripStatus(trip)
  const n = nights(trip)
  const zones = [...new Set(trip.destinations.map((d) => d.timezone).filter((z): z is string => !!z))]
  return (
    <TripTicket mod={["sky"]}>
      <div className="h-ticket__head h-ticket__head--sky">
        <div className="h-ticket__top">
          <h1 className="h-ticket__name h-ticket__name--lg">{trip.name}</h1>
          <span className="h-ticket__dates">{when(trip)}</span>
        </div>
        <dl>
          <Field label={t("overview.destinations")} text>
            {trip.destinations.length ? trip.destinations.map((d) => d.name).join(", ") : t("overview.noDestination")}
          </Field>
          {zones.length > 0 && (
            <Field label={t("overview.timezone")} text>
              {zones.join(", ")}
            </Field>
          )}
        </dl>
        <SyncIndicator tripId={trip.id} variant="line" />
      </div>
      <div className="h-ticket__body">
        {n !== null && (
          <dl className="h-ticket__fields">
            <Field label={t("overview.nights")}>{n}</Field>
          </dl>
        )}
      </div>
      <TicketStub>
        <StatusStub status={s.key} icon={s.icon}>
          {s.label}
        </StatusStub>
        <span className="h-ticket__note">{s.note}</span>
      </TicketStub>
    </TripTicket>
  )
}

/** 05 6.7, the first slice: hero pass, Happening now, Next steps, and the loading, error, not found and offline states. */
export function TripOverview() {
  const { token } = useAuth()
  const { id } = useParams()
  const online = useOnline()
  const q = useTrip(id, !!token)
  const nav = useNavigate()
  const addedBy = (useLocation().state as { addedBy?: string } | null)?.addedBy
  // Read once, then clear it from history so a reload or Back does not show the banner again.
  useEffect(() => {
    if (addedBy) nav(".", { replace: true, state: null })
  }, [addedBy, nav])
  const [notice, setNotice] = useState<Notice | null>(addedBy ? { kind: "ok", text: t("invite.landing.added", { name: addedBy }) } : null)
  if (!token) return <Navigate to="/welcome" replace />
  const trip = q.data
  return (
    <AppShell active="trips" strip={id ? tripStrip(nav, id, "overview") : undefined}>
      <div className="overview">
        <Link to="/" className="h-btn h-btn--text h-btn--sm overview__back">
          <Icon name="chevron-left" size={20} />
          {t("overview.back")}
        </Link>
        {!online && (
          <p role="status" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("overview.offline")}
          </p>
        )}
        {q.isPending && <Skeleton shape="overview" onRetry={() => void q.refetch()} />}
        {q.isError && <QueryError error={q.error} message={t("overview.error")} onRetry={() => void q.refetch()} />}
        {trip && (
          <>
            <NoticeBar notice={notice} onChange={setNotice} />
            <Hero trip={trip} />
            {(trip.my_role === "owner" || (trip.my_role === "editor" && trip.editors_can_invite)) && (
              <Link to={`/trips/${trip.id}/group?invite=1`} className="h-btn h-btn--secondary h-btn--sm overview__invite">
                <Icon name="plus" size={18} />
                {t("group.invite")}
              </Link>
            )}
            <TripActions
              trip={trip}
              role={trip.my_role}
              label={t("overview.actions")}
              notify={(n) => (n.kind === "trashed" ? nav("/", { state: { trashed: { id: n.id, name: trip.name } } }) : setNotice(n))}
            />
            {tripStatus(trip).now && <HappeningNow trip={trip} />}
            {trip.my_role !== "viewer" && <NextSteps trip={trip} />}
            <section className="h-listcard" aria-label={t("notes.title")}>
              <Link className="h-listcard__row" to={`/trips/${trip.id}/notes`}>
                <span className="h-listcard__text">{t("notes.link")}</span>
                <Icon name="chevron-right" size={20} className="h-listcard__go" />
              </Link>
            </section>
          </>
        )}
      </div>
    </AppShell>
  )
}
