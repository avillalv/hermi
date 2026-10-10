import { useState } from "react"
import { Link, useSearchParams } from "react-router"
import { FailNotice, OutOfCreditsDraft, Waiting, draftDay, draftTrip, useAiRun } from "../../components/ai"
import { Btn, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { dayText } from "../itinerary/meta"
import { ActionFrame, type Frame } from "./ActionFrame"
import { DraftPreview } from "./DraftPreview"
import { duration } from "./duration"

const MAX_DAYS = 60

/** Every date from `start` to `end`, at most `MAX_DAYS`, as calendar days (no time zone arithmetic). */
export function tripDays(start: string | null, end: string | null): string[] {
  if (!start || !end || end < start) return []
  const out: string[] = []
  for (let d = new Date(`${start}T00:00:00Z`); out.length < MAX_DAYS; d = new Date(d.getTime() + 86_400_000)) {
    const iso = d.toISOString().slice(0, 10)
    if (iso > end) break
    out.push(iso)
  }
  return out
}

/** 05 6.15 Draft this day (F-AI-2). */
export function DraftDay() {
  return (
    <ActionFrame action="draft_day" title={t("ai.sheet.day")}>
      {(f) => <Drafter {...f} kind="day" />}
    </ActionFrame>
  )
}

/** 05 6.15 Draft the trip (F-AI-2): up to 14 days from the trip start, or from a chosen day. */
export function DraftTrip() {
  return (
    <ActionFrame action="draft_trip" title={t("ai.sheet.trip")}>
      {(f) => <Drafter {...f} kind="trip" />}
    </ActionFrame>
  )
}

function Drafter({ tripId, trip, credits, price, chip, canRun, start, kind }: Frame & { kind: "day" | "trip" }) {
  const [q] = useSearchParams()
  const days = tripDays(trip.start_date, trip.end_date)
  const [day, setDay] = useState(() => (days.includes(q.get("day") ?? "") ? (q.get("day") as string) : (days[0] ?? "")))
  const [notes, setNotes] = useState("")
  const note = notes.trim()
  const action = kind === "day" ? "draft_day" : "draft_trip"
  const { state, run, reset } = useAiRun((key) =>
    kind === "day"
      ? draftDay(tripId, { day, ...(note ? { preferences: note } : {}) }, key)
      : draftTrip(tripId, { ...(note ? { style: note } : {}), ...(day && day !== days[0] ? { from_day: day } : {}) }, key),
  )
  const go = () =>
    start(async () => {
      track("ai_action_started", { action, credits: price, from_cache: false })
      const t0 = Date.now()
      const r = await run()
      if (r) track("ai_action_completed", { action, outcome: r.ok ? "ok" : "failed", duration_seconds_bucket: duration(Date.now() - t0) })
    })
  const planHref = `/trips/${encodeURIComponent(tripId)}/plan`
  const running = state.phase === "running"
  const done = state.phase === "done" ? state.data : null
  const short = !!credits && credits.available < price
  // 0 credits (or a 402 from the API): day one is blurred behind the offer and the free path (07 section 6.2, out_of_credits_draft).
  const locked = (state.phase === "failed" && state.fail.reason === "credits") || (short && state.phase === "idle" && !credits?.blocked)

  if (days.length === 0)
    return (
      <section className="ai-result">
        <p className="h-soft">{t("ai.act.needDates")}</p>
        <Link className="h-btn h-btn--primary" to={`/trips/${encodeURIComponent(tripId)}/edit`}>
          {t("ai.act.addDates")}
        </Link>
      </section>
    )
  if (done)
    return (
      <DraftPreview
        tripId={tripId}
        action={action}
        runId={done.run_id}
        receipt={done.credits}
        overview={done.overview}
        days={done.days}
        onDiscard={reset}
      />
    )
  return (
    <>
      <p className="h-soft">{t(kind === "day" ? "ai.act.dayHelp" : "ai.act.tripHelp")}</p>
      <form
        className="ai-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (canRun && !running) go()
        }}
      >
        <div className="h-input">
          <label className="h-input__label" htmlFor="ai-day">
            {t(kind === "day" ? "ai.act.whichDay" : "ai.act.startDay")}
          </label>
          <select id="ai-day" className="h-input__field" value={day} disabled={running} onChange={(e) => setDay(e.target.value)}>
            {days.map((d, i) => (
              <option key={d} value={d}>
                {t("ai.act.dayOption", { n: i + 1, date: dayText(d) })}
              </option>
            ))}
          </select>
        </div>
        <TextField label={t("ai.act.wishes")} helper={t("ai.act.wishesHelp")} value={notes} maxLength={300} disabled={running} onChange={(e) => setNotes(e.target.value)} />
        <Btn variant="primary" mod={["spend"]} type="submit" busy={running} disabled={!canRun || !day} aria-label={t(price === 1 ? "ai.act.draftAriaOne" : "ai.act.draftAria", { credits: price })}>
          {t(kind === "day" ? "ai.act.draftDay" : "ai.act.draftTrip")}
          {chip}
        </Btn>
      </form>
      {running && <Waiting label={t(kind === "day" ? "ai.act.drafting" : "ai.act.draftingTrip")} />}
      {locked && <OutOfCreditsDraft planHref={planHref} />}
      {state.phase === "failed" && state.fail.reason !== "credits" && <FailNotice fail={state.fail} onRetry={go} onAllow={() => start(go)} />}
    </>
  )
}
