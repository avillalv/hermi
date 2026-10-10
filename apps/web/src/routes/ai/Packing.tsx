import { useState } from "react"
import { AiFeedback, AiLabel, FailNotice, ReceiptLine, Waiting, packingList, useAiRun, type PackItem } from "../../components/ai"
import { Btn, Icon, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { ActionFrame, type Frame } from "./ActionFrame"
import { duration } from "./duration"

const GROUPS = ["clothing", "toiletries", "documents", "electronics", "health", "other"]

/**
 * 05 6.15 packing list: lines grouped as the API returns them, ticked off here, and copied out.
 * shortcut: nothing is saved to the trip checklist, because POST /trips/{id}/checklist/packing (04 5.16) is not built.
 * Ceiling: ticks are lost on leaving. Trigger: the checklist ticket adds "Add to checklist" here with the kept lines.
 */
export function Packing() {
  return (
    <ActionFrame action="explain" title={t("ai.sheet.packing")}>
      {(f) => <Generate {...f} />}
    </ActionFrame>
  )
}

function Generate({ tripId, price, chip, canRun, start }: Frame) {
  const [prefs, setPrefs] = useState("")
  const [ticked, setTicked] = useState<Set<number>>(new Set())
  const [copied, setCopied] = useState<"idle" | "done" | "failed">("idle")
  const note = prefs.trim()
  const { state, run, reset } = useAiRun((key) => packingList(tripId, note ? { preferences: note } : {}, key))
  const go = () =>
    start(async () => {
      track("ai_action_started", { action: "explain", feature: "packing_list", credits: price, from_cache: false })
      const t0 = Date.now()
      setTicked(new Set())
      const r = await run()
      if (r) track("ai_action_completed", { action: "explain", feature: "packing_list", outcome: r.ok ? "ok" : "failed", duration_seconds_bucket: duration(Date.now() - t0) })
    })
  const running = state.phase === "running"
  const done = state.phase === "done" ? state.data : null
  const toggle = (i: number) =>
    setTicked((s) => {
      const n = new Set(s)
      if (!n.delete(i)) n.add(i)
      return n
    })
  const copy = async (items: PackItem[]) => {
    try {
      await navigator.clipboard.writeText(items.map((i) => `- ${i.label}${i.qty && i.qty > 1 ? ` x${i.qty}` : ""}`).join("\n"))
      setCopied("done")
    } catch {
      setCopied("failed")
    }
  }
  return (
    <>
      <p className="h-soft">{t("ai.sheet.packingDesc")}</p>
      <form
        className="ai-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (canRun && !running) go()
        }}
      >
        <TextField label={t("ai.act.prefs")} helper={t("ai.act.prefsHelp")} value={prefs} maxLength={300} disabled={running} onChange={(e) => setPrefs(e.target.value)} />
        <Btn variant="primary" mod={["spend"]} type="submit" busy={running} disabled={!canRun} aria-label={t("ai.act.packAria", { credits: price })}>
          {t("ai.act.pack")}
          {chip}
        </Btn>
      </form>
      {running && <Waiting label={t("ai.act.packing")} />}
      {state.phase === "failed" && <FailNotice fail={state.fail} onRetry={go} onAllow={() => start(go)} />}
      {done && done.items.length === 0 && <p className="h-soft">{t("ai.act.packEmpty")}</p>}
      {done && done.items.length > 0 && (
        <section className="ai-result" aria-label={t("ai.sheet.packing")}>
          {GROUPS.map((g) => {
            const rows = done.items.map((it, i) => ({ it, i })).filter((r) => r.it.group === g)
            if (!rows.length) return null
            return (
              <fieldset key={g} className="ai-pack">
                <legend className="h-label">{t(`ai.act.group.${g}`)}</legend>
                {rows.map(({ it, i }) => (
                  <label key={i} className="ai-pack__row">
                    <input type="checkbox" checked={ticked.has(i)} onChange={() => toggle(i)} />
                    <span>
                      {it.label}
                      {it.qty && it.qty > 1 ? ` x${it.qty}` : ""}
                      {it.reason && <span className="h-soft ai-pack__why"> {it.reason}</span>}
                    </span>
                  </label>
                ))}
              </fieldset>
            )
          })}
          <AiLabel />
          <ReceiptLine receipt={done.credits} />
          <div className="ai-actions">
            <Btn variant="secondary" onClick={() => void copy(done.items)}>
              <Icon name="check" size={16} />
              {t("ai.act.copyList")}
            </Btn>
            <Btn variant="secondary" onClick={reset}>
              {t("ai.act.again")}
            </Btn>
          </div>
          {copied === "done" && <p role="status" className="h-soft">{t("ai.act.copied")}</p>}
          {copied === "failed" && <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{t("ai.act.copyFailed")}</p>}
          <AiFeedback target={{ runId: done.run_id }} action="explain" />
        </section>
      )}
    </>
  )
}
