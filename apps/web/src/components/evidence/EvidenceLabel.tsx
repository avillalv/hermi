import { useState } from "react"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { sendReport } from "../ai/api"
import { SourceChip } from "../SourceChip"
import "../source-chip.css"

/** Where the fact came from: an AI fare, a note or research item, or text the person pasted for an import. */
export type EvidenceKind = "fare" | "note" | "research" | "import"
const DAY_MS = 86_400_000

type Props = {
  kind: EvidenceKind
  url?: string | null
  site?: string | null
  checkedAt?: string | null
  stale?: boolean
  /** The run that found a fare. With it, an agent fare offers "Price was different". */
  runId?: string
  /** Name the fare in the report: its id and price, so the eval set can find it. */
  fareId?: string
  priceMinor?: number
  currency?: string
  onOpen?: () => void
}

/**
 * 05 6.18 and 04 5.14, WF-055: the one label every AI-found fact wears. "Found on [site], checked [date]" linked to the
 * page (SourceChip), the age for a fare, "From your pasted text" for an import, and "Price was different" on an agent
 * fare, which files a wrong_info report on the run (the eval set reads those). A fact with no source never renders blank.
 */
export function EvidenceLabel({ kind, url, site, checkedAt, stale, runId, fareId, priceMinor, currency, onOpen }: Props) {
  const [phase, setPhase] = useState<"idle" | "sending" | "sent" | "error">("idle")
  if (kind === "import") {
    return (
      <span className="evidence-label">
        <span className="source-chip__text">{t("source.pasted")}</span>
      </span>
    )
  }
  if (!url) {
    return (
      <span className="evidence-label">
        <span className="source-chip__text">{t("source.missing")}</span>
      </span>
    )
  }
  const days = checkedAt ? Math.max(0, Math.floor((Date.now() - new Date(checkedAt).getTime()) / DAY_MS)) : null
  const age = days === null ? null : days === 0 ? t("source.ageToday") : days === 1 ? t("source.ageOne") : t("source.ageN", { n: days })
  const report = async () => {
    if (!runId) return
    setPhase("sending")
    const detail = `Price was different: fare ${fareId ?? "unknown"}, ${url.slice(0, 500)}, ${priceMinor ?? "unknown"} ${currency ?? ""}`.trim()
    const r = await sendReport({ runId }, "wrong_info", detail)
    if (r === "ok") track("content_reported", { surface: "ai_answer", reason: "wrong_info" }) // only a new report (201)
    setPhase(r === "ok" || r === "repeat" || r === "gone" ? "sent" : "error")
  }
  return (
    <span className="evidence-label">
      <SourceChip url={url} site={site} checkedAt={checkedAt} stale={stale} agent={kind !== "fare"} onOpen={onOpen} />
      {kind === "fare" && age && <span className="source-chip__text">{age}</span>}
      {kind === "fare" && runId && phase !== "sent" && (
        <button type="button" className="source-chip__btn" disabled={phase === "sending"} onClick={() => void report()}>
          {t("source.priceDifferent")}
        </button>
      )}
      {phase === "sent" && <span role="status" className="source-chip__text">{t("source.priceThanks")}</span>}
      {phase === "error" && <span role="alert" className="source-chip__text">{t("source.priceFailed")}</span>}
    </span>
  )
}
