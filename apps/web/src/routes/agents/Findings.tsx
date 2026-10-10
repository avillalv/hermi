import { Link } from "react-router"
import { EvidenceLabel } from "../../components/evidence"
import { Icon, TicketStub, TripTicket } from "../../components/kit"
import { t } from "../../lib/i18n"
import { formatMoney } from "../../lib/money"
import { track } from "../../lib/track"
import type { Finding } from "./derive"

const web = (url: string) => /^https?:\/\//i.test(url)

/**
 * 05 4.21 evidence row (design `.h-ticket--evidence`): what was found, the evidence label with its link, then a stub with
 * Open source, a link to where it was saved, and Dismiss. Accepted findings are already saved by the run, so there is
 * no "Save to trip" button; Dismiss only hides the row on this screen.
 */
export function EvidenceRow({ tripId, f, runId, onDismiss }: { tripId: string; f: Finding; runId?: string; onDismiss: () => void }) {
  const price = f.kind === "fare" && f.priceMinor !== undefined && f.currency ? formatMoney(f.priceMinor, f.currency) : null
  const title = [f.title, price].filter(Boolean).join(", ")
  const surface = f.kind
  const where = f.kind === "fare" ? `/trips/${encodeURIComponent(tripId)}/flights` : `/trips/${encodeURIComponent(tripId)}/notes`
  return (
    <TripTicket mod={["evidence"]} role="group" aria-label={`${t(f.kind === "fare" ? "agents.kindFareLabel" : "agents.kindNoteLabel")}: ${title}${f.site ? `, ${f.site}` : ""}`}>
      <div className="h-ticket__body">
        <div className="h-evidence__top">
          <h4 className="h-evidence__title">{title}</h4>
          <span className="h-label h-evidence__kind">{t(f.kind === "fare" ? "agents.kindFareLabel" : "agents.kindNoteLabel")}</span>
        </div>
        <EvidenceLabel kind={f.kind} url={f.url} site={f.site} checkedAt={f.checkedAt} runId={runId} onOpen={() => track("evidence_opened", { surface })} />
        {f.kind === "fare" && <span className="h-evidence__quote">{t("agents.fareSeen")}</span>}
      </div>
      <TicketStub>
        {web(f.url) && (
          <a
            className="h-ticket__action"
            href={f.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t("agents.openSourceLabel", { title, site: f.site })}
            onClick={() => track("evidence_opened", { surface })}
          >
            {t("agents.openSource")}
            <Icon name="external-link" size={14} />
          </a>
        )}
        <Link className="h-ticket__action h-ticket__action--brand" to={where}>
          {t(f.kind === "fare" ? "agents.savedSeeFlights" : "agents.savedSeeNotes")}
        </Link>
        <button type="button" className="h-ticket__action h-ticket__action--soft" aria-label={t("agents.dismissLabel", { title })} onClick={onDismiss}>
          {t("agents.dismiss")}
        </button>
      </TicketStub>
    </TripTicket>
  )
}
