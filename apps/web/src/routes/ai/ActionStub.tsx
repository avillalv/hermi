import { Link, useParams } from "react-router"
import { t } from "../../lib/i18n"
import { AppShell } from "../../shell/AppShell"

const TITLES: Record<string, string> = {
  explain: "ai.sheet.explain",
  packing: "ai.sheet.packing",
  day: "ai.sheet.day",
  trip: "ai.sheet.trip",
  research: "ai.sheet.research",
}

/** shortcut: the landing page of a sheet row whose result screen is not built yet. Ceiling: no action runs from here. Trigger: WF-132.2 and WF-132.3 replace it route by route. */
export function ActionStub() {
  const { id = "", action = "" } = useParams()
  const title = TITLES[action]
  return (
    <AppShell active="trips">
      <div className="overview">
        <h1 className="h-title">{title ? t(title) : t("ai.sheet.title")}</h1>
        <p className="h-soft">{t("ai.sheet.stubBody")}</p>
        <Link className="h-btn h-btn--secondary" to={`/trips/${encodeURIComponent(id)}`}>
          {t("ai.sheet.stubBack")}
        </Link>
      </div>
    </AppShell>
  )
}
