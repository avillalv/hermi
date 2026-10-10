import { useState, type FormEvent } from "react"
import { Link } from "react-router"
import { Btn, Icon, TextField } from "../../components/kit"
import { formatDateRange } from "../../lib/dates"
import { t } from "../../lib/i18n"
import { AppShell } from "../../shell/AppShell"
import { requireAccount, type Need } from "./prompts"
import { addGuestItem, createGuestTrip, removeGuestItem, updateGuestTrip, useGuest, type GuestItem } from "./store"
import "./guest.css"

const ACTIONS: { need: Need; label: string }[] = [
  { need: "invite", label: "guest.actionInvite" },
  { need: "ai", label: "guest.actionAi" },
  { need: "export", label: "guest.actionExport" },
  { need: "alert", label: "guest.actionAlert" },
  { need: "import", label: "guest.actionImport" },
]

const byWhen = (a: GuestItem, b: GuestItem) => `${a.day ?? "9999"}${a.start_time ?? ""}`.localeCompare(`${b.day ?? "9999"}${b.start_time ?? ""}`)

function Create() {
  const [place, setPlace] = useState("")
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [error, setError] = useState<string | null>(null)
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!place.trim()) return setError(t("createTrip.searchEmpty"))
    if (!!start !== !!end) return setError(t("createTrip.datesBoth"))
    if (start && end < start) return setError(t("createTrip.datesOrder"))
    createGuestTrip({ name: place.trim(), destination: place, start_date: start, end_date: end })
  }
  return (
    <form className="guest-home__form" onSubmit={submit} noValidate>
      <h1 className="h-pagehead__title">{t("guest.createTitle")}</h1>
      <p className="h-soft">{t("guest.createBody")}</p>
      <TextField label={t("createTrip.where")} value={place} error={error} onChange={(e) => setPlace(e.target.value)} />
      <TextField label={t("createTrip.start")} type="date" value={start} onChange={(e) => setStart(e.target.value)} />
      <TextField label={t("createTrip.end")} type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
      <Btn variant="primary" type="submit">
        {t("guest.create")}
      </Btn>
    </form>
  )
}

/**
 * The guest's trip (05 6.2): created, edited and read on this device, with no request to the server. Anything that needs
 * the server calls `requireAccount`, which opens the Save sheet.
 */
export function GuestHome() {
  const guest = useGuest()
  const [title, setTitle] = useState("")
  const [day, setDay] = useState("")
  const [time, setTime] = useState("")
  const [limit, setLimit] = useState(false)
  if (!guest)
    return (
      <AppShell active="trips">
        <Create />
        <p>
          <Link to="/sign-in" className="h-link">
            {t("auth.signIn")}
          </Link>
        </p>
      </AppShell>
    )
  const { trip } = guest
  const where = trip.destinations.join(", ")
  const subtitle = [where === trip.name ? "" : where, trip.start_date && trip.end_date ? formatDateRange(trip.start_date, trip.end_date) : ""].filter(Boolean).join(", ")
  const add = (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    addGuestItem({ title: title.trim(), day: day || null, start_time: day && time ? time : null, category: "other", location_name: null })
    setTitle("")
    setTime("")
  }
  return (
    <AppShell active="trips">
      <div className="guest-home">
        <h1 className="h-pagehead__title">{trip.name}</h1>
        {subtitle && <p className="h-soft">{subtitle}</p>}
        <TextField label={t("guest.tripName")} value={trip.name} onChange={(e) => updateGuestTrip({ name: e.target.value })} />
        <TextField label={t("createTrip.start")} type="date" value={trip.start_date ?? ""} onChange={(e) => updateGuestTrip({ start_date: e.target.value || null })} />
        <TextField label={t("createTrip.end")} type="date" value={trip.end_date ?? ""} onChange={(e) => updateGuestTrip({ end_date: e.target.value || null })} />

        <h2 className="h-heading h-heading--section">{t("guest.planTitle")}</h2>
        {trip.items.length === 0 && <p className="h-soft">{t("guest.planEmpty")}</p>}
        <ul className="guest-home__items">
          {[...trip.items].sort(byWhen).map((i) => (
            <li key={i.id} className="guest-home__item">
              <span>
                <strong>{i.title}</strong>
                <span className="h-soft"> {[i.day && formatDateRange(i.day, i.day), i.start_time].filter(Boolean).join(", ")}</span>
              </span>
              <Btn variant="text" aria-label={t("guest.removeItem", { title: i.title })} onClick={() => removeGuestItem(i.id)}>
                <Icon name="x" />
              </Btn>
            </li>
          ))}
        </ul>
        <form className="guest-home__form" onSubmit={add} noValidate>
          <TextField label={t("guest.itemTitle")} value={title} onChange={(e) => setTitle(e.target.value)} />
          <TextField label={t("guest.itemDay")} type="date" value={day} onChange={(e) => setDay(e.target.value)} />
          <TextField label={t("guest.itemTime")} type="time" value={time} disabled={!day} onChange={(e) => setTime(e.target.value)} />
          <Btn variant="secondary" type="submit">
            {t("guest.addItem")}
          </Btn>
        </form>

        <div className="guest-home__actions">
          {ACTIONS.map((a) => (
            <Btn key={a.need} variant="secondary" onClick={() => void requireAccount(a.need)}>
              {t(a.label)}
            </Btn>
          ))}
          <Btn variant="text" onClick={() => setLimit(true)}>
            {t("trips.newTrip")}
          </Btn>
        </div>
        {limit && (
          <p role="status" className="h-input__error">
            {t("discover.guestLimit")}
          </p>
        )}
      </div>
    </AppShell>
  )
}
