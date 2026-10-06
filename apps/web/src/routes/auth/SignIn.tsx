import { useEffect, useRef, useState, type FormEvent } from "react"
import { pendingClaim } from "../claim/redeem"
import { pendingInvite } from "../invite/collab"
import { Navigate } from "react-router"
import { Btn, Icon, Logo, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { api } from "./api"
import { authStore, useAuth } from "./authStore"
import { AuthError, identity, type AuthErrorCode, type IdentityAdapter } from "./identity"
import "./auth.css"

type Persona = { persona: string; label: string }
type Step = "options" | "email" | "code"

const COPY: Record<AuthErrorCode, string> = {
  wrong_code: "auth.errors.wrongCode",
  expired: "auth.errors.expired",
  rate_limited: "auth.errors.rateLimited",
  offline: "auth.errors.offline",
  unavailable: "auth.errors.unavailable",
}
const RESEND_SECONDS = 30
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** 05 6.3. Apple, Google and email code, plus the persona picker when the API runs with AUTH_MODE=dev. */
export function SignIn({ adapter = identity }: { adapter?: IdentityAdapter }) {
  const { token } = useAuth()
  const online = useOnline()
  const [step, setStep] = useState<Step>("options")
  const [personas, setPersonas] = useState<Persona[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState("")
  const [code, setCode] = useState("")
  const [wrong, setWrong] = useState(0)
  const [wait, setWait] = useState(0)
  const emailRef = useRef<HTMLInputElement>(null)

  // The dev routes exist only when AUTH_MODE=dev (04 1.2); a 404 means a real deployment, so no picker.
  useEffect(() => {
    const ac = new AbortController()
    api
      .get<Persona[]>("/v1/dev/personas", { signal: ac.signal })
      .then((r) => Array.isArray(r.data) && setPersonas(r.data))
      .catch(() => {})
    return () => ac.abort()
  }, [])

  useEffect(() => {
    if (wait <= 0) return
    const id = setTimeout(() => setWait((w) => w - 1), 1000)
    return () => clearTimeout(id)
  }, [wait])

  // A signed-in user is sent to Trips by the <Navigate> below.
  const done = (t: string, persona?: string) => authStore.signIn(t, persona)

  // After an OAuth redirect or a reload the provider already holds the session.
  useEffect(() => {
    let live = true
    adapter
      .restore?.()
      .then((t) => live && t && done(t))
      .catch(() => {})
    return () => {
      live = false
    }
  }, [adapter])
  const run = async (what: string, fn: () => Promise<void>) => {
    setBusy(what)
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(t(e instanceof AuthError ? COPY[e.code] : "auth.errors.generic"))
      if (e instanceof AuthError && e.code === "wrong_code") setWrong((n) => n + 1)
    } finally {
      setBusy(null)
    }
  }

  const pickPersona = (p: Persona) =>
    run(`persona:${p.persona}`, async () => {
      const r = await api.post<{ access_token: string }>("/v1/dev/session", { persona: p.persona })
      if (!r.data?.access_token) throw new Error("no session")
      done(r.data.access_token, p.persona)
    })
  const sendCode = (e?: FormEvent) => {
    e?.preventDefault()
    if (!EMAIL.test(email.trim())) {
      setError(t("auth.errors.invalidEmail"))
      emailRef.current?.focus()
      return
    }
    void run("send", async () => {
      await adapter.sendCode(email.trim())
      setCode("")
      setWrong(0)
      setWait(RESEND_SECONDS)
      setStep("code")
    })
  }
  const onCode = (v: string) => {
    const digits = v.replace(/\D/g, "").slice(0, 6)
    setCode(digits)
    if (digits.length === 6) void run("verify", async () => done(await adapter.verifyCode(email.trim(), digits)))
  }

  // Only the busy button keeps its place (aria-busy); the others are disabled while a request runs.
  const lock = (key: string) => ({ busy: busy === key, disabled: !online || (busy !== null && busy !== key) })
  const alert = error ? (
    <p role="alert" className="h-input__error">
      <Icon name="circle-alert" size={16} />
      {error}
    </p>
  ) : null
  if (token) return <Navigate to={pendingClaim.target() ?? pendingInvite.target()} replace />

  return (
    <main className="auth">
      <div className="auth__panel">
        <div className="auth__brand">
          <Logo variant="lockup" height={56} />
        </div>
        <h1 className="h-title auth__title">{t("auth.title")}</h1>
        {!online && (
          <p role="status" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("auth.errors.offline")}
          </p>
        )}

        {step === "options" && (
          <>
            <div className="auth__stack">
              <Btn variant="primary" mod={["apple"]} {...lock("apple")} onClick={() => void run("apple", async () => done(await adapter.oauth("apple")))}>
                {t("auth.apple")}
              </Btn>
              <Btn variant="secondary" {...lock("google")} onClick={() => void run("google", async () => done(await adapter.oauth("google")))}>
                {t("auth.google")}
              </Btn>
              <Btn
                variant="secondary"
                disabled={!online || busy !== null}
                onClick={() => {
                  setError(null)
                  setStep("email")
                }}
              >
                {t("auth.email")}
              </Btn>
              {alert}
            </div>
            {personas.length > 0 && (
              <section className="auth__dev auth__stack" aria-labelledby="auth-dev">
                <h2 id="auth-dev" className="h-soft">
                  {t("auth.devTitle")}
                </h2>
                <p className="h-soft">{t("auth.devHelper")}</p>
                {personas.map((p) => (
                  <Btn key={p.persona} variant="secondary" {...lock(`persona:${p.persona}`)} onClick={() => void pickPersona(p)}>
                    {p.label}
                  </Btn>
                ))}
              </section>
            )}
          </>
        )}

        {step === "email" && (
          <form className="auth__stack" onSubmit={sendCode} noValidate>
            <TextField
              label={t("auth.emailLabel")}
              inputRef={emailRef}
              type="email"
              inputMode="email"
              autoComplete="email"
              value={email}
              helper={t("auth.emailHelper")}
              error={error}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Btn variant="primary" type="submit" {...lock("send")}>
              {t("auth.sendCode")}
            </Btn>
          </form>
        )}

        {step === "code" && (
          <div className="auth__stack">
            <div className="auth__field">
              <TextField
                label={t("auth.codeLabel")}
                code
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={code}
                disabled={busy === "verify"}
                helper={t("auth.codeHelper", { email })}
                error={error}
                onChange={(e) => onCode(e.target.value)}
              />
              {wrong >= 3 && <p className="h-soft">{t("auth.errors.wrongCodeWarning")}</p>}
            </div>
            <Btn variant="secondary" {...lock("send")} disabled={!online || busy !== null || wait > 0} onClick={() => sendCode()}>
              {wait > 0 ? t("auth.resendIn", { seconds: wait }) : t("auth.resend")}
            </Btn>
            <Btn
              variant="text"
              onClick={() => {
                setError(null)
                setCode("")
                setStep("email")
              }}
            >
              {t("auth.differentEmail")}
            </Btn>
          </div>
        )}

        <p className="h-fine auth__note">{t("auth.legal")}</p>
      </div>
    </main>
  )
}
