import { useEffect, useMemo, useRef, useState } from "react"
import { Link, Navigate, useNavigate, useParams } from "react-router"
import { AiFeedback, AiLabel } from "../../components/ai"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Btn, Field, Icon, StatusStub, TicketStub, TripTicket } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { tripStrip } from "../trips/TripStrip"
import "../trips/trips.css"
import { cancelRun, isActive, useRun, useRunEvents, type AgentRun as Run } from "./api"
import { buildView, estimateStopCredits, mmss, type View } from "./derive"
import { Modal } from "../itinerary/Modal"
import { EvidenceRow } from "./Findings"
import "./agents.css"

const STAGES = ["agents.stepSearching", "agents.stepReading", "agents.stepChecking", "agents.stepSaving", "agents.stepDone"] as const
const SAY = ["agents.saySearching", "agents.sayReading", "agents.sayChecking", "agents.saySaving", "agents.stepDone"] as const

type Phase = "queued" | "running" | "done" | "stopped" | "failed"
const phaseOf = (r: Run): Phase =>
  r.status === "queued" ? "queued"
  : r.status === "running" ? "running"
  : r.status === "succeeded" ? "done"
  : r.status === "partial" || r.status === "cancelled" ? "stopped"
  : "failed"

const plural = (n: number, one: string, other: string) => t(n === 1 ? one : other, { n })
const found = (fares: number, notes: number) => [fares && plural(fares, "agents.fareCount_one", "agents.fareCount_other"), notes && plural(notes, "agents.noteCount_one", "agents.noteCount_other")].filter(Boolean).join(" and ")

/** Why a run failed, from the API error_code (05 6.16 error wording). Unknown codes get the plain sentence. */
const causeOf = (code: string | null) =>
  /deadline|timed_out/.test(code ?? "") ? t("agents.failedTimeout")
  : /worker_lost|interrupted/.test(code ?? "") ? t("agents.failedLost")
  : /unavailable|provider|serp|search/.test(code ?? "") ? t("agents.failedProvider")
  : t("agents.failedBare")

/**
 * The closing sentence of a finished run (05 6.16 content and states). Credits are the starter's receipt, so others see
 * none. A taster is free, so its sentences carry no credit figure either.
 */
function summaryOf(run: Run, v: View): string {
  const charged = run.is_taster ? null : (run.credits?.charged ?? null)
  const saved = v.fares.length + v.notes.length
  const phase = phaseOf(run)
  const tail = charged === 0 ? " " + t("agents.notCharged") : charged ? " " + t("agents.billedFor", { credits: charged }) : ""
  if (phase === "failed") return causeOf(run.error_code) + tail
  if (saved === 0) {
    if (phase === "stopped") return charged === 0 ? t("agents.stoppedNothingFree") : charged ? t("agents.stoppedNothing", { credits: charged }) : t("agents.emptyBare")
    return charged === 0 ? t("agents.emptySummary") : charged ? t("agents.emptyCharged", { credits: charged }) : t("agents.emptyBare")
  }
  const what = found(v.fares.length, v.notes.length)
  if (charged === null) return t(phase === "done" ? "agents.doneSummaryNoCredits" : "agents.stoppedSummaryNoCredits", { found: what })
  return t(phase === "done" ? "agents.doneSummary" : "agents.stoppedSummary", { found: what, credits: charged })
}

const STOP_X = [32.6, 97.8, 163, 228.2, 293.4]

/** design `.h-run__route`: dotted legs between five stops. Finished stops carry a check, the plane sits at the current stage. */
function RunRoute({ stage }: { stage: number }) {
  const last = Math.min(Math.max(stage, 0), STOP_X.length - 1)
  return (
    <svg className="h-run__route" viewBox="0 0 326 30" aria-hidden="true" focusable="false">
      <g className="h-run__dots">
        {STOP_X.slice(0, last).flatMap((x, i) =>
          [0, 1, 2, 3, 4].map((k) => <circle key={`${i}-${k}`} className="h-run__dot" cx={x + 12 + (k * (STOP_X[i + 1]! - x - 24)) / 4} cy="15" r="2.6" />),
        )}
      </g>
      {STOP_X.slice(0, last).map((x) => (
        <g key={x} transform={`translate(${x} 15)`}>
          <circle className="h-run__stop-ring" r="10.5" />
          <circle className="h-run__stop-core" r="8.5" />
          <path className="h-run__stop-check" d="M-3.6 .2L-1 2.8L3.8 -2.6" />
        </g>
      ))}
      <g transform={`translate(${STOP_X[last]} 15)`}>
        <g className="h-run__plane">
          <circle className="h-run__plane-ring" r="15" />
          <circle className="h-run__plane-core" r="12.5" />
          <use className="h-run__plane-glyph" href="#h-plane-path" transform="rotate(90) scale(.205) translate(-50 -50)" />
        </g>
      </g>
    </svg>
  )
}

const bucket = (s: number) => (s < 30 ? "under_30" : s < 60 ? "30_to_60" : s < 180 ? "60_to_180" : "over_180")

function Elapsed({ run }: { run: Run }) {
  const [now, setNow] = useState(() => Date.now())
  const active = isActive(run.status)
  useEffect(() => {
    if (!active) return
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [active])
  const from = Date.parse(run.started_at ?? run.queued_at)
  const to = run.finished_at ? Date.parse(run.finished_at) : now
  return <>{mmss((to - from) / 1000)}</>
}

/** 05 6.16 agent run: ticket with status and Stop, the step list, findings, and 6.17's price card after a taster. */
export function AgentRunPage() {
  const { token } = useAuth()
  const { id = "", runId = "" } = useParams()
  const nav = useNavigate()
  const online = useOnline()
  const run = useRun(runId, !!token)
  const events = useRunEvents(runId, !!token && !!run.data)
  const view = useMemo(() => buildView(events), [events])
  const [stopping, setStopping] = useState(false)
  const [busy, setBusy] = useState(false)
  const [stopError, setStopError] = useState<string | null>(null)
  const [dismissed, setDismissed] = useState<number[]>([])
  const counted = useRef<Set<number>>(new Set())
  const completed = useRef(false)
  const r = run.data
  const starter = !!r?.credits
  const phase = r ? phaseOf(r) : null
  const terminal = !!r && !isActive(r.status)

  // agent_finding_saved once per saved finding the starter watches arrive. A reload replays them, which is fine: the set is per mount.
  useEffect(() => {
    if (!starter) return
    for (const f of [...view.fares, ...view.notes]) {
      if (counted.current.has(f.seq)) continue
      counted.current.add(f.seq)
      track("agent_finding_saved", { kind: f.kind })
    }
  }, [view, starter])
  // ai_action_completed once, when the starter sees the run end. A stop is partial and a free refund is refunded.
  useEffect(() => {
    if (!r || !starter || !terminal || completed.current) return
    completed.current = true
    const charged = r.credits?.charged ?? null
    const saved = view.fares.length + view.notes.length
    const outcome = r.status === "partial" || r.status === "cancelled" ? "partial"
      : r.status === "succeeded" ? (saved === 0 && charged === 0 ? "refunded" : "ok")
      : charged === 0 ? "refunded" : "failed"
    const secs = (Date.parse(r.finished_at ?? r.queued_at) - Date.parse(r.started_at ?? r.queued_at)) / 1000
    track("ai_action_completed", { action: "agent_run", feature: r.kind, outcome, taster: r.is_taster, duration_seconds_bucket: bucket(secs) })
  }, [r, starter, terminal, view])

  // 6.17: one price card per session, muted for 7 days after it is closed.
  const [upsell, setUpsell] = useState(false)
  const keptFree = !!r && r.is_taster && starter && terminal && r.credits?.charged === 0
  useEffect(() => {
    if (!r || !r.is_taster || !starter || !terminal || keptFree || upsell) return
    try {
      const muted = Number(localStorage.getItem("hermi.taster.mute") ?? 0) > Date.now()
      if (muted || sessionStorage.getItem("hermi.taster.upsell") === "1") return
      sessionStorage.setItem("hermi.taster.upsell", "1")
    } catch {
      /* storage blocked: show it, the rules are a courtesy */
    }
    setUpsell(true)
    track("taster_upsell_shown")
  }, [r, starter, terminal, keptFree, upsell])

  if (!token) return <Navigate to="/welcome" replace />
  const strip = tripStrip(nav, id, "flights")
  const back = `/trips/${encodeURIComponent(id)}/flights`

  const doStop = async () => {
    if (!r) return
    setBusy(true)
    setStopError(null)
    const res = await cancelRun(r.id)
    setBusy(false)
    setStopping(false)
    if (!res.ok) setStopError(res.reason === "forbidden" ? t("agents.stopForbidden") : res.reason === "finished" ? t("agents.stopFinished") : t("agents.stopFailed"))
  }
  const closeUpsell = () => {
    try {
      localStorage.setItem("hermi.taster.mute", String(Date.now() + 7 * 86_400_000))
    } catch {
      /* ignore */
    }
    setUpsell(false)
    nav(back)
  }

  if (run.isPending) return <AppShell active="trips" strip={strip}><div className="overview"><Skeleton shape="overview" /></div></AppShell>
  if (!r || run.isError) {
    return <AppShell active="trips" strip={strip}><div className="overview"><QueryError error={run.error} message={t("agents.loadError")} onRetry={() => void run.refetch()} /></div></AppShell>
  }

  const active = isActive(r.status)
  const reserved = r.credits?.reserved ?? 0
  const turns = Math.max(r.turns_used ?? 0, view.turns)
  const estimate = estimateStopCredits({ reserved, turns })
  const goal = r.kind === "fare_hunt" ? t("agents.goalFare") : r.params.topic ? t("agents.goalResearch", { topic: r.params.topic }) : t("agents.goalResearchNone")
  const label = r.cancel_requested && active ? "agents.statusStopping" : { queued: "agents.statusQueued", running: "agents.statusRunning", done: "agents.statusDone", stopped: "agents.statusStopped", failed: "agents.statusFailed" }[phase!]
  const stage = terminal ? 4 : Math.max(view.stage, 0)
  const say = terminal ? summaryOf(r, view) : r.status === "queued" ? t("agents.queued") : t(SAY[stage])
  const shownFares = view.fares.filter((f) => !dismissed.includes(f.seq))
  const shownNotes = view.notes.filter((f) => !dismissed.includes(f.seq))
  const shownAll = shownFares.length + shownNotes.length
  const canStop = starter && active && !r.cancel_requested
  const credits = r.is_taster ? t("agents.freeTaster") : String(terminal ? (r.credits?.charged ?? reserved) : reserved)
  const stubIcon = phase === "done" ? "circle-check" : phase === "failed" ? "circle-alert" : phase === "stopped" ? "x" : phase === "queued" ? "circle" : "sparkles"

  return (
    <AppShell active="trips" strip={strip}>
      <div className="overview">
        {!online && (
          <p role="status" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("agents.runOffline")}
          </p>
        )}
        {active && starter && (
          <div className="agents__stop">
            {r.status === "queued" ? (
              <Btn variant="secondary" mod={["sm"]} busy={busy} disabled={!online || r.cancel_requested} onClick={() => void doStop()}>{t("agents.cancelRun")}</Btn>
            ) : (
              <Btn variant="secondary" mod={["sm"]} disabled={!canStop || !online} onClick={() => setStopping(true)}>{t("agents.stop")}</Btn>
            )}
            <span className="h-soft">{r.status === "queued" ? t("agents.queuedNoCharge") : r.is_taster ? t("agents.freeTaster") : t("agents.billedByUse", { credits: reserved })}</span>
          </div>
        )}
        <TripTicket mod={["sky", "run"]} role="group" aria-label={`${t("agents.runTitle")}: ${t(label)}`}>
          <div className="h-ticket__head h-ticket__head--sky">
            <span className="h-label h-label--onsky">{r.is_taster ? t("agents.taster") : t("agents.runTitle")}</span>
            <h1 className="h-ticket__name">{goal}</h1>
            <dl className="h-ticket__fields h-ticket__fields--run">
              <Field label={t("agents.elapsed")}><Elapsed run={r} /></Field>
              {r.credits && <Field label={terminal ? t("agents.creditsUsed") : t("agents.creditsReserved")}>{credits}</Field>}
            </dl>
          </div>
          <div className="h-run">
            <RunRoute stage={stage} />
            <ol className="h-run__steps" aria-label={t("agents.steps")}>
              {STAGES.map((k, i) => {
                const state = i < stage || (terminal && i <= stage) ? t("agents.stepDoneWord") : i === stage ? t("agents.current") : ""
                const at = view.stageAt[i]
                return (
                  <li
                    key={k}
                    className={`h-run__step${i === stage && !terminal ? " agents__step--current" : ""}`}
                    aria-current={i === stage && !terminal ? "step" : undefined}
                    aria-label={[t(k), at !== undefined ? mmss(at) : "", state].filter(Boolean).join(", ")}
                  >
                    <span>{t(k)}</span>
                    <span className="h-run__time">{at !== undefined ? mmss(at) : ""}</span>
                  </li>
                )
              })}
            </ol>
          </div>
          <TicketStub>
            {terminal ? (
              <span className="h-touchdown">
                <StatusStub status="done" icon={stubIcon}>{t(label)}</StatusStub>
              </span>
            ) : (
              <StatusStub status="planning" icon={stubIcon}>{t(label)}</StatusStub>
            )}
            <span className="h-ticket__note">{terminal ? say : active && r.status === "queued" ? t("agents.queued") : view.recent.length ? view.recent[view.recent.length - 1]!.summary : t(SAY[stage])}</span>
          </TicketStub>
        </TripTicket>
        <p className="h-sr-only" role="status" aria-live="polite">{say}</p>
        {stopError && <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{stopError}</p>}
        {keptFree && <p className="h-soft">{t("agents.tasterKept")}</p>}

        {(shownAll > 0 || view.fares.length + view.notes.length > 0) && (
          <section aria-label={t("agents.findings", { n: shownAll })}>
            <h2 className="h-label h-label--section">{t("agents.findings", { n: shownAll })}</h2>
            {shownFares.length > 0 && <h3 className="h-label agents__group">{t("agents.fares", { n: shownFares.length })}</h3>}
            {shownFares.map((f) => <EvidenceRow key={f.seq} tripId={id} f={f} onDismiss={() => setDismissed((d) => [...d, f.seq])} />)}
            {shownNotes.length > 0 && <h3 className="h-label agents__group">{t("agents.notes", { n: shownNotes.length })}</h3>}
            {shownNotes.map((f) => <EvidenceRow key={f.seq} tripId={id} f={f} onDismiss={() => setDismissed((d) => [...d, f.seq])} />)}
            <AiLabel found />
            {terminal && <AiFeedback target={{ runId: r.id }} action="agent_run" />}
          </section>
        )}
        {view.notSaved.length > 0 && (
          <details className="agents__notsaved">
            <summary>{t("agents.notSaved", { n: view.notSaved.length })}</summary>
            <ul>
              {view.notSaved.map((n) => <li key={n.seq}>{n.reason}</li>)}
            </ul>
          </details>
        )}
        {upsell && (
          <section className="agents__upsell">
            <p>{t("agents.upsell")}</p>
            <div className="agents__actions">
              <Link className="h-btn h-btn--secondary" to="/account">{t("agents.seePlans")}</Link>
              <Btn variant="secondary" onClick={closeUpsell}>{t("agents.upsellDone")}</Btn>
            </div>
          </section>
        )}
        {!starter && active && <p className="h-soft">{t("agents.stopForbidden")}</p>}
      </div>
      {stopping && (
        <Modal title={t("agents.stopTitle")} onClose={() => setStopping(false)}>
          <p>{r.is_taster ? t("agents.stopTaster") : t("agents.stopBody", { n: estimate })}</p>
          {!r.is_taster && <p className="h-soft">{t("agents.stopEstimate")}</p>}
          <div className="agents__actions">
            <Btn variant="primary" busy={busy} onClick={() => void doStop()}>{t("agents.stopRun")}</Btn>
            <Btn variant="secondary" onClick={() => setStopping(false)}>{t("agents.keepRunning")}</Btn>
          </div>
        </Modal>
      )}
    </AppShell>
  )
}
