import { useState, type FormEvent } from "react"
import { Btn, Icon, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { adminRequest, type AdminFail } from "./adminClient"
import type { AdminSession } from "./session"
import { createPasskey, passkeysSupported, PasskeyCancelled } from "./webauthn"

type Totp = { secret: string; otpauth_uri: string }

/**
 * 08 2.2 enrolment: one factor (passkey preferred, authenticator app as the fallback), then the recovery code set.
 * `mfa_enrolled` turns true when the codes are made, so the codes stay on screen here until the admin says they are
 * saved; only then does the shell read the session again.
 */
export function Enrol({ session, onDone }: { session: AdminSession; onDone: () => void }) {
  const [factor, setFactor] = useState(session.factors.passkeys > 0 || session.factors.totp)
  const [totp, setTotp] = useState<Totp | null>(null)
  const [code, setCode] = useState("")
  const [codes, setCodes] = useState<string[] | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fail = (r: AdminFail) => setError(r.offline ? t("states.error.offline") : r.message || t("admin.enrol.failed"))
  const makeCodes = async () => {
    setBusy("codes")
    const r = await adminRequest<{ codes: string[] }>("POST", "/v1/admin/auth/recovery-codes")
    setBusy(null)
    if (r.ok) setCodes(r.data.codes)
    else fail(r)
  }
  const factorReady = async () => {
    setFactor(true)
    setTotp(null)
    await makeCodes()
  }
  const passkey = async () => {
    setBusy("passkey")
    setError(null)
    const opts = await adminRequest<{ challenge_id: string; public_key: Record<string, unknown> }>("POST", "/v1/admin/auth/webauthn/register/options")
    if (!opts.ok) {
      setBusy(null)
      return fail(opts)
    }
    try {
      const made = await createPasskey(opts.data.public_key)
      const r = await adminRequest("POST", "/v1/admin/auth/webauthn/register/verify", { challenge_id: opts.data.challenge_id, ...made }) // no label: the server names it "Passkey"
      if (!r.ok) {
        setBusy(null)
        return fail(r)
      }
      setBusy(null)
      await factorReady()
    } catch (e) {
      setBusy(null)
      if (!(e instanceof PasskeyCancelled)) setError(t("admin.enrol.failed"))
    }
  }
  const startTotp = async () => {
    setBusy("totp")
    setError(null)
    const r = await adminRequest<Totp>("POST", "/v1/admin/auth/totp/enrol")
    setBusy(null)
    if (r.ok) setTotp(r.data)
    else fail(r)
  }
  const confirmTotp = async (e: FormEvent) => {
    e.preventDefault()
    setBusy("confirm")
    setError(null)
    const r = await adminRequest("POST", "/v1/admin/auth/totp/confirm", { code: code.trim() })
    setBusy(null)
    if (r.ok) await factorReady()
    else fail(r)
  }

  return (
    <main className="admin-center">
      <div className="admin-panel">
        <h1 className="h-title">{t("admin.enrol.title")}</h1>
        <p className="h-soft">{t("admin.enrol.intro")}</p>

        {codes && (
          <section aria-labelledby="admin-codes-title" className="admin-panel">
            <h2 id="admin-codes-title" className="h-heading">
              {t("admin.enrol.codesTitle")}
            </h2>
            <p className="h-soft">{t("admin.enrol.codesBody")}</p>
            <ul className="admin-codes h-mono">
              {codes.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <Btn variant="primary" onClick={onDone}>
              {t("admin.enrol.codesSaved")}
            </Btn>
          </section>
        )}

        {!codes && factor && (
          <>
            <p className="h-soft">{t("admin.enrol.factorDone")}</p>
            <Btn variant="primary" busy={busy === "codes"} onClick={() => void makeCodes()}>
              {t("admin.enrol.codesCreate")}
            </Btn>
          </>
        )}

        {!codes && !factor && !totp && (
          <>
            {passkeysSupported() ? (
              <>
                <Btn variant="primary" busy={busy === "passkey"} disabled={busy !== null && busy !== "passkey"} onClick={() => void passkey()}>
                  {t("admin.enrol.passkey")}
                </Btn>
                <p className="h-soft">{t("admin.enrol.passkeyHelper")}</p>
              </>
            ) : (
              <p className="h-soft">{t("admin.enrol.passkeyUnsupported")}</p>
            )}
            <Btn variant="secondary" busy={busy === "totp"} disabled={busy !== null && busy !== "totp"} onClick={() => void startTotp()}>
              {t("admin.enrol.totp")}
            </Btn>
            <p className="h-soft">{t("admin.enrol.totpHelper")}</p>
          </>
        )}

        {!codes && !factor && totp && (
          // shortcut: no QR image (no QR library is installed). The secret and the otpauth link cover every authenticator
          // app. Add a QR when a package is approved.
          <form className="admin-panel" onSubmit={(e) => void confirmTotp(e)} noValidate>
            <p className="h-soft">{t("admin.enrol.totpSecret")}</p>
            <p className="admin-secret h-mono">{totp.secret}</p>
            <a className="state__link" href={totp.otpauth_uri}>
              {t("admin.enrol.totpLink")}
            </a>
            <TextField
              label={t("admin.enrol.totpCode")}
              code
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={8}
              value={code}
              error={error}
              onChange={(e) => setCode(e.target.value.replace(/\s/g, ""))}
            />
            <Btn variant="primary" type="submit" busy={busy === "confirm"}>
              {t("admin.enrol.totpConfirm")}
            </Btn>
          </form>
        )}

        {error && !(totp && !factor) && (
          <p role="alert" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {error}
          </p>
        )}
      </div>
    </main>
  )
}
