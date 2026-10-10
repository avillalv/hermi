import { Btn } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useAuth } from "../../routes/auth/authStore"
import { setKeptSeparate, useGuest } from "./store"
import { showSavePrompt } from "./prompts"
import "./guest.css"

/** The slim banner under the header, only for a signed-out visitor with a guest trip (05 6.2). It is never a paywall and is not muted. */
export function GuestBanner() {
  const { token } = useAuth()
  const guest = useGuest()
  // Signed in, the banner shows only for a trip kept apart: Save then claims it into the account.
  if (!guest || (token && !guest.kept_separate)) return null
  return (
    <div className="guest-banner" role="region" aria-label={t("guest.bannerLabel")}>
      <p className="guest-banner__text">{t(token ? "guest.keptBanner" : "guest.banner")}</p>
      <Btn
        variant="text"
        onClick={() => {
          setKeptSeparate(false) // signed in, the claim host sees this and claims; signed out, the Save sheet opens
          if (!token) showSavePrompt("banner")
        }}
      >
        {t("guest.save")}
      </Btn>
    </div>
  )
}
