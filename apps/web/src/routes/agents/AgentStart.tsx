import { useRef, useState } from "react"
import { Link, Navigate, useNavigate, useParams } from "react-router"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Btn, Icon, SegItem, SegmentedControl, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { useRoutes } from "../flights/api"
import { Modal } from "../itinerary/Modal"
import { useTrip } from "../trips/api"
import { tripStrip } from "../trips/TripStrip"
import "../trips/trips.css"
import { startRun, usePreview, useTaster, type RunKind, type StartResult } from "./api"
import { EntryCard } from "./EntryCard"
import "./agents.css"

const MAX_ROUTES = 3
const TOPIC_MAX = 300

type Failure = Extract<StartResult, { ok: false }>
const FAIL_COPY: Record<Exclude<Failure["reason"], "active">, string> = {
  credits: "agents.creditsLow",
  tasterUsed: "agents.tasterUsed",
  forbidden: "agents.forbidden",
  invalid: "agents.invalid",
  rate: "agents.rate",
  unavailable: "agents.unavailable",
  failed: "agents.failed",
}

/** 05 6.16 and 6.17 start: the entry card, what to run, then a confirm step that states the cost (or "Free taster") first. */
export function AgentStart() {
  const { token } = useAuth()
  const { id = "" } = useParams()
  const nav = useNavigate()
  const online = useOnline()
  const [kind, setKind] = useState<RunKind>("deep_research")
  const [topic, setTopic] = useState("")
  const [picked, setPicked] = useState<string[] | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const key = useRef<string | null>(null) // one Idempotency-Key per confirm, so a retry of the same tap cannot start twice
  const trip = useTrip(id, !!token)
  const canEdit = !!trip.data && trip.data.my_role !== "viewer"
  const routes = useRoutes(id, !!token && canEdit)
  const taster = useTaster(!!token && canEdit)
  const preview = usePreview(id, kind, !!token && canEdit && online)
  if (!token) return <Navigate to="/welcome" replace />

  const chosen = picked ?? routes.data?.slice(0, MAX_ROUTES).map((r) => r.id) ?? []
  const needsRoute = kind === "fare_hunt" && chosen.length === 0
  const p = preview.data
  const free = p ? p.taster : !!taster.data?.available && kind === "deep_research"
  const price = p?.price ?? taster.data?.credits ?? 40

  const toggle = (rid: string) => {
    const base = chosen
    setPicked(base.includes(rid) ? base.filter((x) => x !== rid) : base.length < MAX_ROUTES ? [...base, rid] : base)
  }
  const openConfirm = () => {
    key.current = crypto.randomUUID()
    setFailure(null)
    setConfirming(true)
  }
  const go = async () => {
    if (!p || busy) return
    setBusy(true)
    const body = kind === "fare_hunt" ? { kind, route_ids: chosen } : { kind, ...(topic.trim() ? { topic: topic.trim() } : {}) }
    const r = await startRun(id, body, key.current ?? crypto.randomUUID())
    setBusy(false)
    if (r.ok) {
      track("ai_action_started", { action: "agent_run", feature: kind, credits: p.credits, from_cache: p.from_cache, taster: p.taster })
      nav(`/trips/${encodeURIComponent(id)}/agents/${r.run.id}`, { replace: true })
      return
    }
    setConfirming(false)
    setFailure(r)
  }

  const left = p ? p.balance - p.credits : 0
  return (
    <AppShell active="trips" strip={tripStrip(nav, id, "flights")}>
      <div className="overview">
        {!online && (
          <p role="status" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("agents.offline")}
          </p>
        )}
        <h1 className="h-title">{t("agents.title")}</h1>
        {trip.isPending && <Skeleton shape="block" />}
        {trip.isError && <QueryError error={trip.error} message={t("agents.startError")} onRetry={() => void trip.refetch()} />}
        {trip.data && !canEdit && <p className="h-soft">{t("agents.viewerNote")}</p>}
        {canEdit && preview.isError && !preview.data && <QueryError error={preview.error} message={t("agents.startError")} onRetry={() => void preview.refetch()} />}
        {canEdit && (
          <>
            <EntryCard free={free} price={price} onStart={openConfirm} disabled={!online || !p || needsRoute || busy} />
            <SegmentedControl aria-label={t("agents.kinds")}>
              <SegItem selected={kind === "deep_research"} onClick={() => setKind("deep_research")}>{t("agents.kindResearch")}</SegItem>
              <SegItem selected={kind === "fare_hunt"} onClick={() => setKind("fare_hunt")}>{t("agents.kindFare")}</SegItem>
            </SegmentedControl>
            {kind === "deep_research" ? (
              <TextField label={t("agents.topic")} helper={t("agents.topicHelp")} value={topic} maxLength={TOPIC_MAX} onChange={(e) => setTopic(e.target.value)} />
            ) : routes.data && routes.data.length === 0 ? (
              <p className="h-soft">
                {t("agents.noRoutes")} <Link to={`/trips/${encodeURIComponent(id)}/flights`}>{t("flights.title")}</Link>
              </p>
            ) : (
              <fieldset className="agents__routes">
                <legend className="h-label">{t("agents.routes")}</legend>
                {routes.data?.map((r) => (
                  <label key={r.id} className="flights__check">
                    <input type="checkbox" checked={chosen.includes(r.id)} onChange={() => toggle(r.id)} />
                    {r.origin_codes.join(", ")} {t("flights.to").toLowerCase()} {r.destination_codes.join(", ")}
                  </label>
                ))}
              </fieldset>
            )}
            {failure && (
              <p role="alert" className="h-input__error">
                <Icon name="circle-alert" size={16} />
                {failure.reason === "active" ? t("agents.active") : t(FAIL_COPY[failure.reason])}{" "}
                {failure.reason === "active" && failure.activeRunId && (
                  <Link to={`/trips/${encodeURIComponent(id)}/agents/${failure.activeRunId}`}>{t("agents.viewActive")}</Link>
                )}
                {(failure.reason === "credits" || failure.reason === "tasterUsed") && <Link to="/account">{t("agents.seePlans")}</Link>}
              </p>
            )}
          </>
        )}
      </div>
      {confirming && p && (
        <Modal title={t("agents.confirmTitle")} onClose={() => setConfirming(false)}>
          <p className="h-soft">
            {p.taster
              ? t("agents.confirmTaster")
              : p.sufficient
                ? t("agents.confirmPaid", { credits: p.credits, balance: p.balance, left })
                : t("agents.confirmShort", { credits: p.credits, balance: p.balance })}
          </p>
          <div className="agents__actions">
            {p.sufficient ? (
              <Btn variant="primary" busy={busy} onClick={() => void go()}>{t("agents.start")}</Btn>
            ) : (
              <Link className="h-btn h-btn--primary" to="/account">{t("agents.seePlans")}</Link>
            )}
            <Btn variant="secondary" onClick={() => setConfirming(false)}>{t("agents.cancel")}</Btn>
          </div>
        </Modal>
      )}
    </AppShell>
  )
}
