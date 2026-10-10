import { useEffect, useRef, useState, type ReactElement } from "react"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { Modal } from "../../routes/itinerary/Modal"
import { Btn, Icon } from "../kit"
import { AI_CONSENT_VERSION, setAiConsent } from "./api"
import "./ai.css"

/**
 * 05 6.15 first use: the AI consent sheet. Allow stores a `consents` row with the text version; Not now closes it and
 * the app stays fully usable, only the AI action waits. Fires ai_consent_shown, ai_consent_granted, ai_consent_declined.
 */
export function AiConsentGate({ onAllowed, onDeclined }: { onAllowed: () => void; onDeclined: () => void }) {
  const online = useOnline()
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    track("ai_consent_shown")
  }, [])
  const allow = async () => {
    setBusy(true)
    setFailed(false)
    const ok = await setAiConsent(true)
    setBusy(false)
    if (!ok) return setFailed(true)
    track("ai_consent_granted", { version: AI_CONSENT_VERSION })
    onAllowed()
  }
  const decline = () => {
    track("ai_consent_declined")
    onDeclined()
  }
  return (
    <Modal title={t("ai.consentTitle")} onClose={decline}>
      <div className="ai-consent">
        <p className="ai-consent__lead">{t("ai.consentLead")}</p>
        <p className="h-soft">{t("ai.consentBody")}</p>
        <p className="h-soft">{t("ai.consentFree")}</p>
        {!online && (
          <p role="status" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("ai.offline")}
          </p>
        )}
        {failed && (
          <p role="alert" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("ai.consentError")}
          </p>
        )}
        <div className="ai-actions">
          <Btn variant="primary" busy={busy} disabled={!online} onClick={() => void allow()}>
            {t("ai.allow")}
          </Btn>
          <Btn variant="secondary" disabled={busy} onClick={decline}>
            {t("ai.notNow")}
          </Btn>
        </div>
      </div>
    </Modal>
  )
}

/**
 * The shared entry-point hook. `request(resume)` opens the gate; Allow runs `resume` (the action the person was after),
 * Not now just closes it. Render `element` once in the screen. An entry point calls `request` when it knows consent is
 * missing (`useAiConsent().granted === false`) or when the API answers 403 `ai_consent_required`.
 */
export function useAiConsentGate(): { request: (resume?: () => void) => void; element: ReactElement | null } {
  const [open, setOpen] = useState(false)
  const resume = useRef<(() => void) | undefined>(undefined)
  const request = (fn?: () => void) => {
    resume.current = fn
    setOpen(true)
  }
  const element = open ? (
    <AiConsentGate
      onAllowed={() => {
        setOpen(false)
        const fn = resume.current
        resume.current = undefined
        fn?.()
      }}
      onDeclined={() => {
        setOpen(false)
        resume.current = undefined
      }}
    />
  ) : null
  return { request, element }
}
