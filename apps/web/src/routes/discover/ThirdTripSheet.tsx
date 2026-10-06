import { useEffect } from "react"
import { Link } from "react-router"
import { Btn } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { Modal } from "../itinerary/Modal"
import "../itinerary/plan.css"

/**
 * The `third_trip` paywall (05 6.27) in the shared modal (focus moves in, Tab stays, Escape closes, focus returns). It names the
 * limit and what more gives, with the free path "Archive a trip" first. shortcut: WF-066 builds the full 4.14 sheet; left out
 * until then are the sky head, the Plus annual offer and the "Upgrade in the iOS app" button.
 */
export function ThirdTripSheet({ onClose }: { onClose: () => void }) {
  useEffect(() => void track("paywall_viewed", { placement: "third_trip", offer_shown: [] }), [])
  const dismiss = () => {
    track("paywall_dismissed", { placement: "third_trip" })
    onClose()
  }
  return (
    <Modal title={t("discover.paywallTitle")} onClose={dismiss}>
      <p className="h-soft">{t("discover.paywallBody")}</p>
      <div className="h-stack h-stack--roomy">
        <Link to="/" className="h-btn h-btn--primary">
          {t("discover.paywallArchive")}
        </Link>
        <Btn variant="text" onClick={dismiss}>
          {t("discover.paywallClose")}
        </Btn>
      </div>
    </Modal>
  )
}
