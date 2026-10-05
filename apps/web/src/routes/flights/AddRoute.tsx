import { useEffect, useRef, useState } from "react"
import { Link } from "react-router"
import { Btn, Icon, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { addRoute, type Result } from "./api"

const IATA = /^[A-Z]{3}$/
const codes = (s: string) => s.split(/[\s,]+/).filter(Boolean).map((c) => c.toUpperCase())

/**
 * 05 6.9 Add route. shortcut: an inline panel (Escape and Cancel close it), like the invite panel, not a modal sheet.
 * Exact dates only; a date window and trip length need the date picker kit block. Upgrade with the paywall sheet (WF-064).
 */
export function AddRoute({ tripId, start, end, maxPerSide, onClose }: { tripId: string; start: string | null; end: string | null; maxPerSide: number; onClose: () => void }) {
  const [v, setV] = useState({ from: "", to: "", leave: start ?? "", back: end ?? "", people: "1" })
  const [err, setErr] = useState<Partial<Record<"from" | "to" | "leave" | "back", string>>>({})
  const [fail, setFail] = useState<Extract<Result, { ok: false }>["reason"] | null>(null)
  const [busy, setBusy] = useState(false)
  const first = useRef<HTMLInputElement>(null)
  const panel = useRef<HTMLElement>(null)
  useEffect(() => first.current?.focus(), [])
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && panel.current?.contains(document.activeElement) && onClose()
    document.addEventListener("keydown", esc)
    return () => document.removeEventListener("keydown", esc)
  }, [onClose])
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }))

  const side = (s: string) => {
    const c = codes(s)
    return c.length === 0 || !c.every((x) => IATA.test(x)) ? t("flights.airportBad") : c.length > maxPerSide ? t("flights.airportMany", { max: maxPerSide }) : undefined
  }
  const submit = async () => {
    const e = {
      from: side(v.from),
      to: side(v.to),
      leave: v.leave ? undefined : t("flights.dateNeeded"),
      back: v.back && v.leave && v.back < v.leave ? t("flights.dateOrder") : undefined,
    }
    setErr(e)
    if (Object.values(e).some(Boolean)) return
    setBusy(true)
    const oneWay = !v.back
    const r = await addRoute(tripId, {
      origin_codes: codes(v.from),
      destination_codes: codes(v.to),
      trip_type: oneWay ? "one_way" : "round_trip",
      depart_from: v.leave,
      depart_to: v.leave,
      return_from: oneWay ? null : v.back,
      return_to: oneWay ? null : v.back,
      adults: Math.min(9, Math.max(1, Number(v.people) || 1)),
      mode: "cached",
    })
    setBusy(false)
    if (r.ok) {
      const days = Math.max(0, Math.round((Date.parse(v.leave) - Date.now()) / 86_400_000))
      track("flight_route_added", { route_type: oneWay ? "one_way" : "round_trip", days_to_departure_bucket: days <= 30 ? "0_30" : days <= 90 ? "31_90" : "91_plus" })
      onClose()
    } else setFail(r.reason)
  }
  return (
    <section className="flights__sheet" aria-labelledby="flights-add" ref={panel}>
      <h2 className="h-label" id="flights-add">
        {t("flights.sheetTitle")}
      </h2>
      {fail && (
        <p role="alert" className="h-input__error flights__note">
          <Icon name="circle-alert" size={16} />
          <span>
            {t(fail === "limit" ? "flights.limit" : fail === "forbidden" ? "flights.forbidden" : fail === "invalid" ? "flights.invalid" : "flights.failed")}{" "}
            {fail === "limit" && <Link to="/account">{t("flights.limitLink")}</Link>}
          </span>
        </p>
      )}
      <form className="flights__form" onSubmit={(e) => (e.preventDefault(), void submit())} noValidate>
        <TextField label={t("flights.from")} helper={t("flights.fromHelp", { max: maxPerSide })} inputRef={first} value={v.from} error={err.from} autoComplete="off" onChange={set("from")} />
        <TextField label={t("flights.to")} value={v.to} error={err.to} autoComplete="off" onChange={set("to")} />
        <TextField label={t("flights.leave")} type="date" value={v.leave} error={err.leave} onChange={set("leave")} />
        <TextField label={t("flights.back")} helper={t("flights.backHelp")} type="date" value={v.back} error={err.back} onChange={set("back")} />
        <TextField label={t("flights.people")} type="number" min={1} max={9} value={v.people} onChange={set("people")} />
        <div className="flights__row">
          <Btn variant="primary" type="submit" busy={busy}>
            {t("flights.save")}
          </Btn>
          <Btn variant="secondary" onClick={onClose}>
            {t("flights.cancel")}
          </Btn>
        </div>
      </form>
    </section>
  )
}
