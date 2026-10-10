import { useState } from "react"
import { Link } from "react-router"
import {
  AiFeedback,
  AiLabel,
  FailNotice,
  OutOfCreditsResearch,
  RESEARCH_TOPICS,
  ReceiptLine,
  Waiting,
  research,
  useAiRun,
  type ResearchTopic,
  type Researched,
} from "../../components/ai"
import { EvidenceLabel } from "../../components/evidence"
import { Btn, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { ActionFrame, type Frame } from "./ActionFrame"
import { duration } from "./duration"

const MAX = 300
const DAY_MS = 86_400_000

/** 05 6.15 Research a question (F-AI-3): a topic, or your own question, then sourced notes saved to the trip. */
export function Research() {
  return (
    <ActionFrame action="research" title={t("ai.sheet.research")}>
      {(f) => <Ask {...f} />}
    </ActionFrame>
  )
}

/** When a note's page was read: the run's own time, or for a shared hit, the age of the cached entry. */
function seenAt(r: Researched, url: string): string {
  const own = r.sources.find((s) => s.url === url)?.retrieved_at
  if (own) return own
  return r.from_cache && r.checked_days_ago !== null ? new Date(Date.now() - r.checked_days_ago * DAY_MS).toISOString() : new Date().toISOString()
}

function Ask({ tripId, credits, price, chip, canRun, start }: Frame) {
  const [topic, setTopic] = useState<ResearchTopic>("destination_brief")
  const [own, setOwn] = useState("")
  const question = own.trim()
  const { state, run, reset } = useAiRun((key) => research(tripId, { topic, ...(question ? { question } : {}) }, key))
  const go = () =>
    start(async () => {
      track("ai_action_started", { action: "research", credits: price, from_cache: false })
      const t0 = Date.now()
      const r = await run()
      if (r) track("ai_action_completed", { action: "research", outcome: r.ok ? "ok" : "failed", duration_seconds_bucket: duration(Date.now() - t0) })
    })
  const running = state.phase === "running"
  const done = state.phase === "done" ? state.data : null
  const have = credits?.available
  const short = have !== undefined && have < price
  // Out of credits (or a 402 from the API): the free path first, then the offer (07 section 6.2, out_of_credits_research).
  const locked = (state.phase === "failed" && state.fail.reason === "credits") || (short && state.phase === "idle" && !credits?.blocked)
  const notesHref = `/trips/${encodeURIComponent(tripId)}/notes`

  if (done)
    return (
      <section className="ai-result" aria-label={t("ai.act.notes")}>
        {done.from_cache && (
          <p role="status" className="h-soft">
            {done.checked_days_ago === null || done.checked_days_ago === 0
              ? t("ai.act.fromSharedToday")
              : t(done.checked_days_ago === 1 ? "ai.act.fromSharedOne" : "ai.act.fromShared", { days: done.checked_days_ago })}
            {done.stale ? ` ${t("ai.act.stale")}` : ""}
          </p>
        )}
        {done.notes.length === 0 && <p className="h-soft">{t("ai.act.researchEmpty")}</p>}
        {done.notes.map((n) => (
          <article key={`${n.title}|${n.urls.join(",")}`} className="ai-note">
            <h3 className="h-label">{n.title}</h3>
            <p className="ai-answer">{n.body}</p>
            {n.urls.map((u) => (
              <EvidenceLabel key={u} kind="research" url={u} checkedAt={seenAt(done, u)} stale={done.stale} />
            ))}
          </article>
        ))}
        {done.notes.length > 0 && (
          <>
            <AiLabel />
            <p className="h-soft">
              {t("ai.act.notesSaved")} <Link to={notesHref}>{t("ai.act.openNotes")}</Link>
            </p>
          </>
        )}
        <ReceiptLine receipt={done.credits} />
        <AiFeedback target={{ runId: done.run_id }} action="research" />
        <Btn variant="secondary" onClick={reset}>
          {t("ai.act.researchAgain")}
        </Btn>
      </section>
    )

  return (
    <>
      <p className="h-soft">{t("ai.sheet.researchDesc")}</p>
      <form
        className="ai-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (canRun && !running) go()
        }}
      >
        <div className="h-input">
          <label className="h-input__label" htmlFor="ai-topic">
            {t("ai.act.topic")}
          </label>
          <select id="ai-topic" className="h-input__field" value={topic} disabled={running} onChange={(e) => setTopic(e.target.value as ResearchTopic)}>
            {RESEARCH_TOPICS.map((k) => (
              <option key={k} value={k}>
                {t(`ai.act.topic_${k}`)}
              </option>
            ))}
          </select>
        </div>
        <TextField label={t("ai.act.ownQuestion")} helper={t("ai.act.ownQuestionHelp")} value={own} maxLength={MAX} disabled={running} onChange={(e) => setOwn(e.target.value)} />
        {have !== undefined && !short && <p className="h-soft">{t("ai.act.researchCost", { credits: price, balance: have, left: have - price })}</p>}
        <p className="h-soft">{t("ai.act.researchCache")}</p>
        <Btn variant="primary" mod={["spend"]} type="submit" busy={running} disabled={!canRun} aria-label={t("ai.act.researchAria", { credits: price })}>
          {t("ai.act.research")}
          {chip}
        </Btn>
      </form>
      {running && <Waiting label={t("ai.act.researching")} />}
      {locked && <OutOfCreditsResearch notesHref={notesHref} />}
      {state.phase === "failed" && state.fail.reason !== "credits" && <FailNotice fail={state.fail} onRetry={go} onAllow={() => start(go)} />}
    </>
  )
}
