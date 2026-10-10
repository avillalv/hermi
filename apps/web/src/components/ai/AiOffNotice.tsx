import { useState } from "react"
import { t } from "../../lib/i18n"
import { Btn, Icon } from "../kit"
import { setTripAi } from "./tripAi"
import "./ai.css"

/**
 * "AI is off for this trip" (05 6.15). The owner gets a button to turn it back on; everyone else is told whom to ask.
 * `version` is the trip's version for the PATCH.
 */
export function AiOffNotice({ tripId, version, isOwner, ownerName }: { tripId: string; version?: number; isOwner: boolean; ownerName?: string | null }) {
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const turnOn = async () => {
    setBusy(true)
    setFailed(false)
    const ok = await setTripAi(tripId, version, true)
    setBusy(false)
    setFailed(!ok)
  }
  return (
    <div className="ai-off" role="status">
      <p className="ai-off__line">
        <Icon name="lock" size={16} />
        <strong>{t("ai.tripOff")}</strong>
      </p>
      {isOwner ? (
        <Btn variant="secondary" busy={busy} onClick={() => void turnOn()}>
          {t("ai.tripOn")}
        </Btn>
      ) : (
        <p className="h-soft">{ownerName ? t("ai.tripOffName", { name: ownerName }) : t("ai.tripOffAsk")}</p>
      )}
      {failed && (
        <p role="alert" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {t("ai.tripError")}
        </p>
      )}
    </div>
  )
}
