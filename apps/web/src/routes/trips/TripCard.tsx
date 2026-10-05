import { Link } from "react-router"
import { Field, Icon, StatusStub, TicketStub, TripTicket } from "../../components/kit"
import { daysBetween, formatDateRange, parseDate, timingLabel, tripTiming } from "../../lib/dates"
import { t } from "../../lib/i18n"
import type { TripSummary } from "../onboarding/trips"

type Dated = Pick<TripSummary, "status" | "start_date" | "end_date">

/** What the stub says: the status tag and, when the trip has dates, the timing note ("In 2 months", "Day 3 of 7", "Ended 3 weeks ago"). */
export function tripStatus(trip: Dated) {
  const timing = trip.start_date && trip.end_date ? tripTiming(trip.start_date, trip.end_date) : null
  const closed = trip.status === "archived" || trip.status === "done"
  const now = timing?.kind === "ongoing" && !closed
  const past = closed || timing?.kind === "past"
  const tag = now
    ? { key: "planning" as const, label: t("trips.statusNow"), icon: "globe" }
    : trip.status === "archived"
      ? { key: "done" as const, label: t("trips.statusArchived") }
      : trip.status === "done"
        ? { key: "done" as const, label: t("trips.statusDone") }
        : trip.status === "booked"
          ? { key: "booked" as const, label: t("trips.statusBooked") }
          : { key: "planning" as const, label: t("trips.statusPlanning") }
  return { ...tag, now, past, note: timing ? timingLabel(timing) : null }
}

export const when = (trip: Dated) => (trip.start_date && trip.end_date ? formatDateRange(trip.start_date, trip.end_date) : t("trips.datesNone"))
export const nights = (trip: Dated) => (trip.start_date && trip.end_date ? daysBetween(parseDate(trip.start_date), parseDate(trip.end_date)) : null)

/** 05 4.4 trip card: a boarding-pass ticket that is one link. Airport codes, avatars and fares arrive with the flights and group tickets. */
export function TripCard({ trip }: { trip: TripSummary }) {
  const s = tripStatus(trip)
  const n = nights(trip)
  const label = t("trips.cardLabel", { name: trip.name, when: when(trip), count: trip.member_count, status: s.label })
  return (
    <TripTicket as={Link} to={`/trips/${trip.id}`} aria-label={trip.member_count === 1 ? t("trips.cardLabelOne", { name: trip.name, when: when(trip), status: s.label }) : label}>
      <div className="h-ticket__body h-ticket__body--split">
        <div className="h-ticket__id">
          <h3 className="h-ticket__name">{trip.name}</h3>
          <span className="h-ticket__dates">{when(trip)}</span>
        </div>
        <dl className="h-ticket__fields">
          {n !== null && <Field label={t("trips.nights")}>{n}</Field>}
          <Field label={t("trips.travelers")}>{trip.member_count}</Field>
        </dl>
      </div>
      <TicketStub>
        <StatusStub status={s.key} icon={s.icon}>
          {s.label}
        </StatusStub>
        <span className="h-ticket__note">{s.note}</span>
        <Icon name="chevron-right" size={20} className="h-ticket__go" />
      </TicketStub>
    </TripTicket>
  )
}
