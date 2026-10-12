import { useQueryClient } from "@tanstack/react-query"
import { useEffect, useRef, useState, type FormEvent } from "react"
import { Btn, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { adminRequest, setStepUpHandler } from "./adminClient"
import { passkeyProof, SESSION_KEY, type AdminSession, type Proof } from "./session"
import { passkeysSupported } from "./webauthn"

/**
 * The step-up check (08 2.2): a fresh passkey or authenticator code, valid 5 minutes. Mounted once in the shell. It
 * answers any call that got a 428 (`adminRequest` asks it) and lets that call repeat once. A recovery code is not a
 * step-up factor, so it is not offered here.
 */
export function StepUpDialog({ factors }: { factors: AdminSession["factors"] }) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [code, setCode] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const settle = useRef<((ok: boolean) => void) | null>(null)
  const box = useRef<HTMLFormElement>(null)
  const opener = useRef<HTMLElement | null>(null)

  useEffect(() => {
    setStepUpHandler(
      () =>
        new Promise<boolean>((resolve) => {
          settle.current = resolve
          opener.current = document.activeElement as HTMLElement | null
          setCode("")
          setError(null)
          setOpen(true)
        }),
    )
    return () => setStepUpHandler(null)
  }, [])
  const focusables = () =>
    Array.from(box.current?.querySelectorAll<HTMLElement>("input, button, a[href]") ?? []).filter((el) => !(el as HTMLButtonElement).disabled)
  // Focus the first control on open and give it back to whatever opened the dialog on close.
  useEffect(() => {
    if (!open) return
    focusables()[0]?.focus()
    return () => opener.current?.focus?.()
  }, [open])
  // Escape cancels; Tab stays inside the dialog.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) return close(false)
      if (e.key !== "Tab") return
      const els = focusables()
      if (els.length === 0) return
      const first = els[0]
      const last = els[els.length - 1]
      const at = document.activeElement
      if (!box.current?.contains(at)) (e.shiftKey ? last : first).focus()
      else if (e.shiftKey && at === first) last.focus()
      else if (!e.shiftKey && at === last) first.focus()
      else return
      e.preventDefault()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [open, busy])

  const close = (ok: boolean) => {
    setOpen(false)
    settle.current?.(ok)
    settle.current = null
  }
  const verify = async (proof: Proof) => {
    setBusy(true)
    setError(null)
    const r = await adminRequest<AdminSession>("POST", "/v1/admin/auth/stepup", proof)
    setBusy(false)
    if (r.ok) {
      qc.setQueryData(SESSION_KEY, r)
      close(true)
    } else setError(r.offline ? t("states.error.offline") : r.message || t("admin.enrol.failed"))
  }
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (code.trim()) void verify({ method: "totp", code: code.trim() })
  }
  const passkey = async () => {
    setBusy(true)
    const p = await passkeyProof("stepup")
    setBusy(false)
    if (p === null) return
    if (!p.ok) return setError(p.offline ? t("states.error.offline") : p.message || t("admin.enrol.failed"))
    await verify(p.data)
  }

  if (!open) return null
  const canPasskey = factors.passkeys > 0 && passkeysSupported()
  return (
    <div className="admin-modal">
      <form ref={box} className="admin-modal__box" role="dialog" aria-modal="true" aria-labelledby="admin-stepup-title" onSubmit={submit} noValidate>
        <h2 id="admin-stepup-title" className="h-heading">
          {t("admin.stepUp.title")}
        </h2>
        <p className="h-soft">{t("admin.stepUp.body")}</p>
        {factors.totp && (
          <TextField
            label={t("admin.stepUp.totp")}
            code
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={8}
            value={code}
            error={error}
            onChange={(e) => setCode(e.target.value.replace(/\s/g, ""))}
          />
        )}
        {!factors.totp && error && (
          <p role="alert" className="h-input__error">
            {error}
          </p>
        )}
        {factors.totp && (
          <Btn variant="primary" type="submit" busy={busy}>
            {t("admin.stepUp.confirm")}
          </Btn>
        )}
        {canPasskey && (
          <Btn variant={factors.totp ? "secondary" : "primary"} disabled={busy} onClick={() => void passkey()}>
            {t("admin.stepUp.passkey")}
          </Btn>
        )}
        <Btn variant="text" disabled={busy} onClick={() => close(false)}>
          {t("admin.stepUp.cancel")}
        </Btn>
      </form>
    </div>
  )
}
