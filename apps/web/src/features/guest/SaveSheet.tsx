import { useState } from "react"
import { useNavigate } from "react-router"
import { Btn, Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { authStore } from "../../routes/auth/authStore"
import { identity, type IdentityAdapter } from "../../routes/auth/identity"
import { Modal } from "../../routes/itinerary/Modal"
import { clearHint, closeSavePrompt, dismissSavePrompt, showSavePrompt, useSavePrompt } from "./prompts"
import "./guest.css"

/**
 * The "Save your trip" bottom sheet (05 6.2) in the shared modal (4.19 focus rules). Apple and Google sign in here; email
 * goes to the sign-in screen for its code steps. `GuestClaimHost` claims the trip once a session exists.
 */
export function SaveSheet({ adapter = identity }: { adapter?: IdentityAdapter }) {
  const online = useOnline()
  const nav = useNavigate()
  const [busy, setBusy] = useState<"apple" | "google" | null>(null)
  const [error, setError] = useState<string | null>(null)

  const oauth = async (provider: "apple" | "google") => {
    setBusy(provider)
    setError(null)
    try {
      authStore.signIn(await adapter.oauth(provider))
      closeSavePrompt()
    } catch {
      setError(t("auth.errors.generic"))
    } finally {
      setBusy(null)
    }
  }
  const off = !online || busy !== null
  return (
    <Modal title={t("guest.saveTitle")} onClose={dismissSavePrompt}>
      <p className="h-soft">{t("guest.saveBody")}</p>
      {!online && (
        <p role="status" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {t("guest.offline")}
        </p>
      )}
      {error && (
        <p role="alert" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {error}
        </p>
      )}
      <div className="h-stack h-stack--roomy">
        <Btn variant="primary" mod={["apple"]} busy={busy === "apple"} disabled={off && busy !== "apple"} onClick={() => void oauth("apple")}>
          {t("auth.apple")}
        </Btn>
        <Btn variant="secondary" busy={busy === "google"} disabled={off && busy !== "google"} onClick={() => void oauth("google")}>
          {t("auth.google")}
        </Btn>
        <Btn
          variant="secondary"
          disabled={off}
          onClick={() => {
            closeSavePrompt()
            nav("/sign-in")
          }}
        >
          {t("auth.email")}
        </Btn>
        <Btn variant="text" onClick={dismissSavePrompt}>
          {t("guest.notNow")}
        </Btn>
      </div>
    </Modal>
  )
}

/** Mounted once in the App: the sheet when a trigger opened it, or the quiet line after a muted trigger was tapped. */
export function SaveSheetHost() {
  const { open, hint } = useSavePrompt()
  if (open) return <SaveSheet />
  if (!hint) return null
  return (
    <div className="guest-hint" role="status">
      <p className="guest-hint__text">{t("guest.hint")}</p>
      <Btn
        variant="text"
        onClick={() => {
          clearHint()
          showSavePrompt("banner")
        }}
      >
        {t("guest.save")}
      </Btn>
    </div>
  )
}
