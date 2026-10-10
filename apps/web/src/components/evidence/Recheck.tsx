import { useRef, useState } from "react"
import { Modal } from "../../routes/itinerary/Modal"
import { createNote } from "../../routes/notes/api"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { Btn, Icon } from "../kit"
import { recheck, type RecheckResult } from "./api"

type Props = {
  kind: "note" | "item"
  id: string
  tripId: string
  /** Names the button for VoiceOver: "Recheck: Tram 28 is often crowded". */
  subject: string
  /** Editors and owners only; a viewer sees the chip and no button (05 6.39). */
  canRecheck: boolean
  /** AI off for the trip hides the button. */
  aiOn?: boolean
}

/**
 * 05 6.39: "Recheck" with a 1 credit chip, then a small sheet with what the page says now. A recheck never edits the
 * saved text: `changed` offers "Save as a note" with the new value and its source. Fares are not rechecked here.
 */
export function Recheck({ kind, id, tripId, subject, canRecheck, aiOn = true }: Props) {
  const online = useOnline()
  const key = useRef<string | null>(null) // one Idempotency-Key per tap, kept until a result arrives
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState<RecheckResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<"idle" | "saving" | "done" | "failed">("idle")
  if (!canRecheck || !aiOn) return null

  const go = async () => {
    if (busy) return
    key.current ??= crypto.randomUUID()
    setBusy(true)
    setError(null)
    const r = await recheck(kind, id, tripId, key.current)
    setBusy(false)
    if (!r.ok) {
      if (r.reason !== "failed") key.current = null // a refusal is final; only a failed call keeps its key for a retry
      // shortcut: the 0 credit state shows inline text until the `out_of_credits_verify` paywall exists (WF-132)
      return setError(t(r.reason === "credits" ? "recheck.credits" : "recheck.failed"))
    }
    key.current = null
    setSaved("idle")
    setRes(r.data)
  }
  const save = async () => {
    if (!res?.current_value) return
    setSaved("saving")
    const r = await createNote(tripId, { body: res.current_value, source_url: res.source.url })
    setSaved(r.ok ? "done" : "failed")
  }
  const site = res?.source.site ?? res?.source.url ?? ""
  return (
    <>
      <Btn variant="secondary" mod={["sm"]} busy={busy} disabled={!online} aria-label={t("recheck.buttonAria", { subject })} onClick={() => void go()}>
        {busy ? t("recheck.checking") : t("recheck.button")}
        <span className="h-credit">
          <Icon name="coins" size={14} />
          <span className="h-credit__n">1</span> {t("recheck.credit")}
        </span>
      </Btn>
      {!online && <span role="status" className="source-chip__text">{t("recheck.offline")}</span>}
      {error && <span role="alert" className="source-chip__text">{error}</span>}
      {res && (
        <Modal title={t("recheck.title")} onClose={() => setRes(null)}>
          <div className="plan__form" role="status">
            {res.result === "confirmed" && <p>{t("recheck.same")}</p>}
            {res.result === "changed" && (
              <>
                <p>{t("recheck.changed", { value: res.current_value ?? "" })}</p>
                <p className="h-soft">{t("recheck.changedFrom", { site })}</p>
                <p className="h-soft">{t("recheck.keepsOld")}</p>
              </>
            )}
            {res.result === "not_shown" && <p>{t("recheck.gone")}</p>}
            {res.result === "unreachable" && <p>{t("recheck.unreachable")}</p>}
            {saved === "done" && <p>{t("recheck.saved")}</p>}
            {saved === "failed" && <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{t("recheck.saveFailed")}</p>}
          </div>
          <div className="plan__form">
            {res.result === "changed" && saved !== "done" && (
              <Btn variant="primary" busy={saved === "saving"} onClick={() => void save()}>{t("recheck.saveNote")}</Btn>
            )}
            <Btn variant="secondary" onClick={() => setRes(null)}>{t("recheck.close")}</Btn>
          </div>
        </Modal>
      )}
    </>
  )
}
