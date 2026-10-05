import { useState, type FormEvent } from "react"
import { Navigate, useNavigate } from "react-router"
import { Btn, Icon, Logo, Sprite, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { api } from "../auth/api"
import { useAuth } from "../auth/authStore"
import { markOnboarded } from "./trips"
import "../auth/auth.css"
import "./onboarding.css"

const EU_UK = new Set("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE GB".split(" "))
/** 13 and over, 16 and over for EU and UK locales (05 6.1). */
const minAge = () => (EU_UK.has((navigator.language.split("-")[1] ?? "").toUpperCase()) ? 16 : 13)

/** Age gate (05 6.1) and the skippable profile sheet (05 6.4), then POST /me/bootstrap, which creates the "Me" traveler. */
export function Onboarding() {
  const { token } = useAuth()
  const nav = useNavigate()
  const online = useOnline()
  const age = minAge()
  const [confirmed, setConfirmed] = useState(false)
  const [name, setName] = useState("")
  const [airport, setAirport] = useState("")
  const [currency, setCurrency] = useState("")
  const [busy, setBusy] = useState<"save" | "skip" | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<{ airport?: string; currency?: string }>({})
  if (!token) return <Navigate to="/sign-in" replace />

  const submit = async (profile: boolean) => {
    if (!confirmed) return setError(t("onboarding.ageRequired"))
    const bad3 = (v: string) => !!v.trim() && !/^[a-z]{3}$/i.test(v.trim())
    const fe = profile
      ? { airport: bad3(airport) ? t("onboarding.airportInvalid") : undefined, currency: bad3(currency) ? t("onboarding.currencyInvalid") : undefined }
      : {}
    setFieldErrors(fe)
    if (fe.airport || fe.currency) return
    setBusy(profile ? "save" : "skip")
    setError(null)
    const body: Record<string, unknown> = { age_confirmed: true }
    if (profile) {
      if (name.trim()) body.display_name = name.trim()
      if (/^[a-z]{3}$/i.test(airport.trim())) body.home_airports = [airport.trim().toUpperCase()]
      if (/^[a-z]{3}$/i.test(currency.trim())) body.home_currency = currency.trim().toUpperCase()
    }
    try {
      const r = await api.post("/v1/me/bootstrap", body)
      if (r.response.status === 409) {
        setError(t("onboarding.emailInUse"))
        return setBusy(null)
      }
      if (r.error !== undefined) throw new Error(String(r.response.status))
      markOnboarded()
      nav("/trips/new", { replace: true })
    } catch {
      setError(t("onboarding.failed"))
      setBusy(null)
    }
  }
  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void submit(true)
  }

  return (
    <main className="auth">
      <form className="auth__panel" onSubmit={onSubmit} noValidate>
        <Sprite />
        <div className="auth__brand">
          <Logo variant="lockup" height={56} />
        </div>
        <h1 className="h-title auth__title">{t("onboarding.title")}</h1>
        <div className="auth__stack">
          <label className="onboarding__age">
            <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
            {t("onboarding.ageLabel", { age })}
          </label>
          <p className="h-soft">{t("onboarding.ageHelper", { age })}</p>
        </div>
        <h2 className="h-title">{t("onboarding.profileTitle")}</h2>
        <p className="h-soft">{t("onboarding.profileHelper")}</p>
        <div className="auth__stack">
          <TextField label={t("onboarding.name")} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
          <TextField
            label={t("onboarding.airport")}
            helper={t("onboarding.airportHelper")}
            error={fieldErrors.airport}
            maxLength={3}
            value={airport}
            onChange={(e) => setAirport(e.target.value)}
          />
          <TextField label={t("onboarding.currency")} error={fieldErrors.currency} maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value)} />
        </div>
        {!online && (
          <p role="status" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("onboarding.offline")}
          </p>
        )}
        {error && (
          <p role="alert" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {error}
          </p>
        )}
        <div className="auth__stack">
          <Btn variant="primary" type="submit" busy={busy === "save"} disabled={!online || busy === "skip"}>
            {t("onboarding.save")}
          </Btn>
          <Btn variant="secondary" busy={busy === "skip"} disabled={!online || busy === "save"} onClick={() => void submit(false)}>
            {t("onboarding.skip")}
          </Btn>
        </div>
      </form>
    </main>
  )
}
