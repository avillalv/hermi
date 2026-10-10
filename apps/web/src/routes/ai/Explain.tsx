import { useState } from "react"
import { useSearchParams } from "react-router"
import { AiFeedback, AiLabel, FailNotice, ReceiptLine, Waiting, explain, useAiRun } from "../../components/ai"
import { Btn, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { ActionFrame, type Frame } from "./ActionFrame"
import { duration } from "./duration"

const MAX = 300

/** 05 6.15 Explain (F-AI-1): a question about the trip, or about one item, stay or place named in the address. */
export function Explain() {
  return (
    <ActionFrame action="explain" title={t("ai.sheet.explain")}>
      {(f) => <Ask {...f} />}
    </ActionFrame>
  )
}

function Ask({ tripId, price, chip, canRun, start }: Frame) {
  const [q] = useSearchParams()
  const [question, setQuestion] = useState("")
  const ctx = { item_id: q.get("item") ?? undefined, lodging_id: q.get("lodging") ?? undefined, place_id: q.get("place") ?? undefined }
  const context = Object.values(ctx).some(Boolean) ? ctx : undefined
  const ask = question.trim()
  const { state, run, reset } = useAiRun((key) => explain(tripId, { question: ask, ...(context ? { context } : {}) }, key))
  const go = () =>
    start(async () => {
      track("ai_action_started", { action: "explain", feature: "explain", credits: price, from_cache: false })
      const t0 = Date.now()
      const r = await run()
      if (r) track("ai_action_completed", { action: "explain", feature: "explain", outcome: r.ok ? "ok" : "failed", duration_seconds_bucket: duration(Date.now() - t0) })
    })
  const running = state.phase === "running"
  const done = state.phase === "done" ? state.data : null
  return (
    <>
      <p className="h-soft">{t("ai.sheet.explainDesc")}</p>
      <form
        className="ai-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (canRun && ask && !running) go()
        }}
      >
        <TextField
          label={t("ai.act.question")}
          helper={t("ai.act.questionHelp")}
          value={question}
          maxLength={MAX}
          disabled={running}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <Btn variant="primary" mod={["spend"]} type="submit" busy={running} disabled={!canRun || !ask} aria-label={t("ai.act.askAria", { credits: price })}>
          {t("ai.act.ask")}
          {chip}
        </Btn>
      </form>
      {running && <Waiting label={t("ai.act.thinking")} />}
      {state.phase === "failed" && <FailNotice fail={state.fail} onRetry={go} onAllow={() => start(go)} />}
      {done && (
        <section className="ai-result" aria-label={t("ai.act.answer")}>
          <p className="ai-answer">{done.answer}</p>
          {done.needs_source_check && <p className="h-soft">{t("ai.act.checkSource")}</p>}
          {done.sources.length > 0 && (
            <ul className="ai-sources">
              {done.sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} target="_blank" rel="noreferrer noopener">
                    {s.title || s.url}
                  </a>
                </li>
              ))}
            </ul>
          )}
          <AiLabel />
          <ReceiptLine receipt={done.credits} />
          <AiFeedback target={{ runId: done.run_id }} action="explain" />
          <Btn variant="secondary" onClick={reset}>
            {t("ai.act.askAnother")}
          </Btn>
        </section>
      )}
    </>
  )
}
