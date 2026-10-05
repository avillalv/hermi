import { useEffect, useState } from "react"
import { Link, Navigate, useNavigate, useParams } from "react-router"
import { Btn, Icon, TextField } from "../../components/kit"
import { SyncIndicator } from "../../components/sync-indicator/SyncIndicator"
import { currencyOptions } from "../../lib/currencies"
import { t } from "../../lib/i18n"
import { clearConflict, reportConflict } from "../../lib/sync"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { api } from "../auth/api"
import { useAuth } from "../auth/authStore"
import type { DestinationIn } from "../onboarding/trips"
import { NotFound, patchTrip, useTrip, type Trip, type TripPatch } from "./api"
import { PlaceSearch } from "./PlaceSearch"
import "./trips.css"

const label = (d: { name: string; country?: string | null }) => [d.name, d.country].filter(Boolean).join(", ")

type Dest = DestinationIn & { id?: string }

function Form({ trip, onReload }: { trip: Trip; onReload: () => void }) {
  const nav = useNavigate()
  const online = useOnline()
  const [name, setName] = useState(trip.name)
  const [start, setStart] = useState(trip.start_date ?? "")
  const [end, setEnd] = useState(trip.end_date ?? "")
  const [currency, setCurrency] = useState(trip.home_currency)
  const [dests, setDests] = useState<Dest[]>(trip.destinations.map((d) => ({ ...d, lat: d.lat ?? 0, lon: d.lon ?? 0 })))
  const [errors, setErrors] = useState<{ name?: string; dates?: string; form?: string }>({})
  const [busy, setBusy] = useState(false)
  const [stale, setStale] = useState(false)
  const currencies = currencyOptions()

  const save = async () => {
    const e: typeof errors = {}
    if (!name.trim()) e.name = t("createTrip.nameRequired")
    if (!!start !== !!end) e.dates = t("editTrip.datesBoth")
    else if (start && end < start) e.dates = t("createTrip.datesOrder")
    setErrors(e)
    if (e.name || e.dates) return
    setBusy(true)
    // Destinations go only when the list changed (added, removed or reordered), and a kept one sends just its identity,
    // so the API keeps what the form never shows (kind, bounding box, provider id).
    const same = dests.length === trip.destinations.length && dests.every((d, i) => d.id === trip.destinations[i].id)
    const body: TripPatch = {
      name: name.trim(),
      start_date: start || null,
      end_date: end || null,
      home_currency: currency,
      ...(same ? {} : { destinations: dests.map((d) => (d.id ? { id: d.id, name: d.name, lat: d.lat, lon: d.lon } : d)) }),
    }
    const r = await patchTrip(trip.id, trip.version, body)
    if (r.ok) return nav(`/trips/${trip.id}`)
    setBusy(false)
    setStale(r.reason === "conflict")
    if (r.reason === "conflict") {
      // 05 4.21: the sync indicator's sheet. Keep mine saves the same body on top of their version; Use theirs reloads theirs.
      reportConflict(trip.id, {
        keepMine: async () => {
          const fresh = await api.get<Trip>(`/v1/trips/${encodeURIComponent(trip.id)}`)
          const saved = fresh.data ? await patchTrip(trip.id, fresh.data.version, body) : null
          if (saved?.ok) nav(`/trips/${trip.id}`)
          else setErrors({ form: t("sync.conflict.failed") })
        },
        useTheirs: onReload,
      })
    }
    setErrors({ form: t(r.reason === "conflict" ? "editTrip.conflict" : r.reason === "forbidden" ? "editTrip.viewerOnly" : "editTrip.failed") })
  }

  return (
    <form
      className="edit"
      noValidate
      onSubmit={(ev) => {
        ev.preventDefault()
        void save()
      }}
    >
      <TextField label={t("createTrip.name")} value={name} error={errors.name} onChange={(e) => setName(e.target.value)} />
      <section aria-labelledby="edit-dest" className="edit__group">
        <h2 className="h-label" id="edit-dest">
          {t("overview.destinations")}
        </h2>
        {dests.length === 0 && <p className="h-soft">{t("overview.noDestination")}</p>}
        <ul className="edit__dests">
          {dests.map((d, i) => (
            <li key={d.id ?? `${d.name}-${d.lat}-${d.lon}-${i}`} className="edit__dest">
              <span className="edit__dest-text">
                <span className="h-listcard__text">{label(d)}</span>
                {d.timezone && <span className="h-soft h-mono">{d.timezone}</span>}
              </span>
              <Btn variant="text" mod={["icon"]} aria-label={t("editTrip.remove", { name: d.name })} onClick={() => setDests(dests.filter((_, j) => j !== i))}>
                <Icon name="x" />
              </Btn>
            </li>
          ))}
        </ul>
        <PlaceSearch label={t("editTrip.addDestination")} onPick={(d) => setDests((all) => (all.length >= 12 ? all : [...all, d]))} />
      </section>
      <TextField label={t("createTrip.start")} type="date" value={start} onChange={(e) => setStart(e.target.value)} />
      <TextField label={t("createTrip.end")} type="date" value={end} error={errors.dates} helper={t("createTrip.datesHelper")} onChange={(e) => setEnd(e.target.value)} />
      <div className="h-input">
        <label className="h-input__label" htmlFor="edit-currency">
          {t("editTrip.currency")}
        </label>
        <select id="edit-currency" className="h-input__field" value={currency} onChange={(e) => setCurrency(e.target.value)}>
          {(currencies.some((c) => c.code === currency) ? currencies : [{ code: currency, name: currency }, ...currencies]).map((c) => (
            <option key={c.code} value={c.code}>
              {c.code}, {c.name}
            </option>
          ))}
        </select>
      </div>
      {!online && (
        <p role="status" className="h-input__error trips__note">
          <Icon name="circle-alert" size={16} />
          {t("editTrip.offline")}
        </p>
      )}
      {errors.form && (
        <p role="alert" className="h-input__error trips__note">
          <Icon name="circle-alert" size={16} />
          {errors.form}
          {stale && (
            <Btn variant="text" mod={["sm"]} onClick={onReload}>
              {t("editTrip.reload")}
            </Btn>
          )}
        </p>
      )}
      <Btn variant="primary" busy={busy} disabled={!online} onClick={() => void save()}>
        {t("editTrip.save")}
      </Btn>
    </form>
  )
}

/** 05 6.7 "Trip settings": name, destinations, dates and currency. Owner and editors; a viewer sees why not. */
export function TripEdit() {
  const { token } = useAuth()
  const { id } = useParams()
  const q = useTrip(id, !!token)
  useEffect(() => () => (id ? clearConflict(id) : undefined), [id]) // a sheet must not outlive this screen
  if (!token) return <Navigate to="/welcome" replace />
  const trip = q.data
  return (
    <AppShell active="trips">
      <div className="overview">
        <Link to={`/trips/${id}`} className="h-btn h-btn--text h-btn--sm overview__back">
          <Icon name="chevron-left" size={20} />
          {t("editTrip.back")}
        </Link>
        <h1 className="h-title">{t("editTrip.title")}</h1>
        {id && <SyncIndicator tripId={id} variant="line" />}
        {q.isPending && (
          <>
            <p className="h-soft" aria-live="polite">
              {t("overview.loading")}
            </p>
            {[0, 1, 2].map((i) => (
              <div key={i} className="trips__skel" aria-hidden="true" />
            ))}
          </>
        )}
        {q.isError && (
          <div className="trips__stack">
            <p role="alert" className="h-input__error trips__note">
              <Icon name="circle-alert" size={16} />
              {q.error instanceof NotFound ? t("overview.notFound") : t("overview.error")}
            </p>
            {!(q.error instanceof NotFound) && (
              <button type="button" className="h-btn h-btn--secondary" onClick={() => void q.refetch()}>
                {t("trips.retry")}
              </button>
            )}
          </div>
        )}
        {trip && (trip.my_role === "viewer" ? <p className="h-soft">{t("editTrip.viewerOnly")}</p> : <Form key={`${trip.id}-${trip.version}`} trip={trip} onReload={() => void q.refetch()} />)}
      </div>
    </AppShell>
  )
}
