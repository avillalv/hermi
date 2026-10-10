import { useId, useState } from "react"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { Icon } from "../kit"
import { setAiConsent, useAiConsent } from "./api"
import { setTripAi } from "./tripAi"
import "./ai.css"

type Props = { checked: boolean; label: string; help: string; error: string; disabled?: boolean; onChange: (next: boolean) => Promise<boolean> }

function Switch({ checked, label, help, error, disabled, onChange }: Props) {
  const id = useId()
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const flip = async (next: boolean) => {
    setBusy(true)
    setFailed(false)
    const ok = await onChange(next)
    setBusy(false)
    setFailed(!ok)
  }
  return (
    <div className="ai-switch">
      <div className="ai-switch__row">
        <label htmlFor={id}>
          <span className="ai-switch__label">{label}</span>
          <span className="h-soft ai-switch__help">{help}</span>
        </label>
        <input id={id} type="checkbox" role="switch" checked={checked} disabled={disabled || busy} onChange={(e) => void flip(e.target.checked)} />
      </div>
      {failed && (
        <p role="alert" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {error}
        </p>
      )}
    </div>
  )
}

/** Account, Privacy (05 6.15): the AI off toggle. Off withdraws `ai_processing` consent, which disables AI only. */
export function AiConsentSwitch() {
  const online = useOnline()
  const { granted, isPending } = useAiConsent(true)
  if (isPending) return null
  return <Switch checked={granted === true} label={t("ai.accountSwitch")} help={t("ai.accountHelp")} error={t("ai.consentError")} disabled={!online} onChange={setAiConsent} />
}

/** The owner's per-trip switch (`trips.ai_enabled`). Off blocks AI for everyone on this trip. */
export function TripAiSwitch({ tripId, version, enabled }: { tripId: string; version?: number; enabled: boolean }) {
  const online = useOnline()
  return <Switch checked={enabled} label={t("ai.tripSwitch")} help={t("ai.tripSwitchHelp")} error={t("ai.tripError")} disabled={!online} onChange={(next) => setTripAi(tripId, version, next)} />
}
