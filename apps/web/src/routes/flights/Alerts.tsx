import { useEffect, useRef, useState } from "react"
import { Link } from "react-router"
import { Btn, Icon, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { formatMoney, minorDigits, toMinor } from "../../lib/money"
import { track } from "../../lib/track"
import { createAlert, deleteAlert, updateAlert, useAlerts, useEntitlements, type Alert, type Money, type Result, type Route } from "./api"

const plain = (m: Money) => (m.amount_minor / 10 ** minorDigits(m.currency)).toFixed(minorDigits(m.currency))

/**
 * 05 6.9 alert sheet. shortcut: an inline panel like PaySheet, not a modal sheet, and the target is "below $" only
 * (the API has no percent drop yet). The push permission reason screen waits for the native adapter. Upgrade links to Account until the paywall sheet (WF-064).
 */
function AlertSheet({ tripId, routeId, currency, mine, onDone, onClose }: { tripId: string; routeId: string; currency: string; mine: Alert | undefined; onDone: (amount: Money) => void; onClose: () => void }) {
  const cur = mine?.target_price.currency ?? currency
  const [v, setV] = useState(mine ? plain(mine.target_price) : "")
  const [push, setPush] = useState(mine?.notify.push ?? true)
  const [email, setEmail] = useState(mine?.notify.email ?? false)
  const [err, setErr] = useState<string | null>(null)
  const [fail, setFail] = useState<Extract<Result, { ok: false }> | null>(null)
  const free = useEntitlements(true)?.tier === "free"
  const [busy, setBusy] = useState(false)
  const first = useRef<HTMLInputElement>(null)
  useEffect(() => {
    first.current?.focus()
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    document.addEventListener("keydown", esc)
    return () => document.removeEventListener("keydown", esc)
  }, [onClose])
  // The upsell shows only for the alert_limit trigger on Free; any other limit shows the server message.
  const upsell = fail?.reason === "limit" && fail.trigger === "alert_limit" && free
  const run = async (send: () => Promise<Result>, after: () => void) => {
    setBusy(true)
    setFail(null)
    const r = await send()
    setBusy(false)
    if (r.ok) after()
    else setFail(r)
  }
  const save = () => {
    const minor = toMinor(v, cur)
    if (minor === null) return setErr(t("flights.alert.bad"))
    setErr(null)
    const target = { amount_minor: minor, currency: cur }
    const body = { target_price: target, notify: { push, email } }
    void run(
      () => (mine ? updateAlert(tripId, mine.id, body) : createAlert(tripId, routeId, body)),
      () => {
        if (!mine) track("fare_alert_created", { kind: "cached" })
        onDone(target)
      },
    )
  }
  return (
    <form className="flights__sheet" role="group" aria-label={t("flights.alert.title")} noValidate onSubmit={(e) => (e.preventDefault(), save())}>
      <h2 className="h-title">{t("flights.alert.title")}</h2>
      {fail && (
        <p role="alert" className="h-input__error flights__note">
          <Icon name="circle-alert" size={16} />
          <span>
            {fail.reason === "limit"
              ? upsell
                ? t("flights.alert.limit")
                : (fail.message ?? t("flights.alert.failed"))
              : t(fail.reason === "forbidden" ? "flights.forbidden" : fail.reason === "conflict" ? "flights.alert.exists" : "flights.alert.failed")}{" "}
            {upsell && <Link to="/account">{t("flights.limitLink")}</Link>}
          </span>
        </p>
      )}
      <TextField label={t("flights.alert.amount")} helper={`${t("flights.alert.currency")}: ${cur}`} inputRef={first} inputMode="decimal" autoComplete="off" value={v} error={err} onChange={(e) => setV(e.target.value)} />
      <label className="flights__check">
        <input type="checkbox" checked={push} onChange={(e) => setPush(e.target.checked)} />
        {t("flights.alert.push")}
      </label>
      <label className="flights__check">
        <input type="checkbox" checked={email} onChange={(e) => setEmail(e.target.checked)} />
        {t("flights.alert.email")}
      </label>
      <p className="h-soft">{t("flights.alert.note")}</p>
      <Btn variant="primary" type="submit" busy={busy}>
        {t("flights.alert.save")}
      </Btn>
      {upsell && (
        <Btn variant="secondary" type="button" onClick={onClose}>
          {t("flights.alert.keep")}
        </Btn>
      )}
      {mine && (
        <Btn variant="secondary" type="button" disabled={busy} onClick={() => void run(() => deleteAlert(tripId, mine.id), onClose)}>
          {t("flights.alert.delete")}
        </Btn>
      )}
      <Btn variant="secondary" type="button" disabled={busy} onClick={onClose}>
        {t("flights.cancel")}
      </Btn>
    </form>
  )
}

/** 05 6.9 alert switch for one route. Off with no alert opens the sheet; with an alert it turns the alert on or off, and Edit opens the sheet. Viewers see nothing. */
export function AlertSwitch({ tripId, routeId, currency, canEdit, online }: { tripId: string; routeId: string; currency: string; canEdit: boolean; online: boolean }) {
  const alerts = useAlerts(tripId, canEdit)
  const [open, setOpen] = useState(false)
  const [said, setSaid] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  if (!canEdit) return null
  const mine = alerts.data?.find((a) => a.route_id === routeId)
  const on = !!mine?.active
  const close = () => {
    setOpen(false)
    document.getElementById(`alert-${routeId}`)?.focus()
  }
  const flip = async () => {
    if (!mine) return setOpen(true)
    setFailed(false)
    setSaid(null)
    const r = await updateAlert(tripId, mine.id, { active: !mine.active })
    if (!r.ok) setFailed(true)
  }
  return (
    <div className="flights__alert">
      <div className="flights__row">
        <span id={`alert-label-${routeId}`}>{t("flights.alert.label")}</span>
        <button id={`alert-${routeId}`} type="button" role="switch" aria-checked={on} aria-labelledby={`alert-label-${routeId}`} className={`flights__switch${on ? " flights__switch--on" : ""}`} disabled={!online || !alerts.data} onClick={() => void flip()}>
          {on ? t("flights.alert.on") : t("flights.alert.off")}
        </button>
      </div>
      {mine && (
        <div className="flights__row">
          <span className="h-soft">{t("flights.alert.below", { amount: formatMoney(mine.target_price.amount_minor, mine.target_price.currency) })}</span>
          <Btn variant="secondary" mod={["sm"]} disabled={!online} onClick={() => setOpen(true)}>
            {t("flights.alert.edit")}
          </Btn>
        </div>
      )}
      {alerts.isError && !alerts.data && (
        <p role="alert" className="h-input__error flights__row">
          {t("flights.alert.error")}
          <Btn variant="secondary" mod={["sm"]} onClick={() => void alerts.refetch()}>
            {t("trips.retry")}
          </Btn>
        </p>
      )}
      {said && (
        <p role="status" className="h-soft">
          {said}
        </p>
      )}
      {failed && (
        <p role="alert" className="h-input__error">
          {t("flights.alert.failed")}
        </p>
      )}
      {open && (
        <AlertSheet
          tripId={tripId}
          routeId={routeId}
          currency={currency}
          mine={mine}
          onClose={close}
          onDone={(m) => {
            setSaid(t("flights.alert.saved", { amount: formatMoney(m.amount_minor, m.currency) }))
            close()
          }}
        />
      )}
    </div>
  )
}

/** The alert list: this person's alerts on the trip, with loading, empty and error states (05 4.5, 6.9). */
export function AlertList({ tripId, routes, name }: { tripId: string; routes: Route[]; name: (r: Route) => string }) {
  const q = useAlerts(tripId, true)
  return (
    <section className="flights__card h-listcard" aria-labelledby="alert-list">
      <h2 className="h-label" id="alert-list">
        {t("flights.alert.listTitle")}
      </h2>
      {q.isPending && <p className="h-soft" aria-live="polite">{t("flights.alert.loading")}</p>}
      {q.isError && !q.data && (
        <>
          <p role="alert" className="h-input__error">
            {t("flights.alert.error")}
          </p>
          <Btn variant="secondary" onClick={() => void q.refetch()}>
            {t("trips.retry")}
          </Btn>
        </>
      )}
      {q.data?.length === 0 && <p className="h-soft">{t("flights.alert.empty")}</p>}
      <ul className="flights__list">
        {q.data?.map((a) => {
          const r = routes.find((x) => x.id === a.route_id)
          const label = r ? name(r) : a.route_id
          return (
            <li key={a.id} className="flights__fare" aria-label={label}>
              <span className="h-mono flights__code">{label}</span>
              <span className="flights__meta">{t("flights.alert.below", { amount: formatMoney(a.target_price.amount_minor, a.target_price.currency) })}</span>
              <span className="h-chip">{a.active ? t("flights.alert.on") : t("flights.alert.off")}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
