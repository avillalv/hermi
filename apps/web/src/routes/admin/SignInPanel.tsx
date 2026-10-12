import { useState, type FormEvent } from "react"
import { Btn, Icon, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { adminRequest } from "./adminClient"
import { passkeyProof, type AdminSession, type Proof } from "./session"
import { passkeysSupported } from "./webauthn"

/** 08 2.2, second layer: a passkey, an authenticator code or a recovery code opens the 2FA session. */
export function SignInPanel({ session, ended, onSignedIn }: { session: AdminSession; ended: boolean; onSignedIn: (s: AdminSession) => void }) {
  const online = useOnline()
  const { passkeys, totp } = session.factors
  // The person can switch; until then the factors on file decide (the session may still be refreshing after enrolment).
  const [picked, setMode] = useState<"code" | "recovery" | null>(null)
  const mode = picked ?? (totp || passkeys > 0 ? "code" : "recovery")
  const [code, setCode] = useState("")
  const [busy, setBusy] = useState<"code" | "passkey" | null>(null)
  const [error, setError] = useState<string | null>(null)
  const canPasskey = passkeys > 0 && passkeysSupported()

  const send = async (proof: Proof, what: "code" | "passkey") => {
    setBusy(what)
    setError(null)
    const r = await adminRequest<AdminSession>("POST", "/v1/admin/auth/signin", proof)
    setBusy(null)
    if (r.ok) onSignedIn(r.data)
    else setError(r.offline ? t("states.error.offline") : r.message || t("admin.enrol.failed"))
  }
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (code.trim()) void send({ method: mode === "recovery" ? "recovery" : "totp", code: code.trim() }, "code")
  }
  const passkey = async () => {
    setBusy("passkey")
    setError(null)
    const p = await passkeyProof("signin")
    setBusy(null)
    if (p === null) return
    if (!p.ok) return setError(p.offline ? t("states.error.offline") : p.message || t("admin.enrol.failed"))
    await send(p.data, "passkey")
  }

  const disabled = !online || busy !== null
  return (
    <main className="admin-center">
      <form className="admin-panel" onSubmit={submit} noValidate>
        <h1 className="h-title">{t("admin.signIn.title")}</h1>
        {ended && (
          <p role="status" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("admin.signIn.ended")}
          </p>
        )}
        {!online && (
          <p role="status" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("states.error.offline")}
          </p>
        )}
        <p className="h-soft">{t("admin.signIn.intro")}</p>
        {passkeys > 0 && !canPasskey && <p className="h-soft">{t("admin.signIn.noPasskeys")}</p>}
        {canPasskey && (
          <Btn variant="primary" busy={busy === "passkey"} disabled={disabled && busy !== "passkey"} onClick={() => void passkey()}>
            {t("admin.signIn.passkey")}
          </Btn>
        )}
        {mode === "code" && (totp || !canPasskey) && (
          <TextField
            label={t("admin.signIn.totp")}
            code
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={8}
            value={code}
            helper={t("admin.signIn.totpHelper")}
            error={error}
            onChange={(e) => setCode(e.target.value.replace(/\s/g, ""))}
          />
        )}
        {mode === "recovery" && (
          <TextField
            label={t("admin.signIn.recovery")}
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            value={code}
            helper={t("admin.signIn.recoveryHelper")}
            error={error}
            onChange={(e) => setCode(e.target.value.trim())}
          />
        )}
        {mode === "code" && !totp && error && (
          <p role="alert" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {error}
          </p>
        )}
        {(mode === "recovery" || totp) && (
          <Btn variant={canPasskey ? "secondary" : "primary"} type="submit" busy={busy === "code"} disabled={disabled && busy !== "code"}>
            {t("admin.signIn.submit")}
          </Btn>
        )}
        <Btn
          variant="text"
          disabled={busy !== null}
          onClick={() => {
            setCode("")
            setError(null)
            setMode(mode === "recovery" ? "code" : "recovery")
          }}
        >
          {mode === "recovery" ? t("admin.signIn.backToCode") : t("admin.signIn.recoveryLink")}
        </Btn>
      </form>
    </main>
  )
}
