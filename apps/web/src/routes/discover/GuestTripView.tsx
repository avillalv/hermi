import { Link } from "react-router"
import { t } from "../../lib/i18n"
import { AppShell } from "../../shell/AppShell"
import { readGuestTrip } from "./guestTrip"
import { SampleBody } from "./SampleBody"
import "./discover.css"

/** The local guest trip (05 6.2): read from this device, never from the server. */
export function GuestTripView() {
  const trip = readGuestTrip()
  return (
    <AppShell active="trips">
      {trip ? (
        <>
          <p role="note" className="discover__banner">
            {t("discover.guestTitle")}
          </p>
          <h1 className="h-pagehead__title">{trip.sample.title}</h1>
          <SampleBody sample={trip.sample} />
        </>
      ) : (
        <>
          <h1 className="h-pagehead__title">{t("trips.title")}</h1>
          <p className="h-soft">{t("discover.guestGone")}</p>
          <Link to="/discover" className="h-btn h-btn--secondary">
            {t("discover.title")}
          </Link>
        </>
      )}
    </AppShell>
  )
}
