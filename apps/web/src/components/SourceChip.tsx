import { useEffect } from "react"
import { t } from "../lib/i18n"
import { track } from "../lib/track"
import { Icon } from "./kit"
import "./source-chip.css"

const STALE_DAYS = 14 // 05 6.18 and 04 5.14: a finding checked more than 14 days ago is stale
const DAY_MS = 86_400_000
const web = (url: string) => /^https?:\/\//i.test(url) // only web links become anchors; javascript: and data: stay plain text
const shortDate = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" })
const host = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return url
  }
}
const bucket = (days: number) => (days <= 30 ? "15_to_30" : "over_30")

/**
 * 05 6.18 evidence label: "Found on [site], checked [date]", linked to the source. A source older than 14 days
 * (or flagged stale by the API) also shows an amber "Seen 12 Aug. May be out of date." chip. Nothing is hidden.
 */
/** `agent` is true for AI findings: only they go stale, a person's own note never shows the chip. */
export function SourceChip({ url, site, checkedAt, stale, agent = true, onOpen }: { url: string; site?: string | null; checkedAt?: string | null; stale?: boolean; agent?: boolean; onOpen?: () => void }) {
  const name = site || host(url)
  const age = checkedAt ? (Date.now() - new Date(checkedAt).getTime()) / DAY_MS : 0
  const old = agent && (!!stale || age > STALE_DAYS)
  useEffect(() => {
    // keyed on `old` only: the age keeps growing between renders and could cross a bucket edge, which must not refire
    if (old) track("evidence_stale_shown", { age_bucket: bucket(age) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [old])
  const label = checkedAt ? t("source.found", { site: name, date: shortDate(checkedAt) }) : t("source.foundNoDate", { site: name })
  return (
    <span className="source-chip">
      {web(url) ? (
        <a className="source-chip__link" href={url} target="_blank" rel="noopener noreferrer" aria-label={`${label}. ${t("source.open", { site: name })}`} onClick={onOpen}>
          {label}
          <Icon name="external-link" size={14} />
        </a>
      ) : (
        <span className="source-chip__text">{label}</span>
      )}
      {old && checkedAt && (
        <span className="source-chip__stale">
          <Icon name="circle-alert" size={14} />
          {t("source.stale", { date: shortDate(checkedAt) })}
        </span>
      )}
    </span>
  )
}
