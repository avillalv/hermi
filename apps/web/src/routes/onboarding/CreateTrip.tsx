import { useEffect, useState, type KeyboardEvent } from "react"
import { Navigate, useNavigate } from "react-router"
import { Btn, Icon, Sprite, TextField } from "../../components/kit"
import { parseDate } from "../../lib/dates"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { api } from "../auth/api"
import { useAuth } from "../auth/authStore"
import { createTrip, type DestinationIn } from "./trips"
import "../auth/auth.css"
import "./onboarding.css"

type Step = 1 | 2 | 3

/** 05 6.6 in three steps: place, dates, who is going and the name. One destination for now (shortcut: multi-destination and saved travelers come with WF-019). */
export function CreateTrip() {
  const { token } = useAuth()
  const nav = useNavigate()
  const online = useOnline()
  const [step, setStep] = useState<Step>(1)
  const [place, setPlace] = useState("")
  const [picked, setPicked] = useState<DestinationIn | null>(null)
  const [active, setActive] = useState(-1)
  const [options, setOptions] = useState<DestinationIn[]>([])
  const [lookupFailed, setLookupFailed] = useState(false)
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [noDates, setNoDates] = useState(false)
  const [name, setName] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Typeahead (04 section 5.5). A failed lookup never blocks: the typed name is used and resolved later.
  useEffect(() => {
    const q = place.trim()
    if (q.length < 2 || picked?.name === q) return setOptions([])
    const ac = new AbortController()
    api
      .get<DestinationIn[]>("/v1/geo/destinations", { query: { q, limit: 8 }, signal: ac.signal })
      .then((r) => {
        if (ac.signal.aborted) return
        const ok = r.error === undefined && Array.isArray(r.data)
        setLookupFailed(!ok)
        setOptions(ok ? r.data! : [])
        setActive(-1)
      })
      .catch(() => !ac.signal.aborted && setLookupFailed(true))
    return () => ac.abort()
  }, [place, picked])

  if (!token) return <Navigate to="/sign-in" replace />

  const pick = (o: DestinationIn) => {
    setPicked(o)
    setPlace(o.name)
    setOptions([])
  }
  // ARIA combobox keys: arrows move the active option (wrapping), Enter picks it, Escape closes the list.
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    const n = options.length
    if (e.key === "Escape" && n) {
      e.preventDefault()
      return setOptions([])
    }
    if (!n) return
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault()
      const d = e.key === "ArrowDown" ? 1 : -1
      setActive((a) => (a < 0 ? (d > 0 ? 0 : n - 1) : (a + d + n) % n))
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault()
      pick(options[active])
    }
  }

  const next = () => {
    setError(null)
    if (step === 1) {
      if (!place.trim()) return setError(t("createTrip.searchEmpty"))
      return setStep(2)
    }
    if (step === 2) {
      if (!noDates && !!start !== !!end) return setError(t("createTrip.datesBoth"))
      if (!noDates && start && end < start) return setError(t("createTrip.datesOrder"))
      const month = !noDates && start ? `, ${parseDate(start).toLocaleString("en", { month: "long", timeZone: "UTC" })}` : ""
      setName((n) => n || `${picked?.name ?? place.trim()}${month}`)
      setStep(3)
    }
  }

  const create = async () => {
    if (!name.trim()) return setError(t("createTrip.nameRequired"))
    setBusy(true)
    setError(null)
    const hasDates = !noDates && start && end
    const r = await createTrip({
      name: name.trim(),
      ...(hasDates ? { start_date: start, end_date: end } : {}),
      ...(picked ? { destinations: [picked] } : {}),
    })
    if (r.ok) {
      track("trip_created", { source: "blank", destination_count: picked ? 1 : 0, has_dates: !!hasDates })
      return nav("/", { replace: true }) // shortcut: opens Trips until Trip overview (WF-020) exists
    }
    setBusy(false)
    // shortcut: an inline sentence for the Free trip limit. WF-064 replaces it with the third_trip paywall sheet (05 6.27), with "Archive a trip" first.
    setError(t(r.reason === "limit" ? "createTrip.limit" : "createTrip.failed"))
  }

  // Steps 1 and 2 show their error on the field; only step 3 has a standalone alert.
  const alert = error && step === 3 && (
    <p role="alert" className="h-input__error">
      <Icon name="circle-alert" size={16} />
      {error}
    </p>
  )

  return (
    <main className="auth">
      <div className="auth__panel">
        <Sprite />
        <header className="create__bar">
          <Btn variant="text" mod={["icon"]} aria-label={t("createTrip.close")} onClick={() => nav("/")}>
            <Icon name="x" />
          </Btn>
          <h1 className="h-title">{t("createTrip.title")}</h1>
          <span className="h-soft" aria-live="polite">
            {t("createTrip.step", { n: step })}
          </span>
        </header>

        {step === 1 && (
          <div className="auth__stack">
            <h2 className="h-title">{t("createTrip.where")}</h2>
            <TextField
              label={t("createTrip.search")}
              role="combobox"
              aria-expanded={options.length > 0}
              aria-controls="places"
              aria-autocomplete="list"
              aria-activedescendant={active >= 0 && options[active] ? `place-${active}` : undefined}
              onKeyDown={onKey}
              autoComplete="off"
              value={place}
              error={error}
              onChange={(e) => {
                setPlace(e.target.value)
                setPicked(null)
                setLookupFailed(false)
              }}
            />
            {lookupFailed && <p className="h-soft">{t("createTrip.searchError")}</p>}
            {options.length > 0 && (
              <ul id="places" role="listbox" aria-label={t("createTrip.results")} className="create__options">
                {options.map((o, i) => (
                  // Keys are handled on the input (aria-activedescendant), so the option only needs the click.
                  // eslint-disable-next-line jsx-a11y/click-events-have-key-events
                  <li
                    key={`${o.name}-${o.lat}-${o.lon}`}
                    id={`place-${i}`}
                    role="option"
                    tabIndex={-1}
                    aria-selected={i === active}
                    className={i === active ? "create__option create__option--active" : "create__option"}
                    onClick={() => pick(o)}
                  >
                    {[o.name, o.country].filter(Boolean).join(", ")}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="auth__stack">
            <h2 className="h-title">{t("createTrip.when")}</h2>
            <TextField label={t("createTrip.start")} type="date" value={start} disabled={noDates} onChange={(e) => setStart(e.target.value)} />
            <TextField
              label={t("createTrip.end")}
              type="date"
              value={end}
              disabled={noDates}
              error={error}
              helper={t("createTrip.datesHelper")}
              onChange={(e) => setEnd(e.target.value)}
            />
            <label className="onboarding__age">
              <input type="checkbox" checked={noDates} onChange={(e) => setNoDates(e.target.checked)} />
              {t("createTrip.noDates")}
            </label>
          </div>
        )}

        {step === 3 && (
          <div className="auth__stack">
            <h2 className="h-title">{t("createTrip.who")}</h2>
            <p className="h-chip">{t("createTrip.justMe")}</p>
            <p className="h-soft">{t("createTrip.whoHelper")}</p>
            <TextField label={t("createTrip.name")} value={name} onChange={(e) => setName(e.target.value)} />
            {!online && (
              <p role="status" className="h-input__error">
                <Icon name="circle-alert" size={16} />
                {t("createTrip.offline")}
              </p>
            )}
          </div>
        )}
        {alert}

        <div className="auth__stack">
          {step < 3 ? (
            <Btn variant="primary" onClick={next}>
              {t("createTrip.next")}
            </Btn>
          ) : (
            <Btn variant="primary" busy={busy} disabled={!online} onClick={() => void create()}>
              {t("createTrip.create")}
            </Btn>
          )}
          {step > 1 && (
            <Btn variant="text" disabled={busy} onClick={() => (setError(null), setStep((step - 1) as Step))}>
              {t("createTrip.back")}
            </Btn>
          )}
        </div>
      </div>
    </main>
  )
}
