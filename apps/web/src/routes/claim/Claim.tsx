import { useEffect, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router"
import { Btn, Icon, Logo } from "../../components/kit"
import { Skeleton } from "../../components/Skeleton"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { useAuth } from "../auth/authStore"
import { pendingClaim, redeemClaim, type ClaimResult } from "./redeem"
import "../auth/auth.css"
import "../trips/trips.css"

/**
 * /claim/:token (04 section 5.1, WF-040). The emailed one-time link attaches the signed-in account to the owner's imported
 * data. Signed out: sign in first and come back. shortcut: "Ask for a new link" is guidance only, there is no self-serve
 * resend endpoint yet. Add one when the importer's email job lands.
 */
export function Claim() {
  const { token = "" } = useParams()
  const auth = useAuth()
  const nav = useNavigate()
  const online = useOnline()
  const [failure, setFailure] = useState<Exclude<ClaimResult, { ok: true }>["reason"] | null>(null)
  const [attempt, setAttempt] = useState(0)
  const ran = useRef<string | null>(null)

  useEffect(() => {
    if (!auth.token) {
      pendingClaim.set(token)
      void nav("/sign-in", { replace: true })
      return
    }
    const key = `${token}:${attempt}`
    if (ran.current === key) return // StrictMode runs effects twice; the token works once
    ran.current = key
    setFailure(null)
    void redeemClaim(token).then((r) => {
      pendingClaim.clear()
      if (r.ok) nav("/", { replace: true })
      else setFailure(r.reason)
    })
  }, [auth.token, token, attempt, nav])

  const message = failure && t(`claim.${failure}`)
  return (
    <main className="auth">
      <div className="auth__panel">
        <div className="auth__brand">
          <Logo variant="lockup" height={56} />
        </div>
        <h1 className="h-title auth__title">{t("claim.title")}</h1>
        {!failure && (
          <div role="status" aria-busy="true">
            <p className="h-soft auth__note">{t("claim.redeeming")}</p>
            <Skeleton shape="block" />
          </div>
        )}
        {message && (
          <p role="alert" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {message}
          </p>
        )}
        {failure === "failed" && (
          <Btn variant="primary" disabled={!online} onClick={() => setAttempt((n) => n + 1)}>
            {t("claim.retry")}
          </Btn>
        )}
        {failure === "has_account" && (
          <Btn variant="secondary" onClick={() => nav("/")}>
            {t("claim.toTrips")}
          </Btn>
        )}
      </div>
    </main>
  )
}
