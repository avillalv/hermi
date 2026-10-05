import { useState } from "react"
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router"
import { Avatar, Btn, Icon, SegItem, SegmentedControl, StatusStub, TicketStub, TripTicket } from "../../components/kit"
import { daysBetween, parseDate } from "../../lib/dates"
import { t } from "../../lib/i18n"
import { formatMoney } from "../../lib/money"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { NotFound, useTrip, type Person } from "../trips/api"
import { tone } from "../trips/TripGroup"
import { tripStrip } from "../trips/TripStrip"
import "../trips/trips.css"
import "../itinerary/plan.css"
import { AddStay, type Prefill } from "./AddStay"
import { setHeart, setStatus, SORTS, useMe, useStays, type Sort, type Stay, type Status } from "./api"
import { Bookmarklet } from "./Bookmarklet"
import { Compare } from "./Compare"
import "./stays.css"

const MAX_COMPARE = 4 // 04 5.9: 2 to 4 stays; the plan's own cap (Free compares 2) is enforced by the API
// `site` is the host of the link without "www." (04 5.9), so brands are matched by registrable domain suffix.
const BRANDS: [string, string][] = [["airbnb.", "Airbnb"], ["vrbo.", "Vrbo"], ["booking.", "Booking.com"]]
export const brandOf = (site: string) => { // registrable label only: "airbnb.evil.com" is not Airbnb
  const l = site.split(".")
  const cc = l.length > 2 && l[l.length - 1].length === 2 && l[l.length - 2].length <= 3 // co.uk style
  return BRANDS.find(([k]) => `${l[l.length - (cc ? 3 : 2)]}.` === k)?.[1]
}
const sourceOf = (s: Stay) => (s.site ? brandOf(s.site) ?? s.site : t(`stays.src.${s.added_via === "manual" ? "manual" : "paste"}`))
const web = (url: string) => /^https?:\/\//i.test(url) // only web links become anchors; javascript: and data: stay plain text
const day = (iso: string) => parseDate(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" })
const initials = (name: string) => name.slice(0, 2).toUpperCase()

type Note = { kind: "ok" | "error"; text: string }

const Heart = () => (
  <svg className="h-vote__heart" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <use href="#i-heart" />
  </svg>
)

/** The chips: one per traveler, each an avatar and a heart. Only my own is a button; the others show state (05 4.10: hearts are the only vote). */
function Votes({ stay, travelers, mine, onHeart }: { stay: Stay; travelers: Person[]; mine: boolean; onHeart: (voted: boolean) => void }) {
  const own = travelers.some((p) => p.is_me)
  const button = (key: string, name: string, color: string) => (
    <button key={key} type="button" className={`h-vote h-vote--${tone(color)}`} aria-pressed={mine} aria-label={t("stays.youLoveCard", { title: stay.title })} onClick={() => onHeart(!mine)}>
      <Avatar tone={tone(color)} size="sm">{initials(name)}</Avatar>
      <Heart />
    </button>
  )
  return (
    <div className="h-stay__votes">
      {travelers.map((p) => {
        if (p.is_me) return button(p.id, p.name, p.color)
        const on = stay.votes.some((v) => v.person_id === p.id)
        return (
          <span key={p.id} className={`h-vote h-vote--${tone(p.color)} stays__vote`} data-on={on} role="img" aria-label={t(on ? "stays.likes" : "stays.notLiked", { name: p.name, title: stay.title })}>
            <Avatar tone={tone(p.color)} size="sm">{initials(p.name)}</Avatar>
            <Heart />
          </span>
        )
      })}
      {!own && button("me", t("stays.youName"), "")}
    </div>
  )
}

// shortcut: gaps against the 05 4.10 card and the mockup, each with its trigger. Map header and price pins (the illustrated map ticket);
// the "Price from {date}" age line (needs a price timestamp from the API); the Shortlisted chip (a later polish pass); "Book via partner" (WF-068).
type CardProps = {
  stay: Stay; travelers: Person[]; meId: string | undefined; canEdit: boolean; locked: boolean; booked: boolean
  picked: boolean; pickDisabled: boolean; onPick: () => void; onHeart: (voted: boolean) => void; onStatus: (s: Status) => void
}

function StayCard({ stay, travelers, meId, canEdit, locked, booked, picked, pickDisabled, onPick, onHeart, onStatus }: CardProps) {
  const [names, setNames] = useState(false)
  const night = stay.price_per_night
  const hearts = stay.votes.length
  const of = Math.max(travelers.length, hearts, 1)
  const mine = !!meId && stay.votes.some((v) => v.user_id === meId)
  const who = stay.votes.map((v) => (v.user_id === meId ? t("stays.youName") : travelers.find((p) => p.id === v.person_id)?.name ?? t("stays.formerTraveler")))
  const title = stay.title
  const rejected = stay.status === "rejected"
  const act = (key: string, status: Status, text: string) => (
    <Btn variant="text" mod={["sm"]} disabled={locked} aria-label={t(key, { title })} onClick={() => onStatus(status)}>{text}</Btn>
  )
  const main = (
    <>
      <h3 className="h-stay__name">{title}</h3>
      <span className="h-stay__meta">
        <span className="h-label">{sourceOf(stay)}</span>
        {stay.rating !== null && (
          <span className="h-stay__rating"><Icon name="star" size={14} />{stay.rating.toFixed(1)}</span>
        )}
      </span>
      {stay.status === "booked" && <StatusStub status="booked">{t("stays.bookedBadge")}</StatusStub>}
    </>
  )
  return (
    <article className="stays__item" aria-label={`${title}, ${sourceOf(stay)}${night ? `, ${formatMoney(night.amount_minor, night.currency)} ${t("stays.night")}` : ""}`}>
      <TripTicket mod={["actions"]}>
        <div className="h-ticket__body h-ticket__body--row">
          <div className="h-photo-ph" role="img" aria-label={t("stays.photo")}><Icon name="image" size={22} /><span>{t("stays.photo")}</span></div>
          {stay.url && web(stay.url) ? (
            <a className="h-stay__main" href={stay.url} target="_blank" rel="noopener noreferrer" aria-label={t("stays.openLink", { title })}>{main}</a>
          ) : (
            <div className="h-stay__main">{main}</div>
          )}
          <div className="h-stay__price">
            {night ? (
              <>
                <span className="h-stay__night-row"><span className="h-stay__night">{formatMoney(night.amount_minor, night.currency)}</span><span className="h-soft">{t("stays.night")}</span></span>
                {stay.price_total && <span className="h-stay__total">{t("stays.total", { price: formatMoney(stay.price_total.amount_minor, stay.price_total.currency) })}</span>}
                {stay.price_total && travelers.length > 1 && <span className="h-stay__each">{t("stays.each", { price: formatMoney(Math.round(stay.price_total.amount_minor / travelers.length), stay.price_total.currency) })}</span>}
              </>
            ) : (
              <span className="h-soft">{t("stays.noPrice")}</span>
            )}
          </div>
        </div>
        <TicketStub>
          <button type="button" className="h-stay__count stays__tally" aria-expanded={names} onClick={() => setNames(!names)}>
            {hearts === 0 ? (
              <span className="h-stay__count-n">{t("stays.noOne")}</span>
            ) : (
              <>
                <span className="h-stay__count-n">{t("stays.tally", { n: hearts, m: of })}</span> {t("stays.likeThis")}
              </>
            )}
          </button>
          <Votes stay={stay} travelers={travelers} mine={mine} onHeart={onHeart} />
        </TicketStub>
      </TripTicket>
      {names && hearts > 0 && <p className="h-soft stays__names"><span className="h-sr-only">{t("stays.tallyNames")}: </span>{who.join(", ")}</p>}
      <div className="stays__actions">
        {!rejected && (
          <label className="stays__pick">
            <input type="checkbox" checked={picked} disabled={pickDisabled} aria-label={t("stays.pickToCompare", { title })} onChange={onPick} />
            {t("stays.compare")}
          </label>
        )}
        {canEdit && (
          <>
            {stay.status === "booked" && act("stays.unbook", "shortlisted", t("stays.unbookText"))}
            {!booked && !rejected && act("stays.markBooked", "booked", t("stays.markBookedText"))}
            {stay.status !== "booked" && !rejected && act("stays.reject", "rejected", t("stays.rejectText"))}
            {rejected && act("stays.restore", "shortlisted", t("stays.restoreText"))}
          </>
        )}
      </div>
    </article>
  )
}

/** 05 6.11 Stays: shortlist, compare and vote. */
export function Stays() {
  const { token } = useAuth()
  const { id = "" } = useParams()
  const nav = useNavigate()
  const online = useOnline()
  const [params, setParams] = useSearchParams()
  const trip = useTrip(id, !!token)
  const me = useMe(!!token)
  const [sort, setSort] = useState<Sort>("votes")
  const list = useStays(id, sort, !!token)
  const [view, setView] = useState<"list" | "compare">("list")
  const [picked, setPicked] = useState<string[]>([])
  const [adding, setAdding] = useState(params.get("add") === "1")
  // The paste helper: the bookmarklet sends the page address and title in the query. Nothing is saved until the person confirms.
  const [prefill] = useState<Prefill | null>(() =>
    params.get("add") === "1" && params.get("url") ? { url: params.get("url") ?? "", title: params.get("title") ?? "", via: params.get("via") === "bookmarklet" ? "bookmarklet" : null } : null,
  )
  const [showRejected, setShowRejected] = useState(false)
  const [note, setNote] = useState<Note | null>(null)
  if (!token) return <Navigate to="/welcome" replace />

  const canEdit = !!trip.data && trip.data.my_role !== "viewer"
  // shortcut: offline, adding and changing are disabled; 05 6.11 wants queued edits with a "Waiting to sync" chip. Upgrade: WF-089 (offline queue).
  const locked = !online
  const all = list.data?.items ?? []
  const live = all.filter((s) => s.status !== "rejected")
  const rejected = all.filter((s) => s.status === "rejected")
  const booked = all.some((s) => s.status === "booked")
  const failed = (list.isError && !list.data) || trip.isError
  const pending = !failed && (list.isPending || trip.isPending)
  const empty = !failed && !pending && all.length === 0
  const ready = !failed && !pending
  const pick = (sid: string) => setPicked((p) => (p.includes(sid) ? p.filter((x) => x !== sid) : p.length < MAX_COMPARE ? [...p, sid] : p))
  const travelers = trip.data?.travelers ?? []
  const closeAdd = () => {
    setAdding(false)
    if (params.has("add")) setParams({}, { replace: true })
  }
  const heart = async (s: Stay, voted: boolean) => {
    const r = await setHeart(id, s.id, voted)
    if (r.ok) {
      setNote(null)
      track("lodging_voted", { voted })
    } else setNote({ kind: "error", text: t("stays.voteFailed") })
  }
  const status = async (s: Stay, to: Status) => {
    const r = await setStatus(id, s, to)
    if (r.ok) {
      setNote(null)
      if (to === "booked") track("lodging_booked")
      return
    }
    const text = r.reason === "forbidden" ? t("stays.forbidden") : r.reason === "conflict" ? r.detail ?? t(to === "booked" ? "stays.booking409" : "stays.conflict") : t("stays.changeFailed")
    setNote({ kind: "error", text })
  }
  const openCompare = () => {
    track("lodging_compare_opened", { count: picked.length })
    setView("compare")
  }
  const card = (s: Stay) => (
    <StayCard
      key={s.id} stay={s} travelers={travelers} meId={me.data?.id} canEdit={canEdit} locked={locked} booked={booked}
      picked={picked.includes(s.id)} pickDisabled={!picked.includes(s.id) && picked.length >= MAX_COMPARE} onPick={() => pick(s.id)}
      onHeart={(v) => void heart(s, v)} onStatus={(to) => void status(s, to)}
    />
  )
  const nights = trip.data?.start_date && trip.data.end_date ? daysBetween(parseDate(trip.data.start_date), parseDate(trip.data.end_date)) : 0
  const dates = nights > 0 && trip.data?.start_date && trip.data.end_date ? t("stays.dates", { from: day(trip.data.start_date), to: day(trip.data.end_date), n: nights }) : ""

  return (
    <AppShell active="trips" strip={tripStrip(nav, id, "stays")}>
      <div className="overview">
        {!online && (
          <p role="status" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("stays.offline")}
          </p>
        )}
        <h1 className="h-sr-only">{t("stays.title")}</h1>
        <div className="h-row">
          {ready && !empty ? (
            <SegmentedControl narrow aria-label={t("stays.views")}>
              <SegItem selected={view === "list"} onClick={() => setView("list")}>{t("stays.list")}</SegItem>
              <SegItem selected={view === "compare"} onClick={() => (picked.length >= 2 ? openCompare() : setView("compare"))}>{t("stays.compare")}</SegItem>
            </SegmentedControl>
          ) : (
            <span />
          )}
          {canEdit && (
            <Btn variant="primary" mod={["lead"]} disabled={locked} onClick={() => setAdding(true)}>
              <Icon name="plus" size={20} />
              {t("stays.add")}
            </Btn>
          )}
        </div>
        {trip.data && !canEdit && <p className="h-soft">{t("stays.viewerNote")}</p>}
        {note && (
          <p role="alert" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {note.text}
          </p>
        )}
        {pending && (
          <>
            <p className="h-soft" aria-live="polite">{t("stays.loading")}</p>
            {[0, 1, 2].map((n) => <div key={n} className="stays__skel" aria-hidden="true" />)}
          </>
        )}
        {failed && (
          <div className="trips__stack">
            <p role="alert" className="h-input__error trips__note">
              <Icon name="circle-alert" size={16} />
              {trip.error instanceof NotFound ? t("overview.notFound") : t("stays.error")}
            </p>
            {!(trip.error instanceof NotFound) && <Btn variant="secondary" onClick={() => void Promise.all([list.refetch(), trip.refetch()])}>{t("trips.retry")}</Btn>}
          </div>
        )}
        {empty && (
          <div className="trips__empty">
            <strong>{t("stays.emptyTitle")}</strong>
            <span className="h-soft">{t("stays.emptyBody")}</span>
            {canEdit && <Btn variant="primary" disabled={locked} onClick={() => setAdding(true)}>{t("stays.add")}</Btn>}
          </div>
        )}
        {ready && !empty && view === "compare" &&
          (picked.length >= 2 ? (
            <Compare tripId={id} ids={picked} onBack={() => setView("list")} />
          ) : (
            <div className="trips__stack">
              <p className="h-soft">{t("stays.compareHint")}</p>
              <Btn variant="secondary" onClick={() => setView("list")}>{t("stays.compareBack")}</Btn>
            </div>
          ))}
        {ready && !empty && view === "list" && (
          <>
            <div className="h-row h-row--sort">
              <span className="h-stay__where">
                <span className="h-stay__where-name">{trip.data?.name}</span>
                {dates && <span className="h-stay__where-dates">{dates}</span>}
                <span className="h-soft">{t(`stays.sorted.${list.data?.sorted_by ?? sort}`)}</span>
              </span>
              <label className="stays__sort">
                {t("stays.sortLabel")}
                <select className="h-input__field" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                  {SORTS.map((s) => <option key={s} value={s}>{t(`stays.sort.${s}`)}</option>)}
                </select>
              </label>
            </div>
            {canEdit && booked && <p className="h-soft">{t("stays.oneBooked")}</p>}
            {picked.length >= MAX_COMPARE && <p className="h-soft">{t("stays.compareMax")}</p>}
            <div className="h-stack">{live.map(card)}</div>
            {rejected.length > 0 && (
              <section aria-label={t("stays.rejectedAria")} className="h-stack">
                <Btn variant="text" aria-expanded={showRejected} onClick={() => setShowRejected(!showRejected)}>{t("stays.rejected", { n: rejected.length })}</Btn>
                {showRejected && rejected.map(card)}
              </section>
            )}
          </>
        )}
        {ready && canEdit && <Bookmarklet tripId={id} />}
        {ready && view === "list" && picked.length >= 2 && picked.length <= MAX_COMPARE && (
          <div className="stays__bar">
            <Btn variant="primary" onClick={openCompare}>{t("stays.compareCount", { n: picked.length })}</Btn>
          </div>
        )}
      </div>
      {adding && <AddStay tripId={id} currency={trip.data?.home_currency ?? "USD"} prefill={prefill} onClose={closeAdd} onAdded={closeAdd} />}
    </AppShell>
  )
}
