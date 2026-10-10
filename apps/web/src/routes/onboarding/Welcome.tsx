import { Link, Navigate } from "react-router"
import { pendingInvite } from "../invite/collab"
import { Sprite, TicketStub, TripTicket } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useAuth } from "../auth/authStore"
import { WelcomeMap } from "./WelcomeMap"
import "./onboarding.css"

/**
 * 05 6.1, ported from design/screens/01-welcome.html: the map, then a floating boarding pass holding the lockup, the
 * headline and the two buttons. "Plan a trip" opens the local guest trip (05 6.2). The swipeable value cards are left
 * for a later slice.
 */
export function Welcome() {
  const { token } = useAuth()
  if (token) return <Navigate to={pendingInvite.target()} replace />
  return (
    <main className="h-screen">
      <Sprite />
      <WelcomeMap />
      <TripTicket mod={["sky", "cta", "lg", "float"]}>
        <div className="h-ticket__head h-ticket__head--sky h-ticket__head--center">
          <svg className="h-mark" width="56" height="56" aria-hidden="true" focusable="false">
            <use href="#hermi-mark" />
          </svg>
          <span className="h-lockup__name">Hermi</span>
        </div>
        <div className="h-ticket__body h-ticket__body--roomy">
          <h1 className="h-display">
            <span className="h-display__line">{t("welcome.line1")}</span>
            <span className="h-display__line">{t("welcome.line2")}</span>
          </h1>
          <p className="h-lead">{t("welcome.body")}</p>
        </div>
        <TicketStub>
          <Link to="/guest-trip" className="h-btn h-btn--primary">
            {t("welcome.plan")}
          </Link>
          <Link to="/sign-in" className="h-btn h-btn--secondary">
            {t("welcome.signIn")}
          </Link>
          <p className="h-fine">
            {t("welcome.legalPre")}
            <a className="h-link" href="https://hermi.world/terms">
              {t("welcome.terms")}
            </a>
            {t("welcome.legalMid")}
            <a className="h-link" href="https://hermi.world/privacy">
              {t("welcome.privacy")}
            </a>
            {t("welcome.legalEnd")}
          </p>
        </TicketStub>
      </TripTicket>
    </main>
  )
}
