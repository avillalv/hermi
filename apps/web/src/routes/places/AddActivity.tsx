import { useRef, useState } from "react"
import { Btn, Icon, LinkBtn, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { createItem } from "../itinerary/api"
import { dayText, IDEAS } from "../itinerary/meta"
import { Modal } from "../itinerary/Modal"
import { fromPlace, fromSaved, removeSaved, savePlace, searchPlaces, usePlaceDetails, useSavedPlaces, type Candidate, type SearchResult } from "./api"
import { appleMapsUrl, googleMapsUrl } from "./handoff"
import "./places.css"

/** The sheet's category chips (05 6.13) and the Geoapify search kind each one asks for. "Getting around" has no place kind, so it is left out. */
const KINDS = { sights: "landmarks", museum: "museums", food: "restaurants", nature: "parks", nightlife: "nightlife", shopping: "shopping" } as const
type Kind = keyof typeof KINDS

type Found = { kind: "idle" } | { kind: "loading" } | { kind: "done"; data: SearchResult } | { kind: "error"; message: string; byHand: boolean }
type Destination = { id: string; lat?: number; lon?: number }
type Props = {
  tripId: string
  days: { day: string; n: number }[]
  /** The day on screen, or "ideas": the day picker starts there. */
  start: string
  destination: Destination | null
  canWrite: boolean
  online: boolean
  onClose: () => void
  /** Hand over to the manual form (the "Custom item" row and "Add by hand"). */
  onCustom: () => void
  onAdded: (day: string, title: string) => void
}

const bucket = (n: number) => (n === 0 ? "0" : n <= 5 ? "1-5" : n <= 10 ? "6-10" : "11+")
const safeUrl = (u: string | null) => (u && /^https?:\/\//i.test(u) ? u : null)

function Detail({ c, p, onBack }: { c: Candidate; p: Props; onBack: () => void }) {
  const details = usePlaceDetails(c.provider === "geoapify" ? c.id : null)
  const saved = useSavedPlaces(p.tripId)
  const d = details.data
  const hours = d?.opening_hours ?? c.opening_hours
  const site = safeUrl(d?.website ?? c.website)
  const wiki = d?.wiki
  const inIdeas = !!c.savedId || !!saved.data?.some((s) => s.place.id === c.id)
  const [day, setDay] = useState(p.start)
  const [time, setTime] = useState("")
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<{ kind: "ok" | "error"; text: string } | null>(null)
  const n = p.days.find((x) => x.day === day)?.n
  const spot = { name: c.name, lat: c.lat, lon: c.lon }

  const add = async () => {
    setBusy(true)
    setNote(null)
    const scheduled = day !== IDEAS
    const r = await createItem(p.tripId, {
      title: c.name,
      category: c.category,
      day: scheduled ? day : null,
      ...(scheduled && time ? { start_time: `${time}:00` } : {}),
      location_name: c.name,
      ...(c.address ? { address: c.address } : {}),
      ...(c.lat !== null && c.lon !== null ? { lat: c.lat, lon: c.lon } : {}),
      ...(site ? { url: site } : {}),
      ...(c.provider === "geoapify" ? { place: { provider: "geoapify" as const, id: c.id.replace(/^geoapify:/, "") } } : {}),
    })
    setBusy(false)
    if (!r.ok) return setNote({ kind: "error", text: t(r.reason === "forbidden" ? "places.forbidden" : "places.addFailed") })
    track("itinerary_item_added", { category: c.category, source: "place_search" })
    p.onAdded(day, c.name)
  }
  const save = async () => {
    setBusy(true)
    const ok = await savePlace(p.tripId, c.id)
    setBusy(false)
    setNote(ok ? { kind: "ok", text: t("places.saved") } : { kind: "error", text: t("places.saveFailed") })
  }

  return (
    <div className="places__detail">
      <Btn variant="text" mod={["sm"]} onClick={onBack}>{t("places.back")}</Btn>
      <h3 className="h-title">{c.name}</h3>
      {c.address && <p className="h-soft places__facts">{c.address}</p>}
      {hours && (
        <p className="places__facts">
          <span className="h-label">{t("places.hours")}</span>
          <span>{hours}</span>
        </p>
      )}
      {site && <a href={site} target="_blank" rel="noopener noreferrer">{t("places.website")}</a>}
      {wiki && (
        <div>
          <p className="places__wiki">{wiki.extract}</p>
          <p className="h-soft">
            <span>{wiki.attribution}</span>
            {safeUrl(wiki.url) && <>{" "}<a href={wiki.url ?? undefined} target="_blank" rel="noopener noreferrer">{t("places.wikiLink")}</a></>}
          </p>
        </div>
      )}
      <div className="places__handoff">
        <LinkBtn variant="secondary" mod={["sm"]} href={appleMapsUrl(spot)} target="_blank" rel="noopener noreferrer" onClick={() => track("maps_handoff", { app: "apple" })}>{t("places.openApple")}</LinkBtn>
        <LinkBtn variant="secondary" mod={["sm"]} href={googleMapsUrl(spot)} target="_blank" rel="noopener noreferrer" onClick={() => track("maps_handoff", { app: "google" })}>{t("places.openGoogle")}</LinkBtn>
      </div>
      <div className="h-input">
        <label className="h-input__label" htmlFor="places-day">{t("plan.fieldDay")}</label>
        <select id="places-day" className="h-input__field" value={day} onChange={(e) => setDay(e.target.value)}>
          {p.days.map((x) => <option key={x.day} value={x.day}>{t("plan.dayChip", { n: x.n, date: dayText(x.day) })}</option>)}
          <option value={IDEAS}>{t("plan.ideas")}</option>
        </select>
      </div>
      <TextField label={t("plan.fieldTime")} type="time" value={day === IDEAS ? "" : time} disabled={day === IDEAS} onChange={(e) => setTime(e.target.value)} />
      {note && (
        <p role={note.kind === "error" ? "alert" : "status"} className={note.kind === "error" ? "h-input__error" : undefined}>
          {note.kind === "error" && <Icon name="circle-alert" size={16} />}
          {note.text}
        </p>
      )}
      <Btn variant="primary" busy={busy} disabled={!p.canWrite || !p.online} onClick={() => void add()}>
        {n ? t("places.addToDay", { name: c.name, n }) : t("places.addToIdeas", { name: c.name })}
      </Btn>
      {!inIdeas && c.provider === "geoapify" && (
        <Btn variant="secondary" disabled={!p.canWrite || !p.online || busy} onClick={() => void save()}>{t("places.saveToIdeas", { name: c.name })}</Btn>
      )}
    </div>
  )
}

/** 05 6.13 Add item: search places, pick a result to see its detail and add it to a day, or save it to ideas. A custom item hands over to the manual form. */
export function AddActivity(p: Props) {
  const [q, setQ] = useState("")
  const [kind, setKind] = useState<Kind | null>(null)
  const [found, setFound] = useState<Found>({ kind: "idle" })
  const [picked, setPicked] = useState<Candidate | null>(null)
  const latest = useRef(0)
  const ideas = useSavedPlaces(p.tripId)

  const run = async (text: string, k: Kind | null) => {
    if (!text.trim() && !k) return
    if (!p.destination) return setFound({ kind: "error", message: t("places.noDestination"), byHand: true })
    const mine = ++latest.current
    setFound({ kind: "loading" })
    const r = await searchPlaces({ tripId: p.tripId, destinationId: p.destination.id, q: text.trim() || undefined, category: k ? KINDS[k] : undefined })
    if (mine !== latest.current) return // a newer search is already running
    if (r.ok) {
      track("place_searched", { result_count_bucket: bucket(r.data.places.length) })
      return setFound({ kind: "done", data: r.data })
    }
    const message = r.reason === "quota" ? t("places.quota") : r.reason === "rate_limited" ? t("places.rateLimited") : t("places.error")
    setFound({ kind: "error", message, byHand: r.reason !== "rate_limited" })
  }
  const chip = (k: Kind) => {
    const next = kind === k ? null : k
    setKind(next)
    void run(q, next)
  }

  return (
    <Modal title={t("plan.addTitle")} onClose={p.onClose}>
      {picked ? (
        <Detail c={picked} p={p} onBack={() => setPicked(null)} />
      ) : (
        <>
          <form className="places__search" role="search" noValidate onSubmit={(e) => (e.preventDefault(), void run(q, kind))}>
            <TextField label={t("places.searchLabel")} type="search" value={q} maxLength={120} autoComplete="off" placeholder={t("places.searchPlaceholder")} onChange={(e) => setQ(e.target.value)} />
            <Btn variant="primary" type="submit" disabled={!p.online || found.kind === "loading"}>{t("places.search")}</Btn>
          </form>
          <div className="places__chips" role="group" aria-label={t("places.categories")}>
            {(Object.keys(KINDS) as Kind[]).map((k) => (
              <Btn key={k} variant="secondary" mod={["sm"]} aria-pressed={kind === k} disabled={!p.online} onClick={() => chip(k)}>{t(`places.cat.${k}`)}</Btn>
            ))}
          </div>
          {!p.online && <p role="status" className="h-input__error"><Icon name="circle-alert" size={16} />{t("places.offline")}</p>}
          {found.kind === "loading" && (
            <div className="places__results" aria-live="polite" aria-label={t("places.loading")}>
              <div className="places__skel" aria-hidden="true" />
              <div className="places__skel" aria-hidden="true" />
              <div className="places__skel" aria-hidden="true" />
            </div>
          )}
          {found.kind === "error" && (
            <div className="places__note">
              <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{found.message}</p>
              {found.byHand && <Btn variant="secondary" onClick={p.onCustom}>{t("places.addByHand")}</Btn>}
            </div>
          )}
          {found.kind === "done" && (found.data.places.length === 0 ? (
            <p className="h-soft">{t("places.empty")}</p>
          ) : (
            <>
              <p className="h-soft">{t(found.data.sorted_by === "distance" ? "places.sortDistance" : "places.sortRelevance")}</p>
              <div className="places__results" role="listbox" aria-label={t("places.results")}>
                {found.data.places.map((pl) => (
                  <button key={pl.id} type="button" role="option" aria-selected="false" className="places__result" onClick={() => setPicked(fromPlace(pl))}>
                    <span className="h-listcard__text">{pl.name}</span>
                    <span className="h-soft">{[t(`plan.cat.${pl.category}`), pl.address].filter(Boolean).join(", ")}</span>
                  </button>
                ))}
              </div>
            </>
          ))}
          <h3 className="h-label">{t("places.ideasTitle")}</h3>
          {ideas.isError && <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{t("places.ideasError")}</p>}
          {ideas.data?.length === 0 && <p className="h-soft">{t("places.ideasEmpty")}</p>}
          {ideas.data && ideas.data.length > 0 && (
            <div className="places__results">
              {ideas.data.map((s) => (
                <div key={s.id} className="places__idea">
                  <button type="button" className="places__result" onClick={() => setPicked(fromSaved(s))}>
                    <span className="h-listcard__text">{s.place.name}</span>
                    {s.place.address && <span className="h-soft">{s.place.address}</span>}
                  </button>
                  <Btn variant="text" mod={["sm"]} aria-label={t("places.removeIdea", { name: s.place.name })} disabled={!p.canWrite || !p.online} onClick={() => void removeSaved(p.tripId, s.id)}>
                    <Icon name="x" size={18} />
                  </Btn>
                </div>
              ))}
            </div>
          )}
          <button type="button" className="places__result" onClick={p.onCustom}>
            <Icon name="plus" size={18} />
            <span className="h-listcard__text">{t("places.custom")}</span>
          </button>
          <p className="h-soft">{t("places.attribution")}</p>
        </>
      )}
      <Btn variant="text" onClick={p.onClose}>{t("plan.close")}</Btn>
    </Modal>
  )
}
