import { useEffect, useRef, useState } from "react"
import { Link } from "react-router"
import { Btn, Icon, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import type { Trip } from "../trips/api"
import { createInvite, createShareLink, revokeInvite, type Invite, type Result } from "./collab"

type Msg = "failed" | "pending" | "cap" | "forbidden" | "copied" | "emailReady"
const EMAIL = /^[^@\s]+@[^@\s]+$/
const ERRORS: Msg[] = ["failed", "pending", "cap", "forbidden"]
const day = (iso: string) => new Date(iso).toLocaleDateString("en", { month: "short", day: "numeric" })

/** Native share sheet where there is one, else the clipboard. */
async function share(url: string): Promise<"shared" | "copied"> {
  if (navigator.share) {
    try {
      await navigator.share({ url, title: "Hermi" })
      return "shared"
    } catch (e) {
      if ((e as Error).name === "AbortError") return "shared"
    }
  }
  await navigator.clipboard.writeText(url)
  return "copied"
}

/**
 * 05 6.8 Invite sheet. shortcut: an inline panel in the Group section, not a modal sheet; it has a visible Close and
 * Escape closes it. Upgrade when the shared sheet lands with the paywall sheet (WF-064). The API sends no mail yet, so
 * "Create invite" with an email makes the link to share, and Resend is the same call as Regenerate.
 */
export function InviteSheet({ trip, owner, ownerName, pending, onClose }: { trip: Trip; owner: boolean; ownerName: string; pending: Invite[]; onClose: () => void }) {
  const online = useOnline()
  const panel = useRef<HTMLElement>(null)
  const [role, setRole] = useState<"editor" | "viewer">(owner ? "editor" : "viewer")
  const [email, setEmail] = useState("")
  const [emailError, setEmailError] = useState<string>()
  const [busy, setBusy] = useState<string | null>(null)
  const [msg, setMsg] = useState<Msg | null>(null)
  const [sentTo, setSentTo] = useState("")
  const [paywall, setPaywall] = useState(false)
  const [readOnly, setReadOnly] = useState(false)

  const fail = (r: Extract<Result, { ok: false }>) => {
    if (r.reason === "paywall") setPaywall(true)
    else setMsg(r.reason === "pending" || r.reason === "cap" || r.reason === "forbidden" ? r.reason : "failed")
  }
  const send = async (key: string, to?: string, replace?: string, as: "editor" | "viewer" = role) => {
    setBusy(key)
    setMsg(null)
    if (replace) {
      const old = await revokeInvite(trip.id, replace)
      if (!old.ok) return setBusy(null), fail(old)
    }
    const r = await createInvite(trip.id, as, to)
    if (!r.ok) return setBusy(null), fail(r)
    track("invite_sent", { channel: to ? "email" : "link", role: as })
    try {
      const how = r.data.url ? await share(r.data.url) : "shared"
      setSentTo(to ?? "")
      setMsg(to ? "emailReady" : how === "copied" ? "copied" : null)
    } catch {
      setMsg("failed")
    }
    setBusy(null)
  }
  const sendEmail = () => {
    if (!EMAIL.test(email.trim())) return setEmailError(t("invite.emailBad"))
    setEmailError(undefined)
    void send("email", email.trim()).then(() => setEmail(""))
  }
  const viewLink = async () => {
    setBusy("ro")
    const r = await createShareLink(trip.id)
    if (!r.ok) return setBusy(null), fail(r)
    if (r.data.url) await share(r.data.url).catch(() => undefined)
    setReadOnly(true)
    setBusy(null)
  }
  const revoke = async (id: string) => {
    setBusy(id)
    const r = await revokeInvite(trip.id, id)
    setBusy(null)
    if (!r.ok) fail(r)
  }
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && panel.current?.contains(document.activeElement) && onClose()
    document.addEventListener("keydown", esc)
    return () => document.removeEventListener("keydown", esc)
  }, [onClose])
  const off = !online || busy !== null
  const open = pending.filter((i) => i.status === "pending")
  const text: Record<Msg, string> = {
    failed: t("invite.failed"),
    pending: t("invite.pendingLimit"),
    cap: t("invite.cap"),
    forbidden: t("invite.forbidden"),
    copied: t("invite.copied"),
    emailReady: t("invite.emailReady", { email: sentTo }),
  }
  const isErr = !!msg && ERRORS.includes(msg)

  return (
    <section aria-labelledby="invite-sheet-title" className="group__form" ref={panel}>
      <div className="overview__row">
        <h3 className="h-title" id="invite-sheet-title">{t("invite.sheet")}</h3>
        <Btn variant="text" mod={["sm"]} aria-label={t("invite.close")} onClick={onClose}>
          <Icon name="x" size={18} />
        </Btn>
      </div>
      {!online && (
        <p role="status" className="h-input__error trips__note">
          <Icon name="circle-alert" size={16} />
          {t("invite.offline")}
        </p>
      )}
      {!owner && <p className="h-soft">{t("group.onlyOwner", { name: ownerName })}</p>}
      <div role="radiogroup" aria-label={t("invite.role")} className="overview__row">
        {(owner ? (["editor", "viewer"] as const) : (["viewer"] as const)).map((r) => (
          <label key={r} className="overview__row">
            <input type="radio" name="invite-role" checked={role === r} onChange={() => setRole(r)} />
            {t(`group.role.${r}`)}
          </label>
        ))}
      </div>
      <p className="h-soft">{t("invite.free")}</p>
      <Btn variant="primary" busy={busy === "link"} disabled={off && busy !== "link"} aria-label={t("invite.shareAria")} onClick={() => void send("link")}>
        <Icon name="external-link" size={18} />
        {t("invite.shareLink")}
      </Btn>
      <form onSubmit={(e) => (e.preventDefault(), sendEmail())} className="group__form" aria-label={t("invite.emailTitle")}>
        <TextField label={t("invite.email")} type="email" value={email} error={emailError} autoComplete="off" onChange={(e) => setEmail(e.target.value)} />
        <Btn variant="secondary" type="submit" busy={busy === "email"} disabled={off && busy !== "email"}>
          {t("invite.emailSend")}
        </Btn>
      </form>
      {paywall && (
        <div role="alert" className="group__form">
          <strong>{t("invite.paywallTitle")}</strong>
          <span className="h-soft">{t("invite.paywallBody")}</span>
          <Link to="/account" className="h-btn h-btn--primary">
            {t("invite.paywallPlans")}
          </Link>
          <Btn variant="text" onClick={() => setPaywall(false)}>
            {t("invite.keepOne")}
          </Btn>
          {owner && (
            <Btn variant="text" busy={busy === "ro"} onClick={() => void viewLink()}>
              {t("invite.readOnly")}
            </Btn>
          )}
        </div>
      )}
      {readOnly && (
        <p role="status" className="trips__note">
          {t("invite.readOnlyReady")}
        </p>
      )}
      {msg && (
        <p role={isErr ? "alert" : "status"} className={isErr ? "h-input__error trips__note" : "trips__note"}>
          {isErr && <Icon name="circle-alert" size={16} />}
          {text[msg]}
        </p>
      )}
      {owner && open.length > 0 && (
        <>
          <h3 className="h-label">{t("invite.pending")}</h3>
          <ul className="edit__dests">
            {open.map((i) => {
              const who = i.email ?? t("invite.pendingLink")
              return (
                <li key={i.id} className="h-listcard__row">
                  <span className="h-listcard__text">{t("invite.pendingRow", { who, role: t(`group.role.${i.role}`).toLowerCase(), date: day(i.expires_at) })}</span>
                  <Btn variant="text" mod={["sm"]} disabled={off} aria-label={t(i.email ? "invite.resendAria" : "invite.regenerateAria", { who })} onClick={() => void send(i.id, i.email ?? undefined, i.id, i.role)}>
                    {t(i.email ? "invite.resend" : "invite.regenerate")}
                  </Btn>
                  <Btn variant="text" mod={["sm"]} disabled={off} aria-label={t("invite.revokeAria", { who })} onClick={() => void revoke(i.id)}>
                    {t("invite.revoke")}
                  </Btn>
                </li>
              )
            })}
          </ul>
        </>
      )}
    </section>
  )
}
