import { useEffect, useId, useState, type KeyboardEvent } from "react"
import { TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { api } from "../auth/api"
import "../onboarding/onboarding.css"
import type { DestinationIn } from "../onboarding/trips"

/**
 * Place autocomplete (04 section 5.5, GET /geo/destinations, Geoapify behind our API, never a scraped page). A pick
 * yields a destination with lat, lon and the IANA `timezone` when the provider knows it. Shared with the itinerary (WF-032).
 * ARIA combobox: arrows move the active option (wrapping), Enter picks it, Escape closes the list. A failed lookup is a message, never a block.
 */
export function PlaceSearch({ label, onPick }: { label: string; onPick: (d: DestinationIn) => void }) {
  const [q, setQ] = useState("")
  const [options, setOptions] = useState<DestinationIn[]>([])
  const [active, setActive] = useState(-1)
  const [failed, setFailed] = useState(false)
  const listId = useId()

  useEffect(() => {
    const term = q.trim()
    if (term.length < 2) return setOptions([])
    const ac = new AbortController()
    // Wait for a pause in typing (250 ms) so each keystroke is not a provider lookup.
    const timer = setTimeout(() => {
      api
        .get<DestinationIn[]>("/v1/geo/destinations", { query: { q: term, limit: 8 }, signal: ac.signal })
        .then((r) => {
          if (ac.signal.aborted) return
          const ok = r.error === undefined && Array.isArray(r.data)
          setFailed(!ok)
          setOptions(ok ? r.data! : [])
          setActive(-1)
        })
        .catch(() => !ac.signal.aborted && setFailed(true))
    }, 250)
    return () => {
      clearTimeout(timer)
      ac.abort()
    }
  }, [q])

  const pick = (o: DestinationIn) => {
    onPick(o)
    setQ("")
    setOptions([])
  }
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    const n = options.length
    if (!n) return
    if (e.key === "Escape") {
      e.preventDefault()
      setOptions([])
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault()
      const d = e.key === "ArrowDown" ? 1 : -1
      setActive((a) => (a < 0 ? (d > 0 ? 0 : n - 1) : (a + d + n) % n))
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault()
      pick(options[active])
    }
  }

  return (
    <div className="place">
      <TextField
        label={label}
        role="combobox"
        aria-expanded={options.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 && options[active] ? `${listId}-${active}` : undefined}
        autoComplete="off"
        value={q}
        onKeyDown={onKey}
        onChange={(e) => {
          setQ(e.target.value)
          setFailed(false)
        }}
      />
      {failed && <p className="h-soft">{t("editTrip.searchError")}</p>}
      {options.length > 0 && (
        <ul id={listId} role="listbox" aria-label={t("createTrip.results")} className="create__options">
          {options.map((o, i) => (
            // Keys are handled on the input (aria-activedescendant), so the option only needs the click.
            // eslint-disable-next-line jsx-a11y/click-events-have-key-events
            <li
              key={`${o.name}-${o.lat}-${o.lon}`}
              id={`${listId}-${i}`}
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
      {options.length > 0 && <p className="h-soft">{t("editTrip.attribution")}</p>}
    </div>
  )
}
