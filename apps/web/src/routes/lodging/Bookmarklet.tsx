import { useEffect, useRef } from "react"
import { t } from "../../lib/i18n"

/**
 * The bookmarklet (05 6.11): runs in the person's own browser on the stay page they have open and opens the Hermi paste helper
 * with that page's address and title in the query. Nothing is fetched by Hermi; the sheet then waits for the person to confirm.
 */
export function bookmarkletHref(origin: string, tripId: string): string {
  const base = `${origin}/trips/${encodeURIComponent(tripId)}/stays?add=1&via=bookmarklet`
  const code = `window.open(${JSON.stringify(base)}+'&url='+encodeURIComponent(location.href)+'&title='+encodeURIComponent(document.title),'_blank','noopener')`
  return `javascript:${encodeURIComponent(code)}`
}

/** A draggable link. React refuses `javascript:` in an href prop, so the real href is set on the node after render. A click inside Hermi only opens this helper again. */
export function Bookmarklet({ tripId }: { tripId: string }) {
  const link = useRef<HTMLAnchorElement>(null)
  useEffect(() => link.current?.setAttribute("href", bookmarkletHref(window.location.origin, tripId)), [tripId])
  return (
    <section className="h-listcard stays__bookmarklet" aria-labelledby="stays-bm">
      <h2 className="h-title" id="stays-bm">{t("stays.bookmarkletTitle")}</h2>
      <p className="h-soft">{t("stays.bookmarkletHelp")}</p>
      <a ref={link} href={`/trips/${encodeURIComponent(tripId)}/stays`} className="h-btn h-btn--secondary h-btn--sm" draggable="true">
        {t("stays.bookmarkletLink")}
      </a>
    </section>
  )
}
