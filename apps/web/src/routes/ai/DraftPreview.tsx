import { useState } from "react"
import { Link } from "react-router"
import { AiFeedback, AiLabel, ReceiptLine, saveDraft, type DraftedDay, type DraftItem, type Receipt } from "../../components/ai"
import { Btn, Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { ICON, dayText } from "../itinerary/meta"

type Props = {
  tripId: string
  days: DraftedDay[]
  overview?: string
  runId: string
  receipt: Receipt
  action: "draft_day" | "draft_trip"
  onDiscard: () => void
}

const keyOf = (d: number, i: number) => `${d}:${i}`

/**
 * A draft is a preview (05 6.15 Drafts): nothing is in the plan until "Accept all" or the picked items are added. Each
 * item shows when to check hours (`verify`), because AI never states opening hours (06 section 5.4).
 */
export function DraftPreview({ tripId, days, overview, runId, receipt, action, onDiscard }: Props) {
  const online = useOnline()
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [phase, setPhase] = useState<"idle" | "saving" | "done" | "failed" | "forbidden">("idle")
  const [saved, setSaved] = useState(0)
  const all = days.flatMap((d, di) => d.items.map((it, ii) => ({ it, k: keyOf(di, ii) })))
  const toggle = (k: string) =>
    setPicked((s) => {
      const n = new Set(s)
      if (!n.delete(k)) n.add(k)
      return n
    })
  const save = async (items: DraftItem[]) => {
    if (!items.length || phase === "saving") return
    setPhase("saving")
    const r = await saveDraft(tripId, items)
    setSaved(r.saved)
    for (const it of items.slice(0, r.saved)) track("itinerary_item_added", { category: it.category, source: "ai_draft" })
    setPhase(r.result === "ok" ? "done" : r.result === "forbidden" ? "forbidden" : "failed")
  }
  if (phase === "done")
    return (
      <section className="ai-result" aria-label={t("ai.act.draft")}>
        <p role="status" className="ai-answer">{t(saved === 1 ? "ai.act.addedOne" : "ai.act.added", { count: saved })}</p>
        <div className="ai-actions">
          <Link className="h-btn h-btn--primary" to={`/trips/${encodeURIComponent(tripId)}/plan`}>
            {t("ai.act.openPlan")}
          </Link>
          <Btn variant="secondary" onClick={onDiscard}>
            {t("ai.act.again")}
          </Btn>
        </div>
      </section>
    )
  const busy = phase === "saving"
  const pickedItems = all.filter((x) => picked.has(x.k)).map((x) => x.it)
  return (
    <section className="ai-result" aria-label={t("ai.act.draft")}>
      <AiLabel />
      {overview && <p className="ai-answer">{overview}</p>}
      <p className="h-soft">{t("ai.act.previewNote")}</p>
      {all.length === 0 && <p className="h-soft">{t("ai.act.draftEmpty")}</p>}
      {days.map((d, di) => (
        <fieldset key={d.day} className="ai-day">
          <legend className="h-label">
            {dayText(d.day)}
            {d.title ? `: ${d.title}` : ""}
          </legend>
          {d.rationale && <p className="h-soft">{d.rationale}</p>}
          {d.items.map((it, ii) => {
            const k = keyOf(di, ii)
            return (
              <label key={k} className="ai-item">
                <input type="checkbox" checked={picked.has(k)} disabled={busy} onChange={() => toggle(k)} />
                <Icon name={ICON[it.category]} size={18} />
                <span className="ai-item__text">
                  <span className="ai-item__title">{it.title}</span>
                  <span className="h-soft">
                    {it.start_time ? `${it.start_time}${it.end_time ? ` to ${it.end_time}` : ""}` : t("ai.act.anyTime")}
                    {it.location_name ? `, ${it.location_name}` : ""}
                  </span>
                  {it.notes && <span className="h-soft">{it.notes}</span>}
                  {it.verify && <span className="ai-item__verify">{t("ai.act.verify")}</span>}
                </span>
              </label>
            )
          })}
        </fieldset>
      ))}
      {phase === "failed" && (
        <p role="alert" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {saved > 0 ? t("ai.act.savePartial", { count: saved }) : t("ai.act.saveFailed")}
        </p>
      )}
      {phase === "forbidden" && <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{t("ai.act.forbidden")}</p>}
      {!online && <p role="status" className="h-soft">{t("ai.act.saveOffline")}</p>}
      <div className="ai-actions">
        <Btn variant="primary" busy={busy} disabled={!online || all.length === 0} onClick={() => void save(all.map((x) => x.it))}>
          {t("ai.act.acceptAll")}
        </Btn>
        <Btn variant="secondary" disabled={!online || busy || pickedItems.length === 0} onClick={() => void save(pickedItems)}>
          {t("ai.act.addPicked", { count: pickedItems.length })}
        </Btn>
        <Btn variant="text" disabled={busy} onClick={onDiscard}>
          {t("ai.act.discard")}
        </Btn>
      </div>
      <ReceiptLine receipt={receipt} />
      <AiFeedback target={{ runId }} action={action} />
    </section>
  )
}
