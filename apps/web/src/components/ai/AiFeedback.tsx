import { useState } from "react"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { Btn, Icon } from "../kit"
import { sendReport, type ReportReason, type ReportTarget } from "./api"
import "./ai.css"

type Action = "explain" | "live_search" | "draft_day" | "draft_trip" | "research" | "agent_run" | "verify_plan"
type Phase = "idle" | "up" | "choose" | "sending" | "sent" | "error" | "rate"

const REASONS: { code: ReportReason; label: string }[] = [
  { code: "wrong_info", label: "ai.reasonWrong" },
  { code: "harmful", label: "ai.reasonHarmful" },
  { code: "privacy", label: "ai.reasonPrivacy" },
  { code: "copyright", label: "ai.reasonCopyright" },
]

/**
 * Thumbs on AI output (06 section 12.4). Up is a thanks and an `ai_feedback_given` event. Down asks what was wrong and
 * files a content report (POST /reports), which the moderation queue (WF-106) reads. One report per person per target:
 * a second tap is harmless. Buttons carry words, so there is no icon-only control.
 */
export function AiFeedback({ target, action }: { target: ReportTarget; action: Action }) {
  const online = useOnline()
  const [phase, setPhase] = useState<Phase>("idle")
  const send = async (reason: ReportReason) => {
    setPhase("sending")
    const r = await sendReport(target, reason)
    if (r === "rate") return setPhase("rate")
    if (r === "failed") return setPhase("error")
    // "gone": the target was removed since it was shown. The person sees the thanks, but nothing was reported, so no event.
    if (r === "ok") {
      track("ai_feedback_given", { action, rating: "down", reason })
      track("content_reported", { surface: "runId" in target ? "ai_answer" : "research", reason }) // 10 section 4: `research` covers agent notes
    }
    setPhase("sent")
  }
  const up = () => {
    track("ai_feedback_given", { action, rating: "up", reason: "none" })
    setPhase("up")
  }
  const done = phase === "up" || phase === "sent"
  const choosing = phase === "choose" || phase === "sending" || phase === "error" || phase === "rate"
  return (
    <div className="ai-feedback">
      <div className="ai-feedback__row" role="group" aria-label={t("ai.feedbackGroup")}>
        <Btn variant="secondary" mod={["sm"]} aria-pressed={phase === "up"} disabled={!online || phase === "sending" || done} onClick={up}>
          <Icon name="check" size={16} />
          {t("ai.helpful")}
        </Btn>
        <Btn variant="secondary" mod={["sm"]} aria-pressed={phase === "sent" || choosing} disabled={!online || phase === "sending" || done} onClick={() => setPhase("choose")}>
          <Icon name="x" size={16} />
          {t("ai.notHelpful")}
        </Btn>
      </div>
      {!online && !done && (
        <p role="status" className="h-soft">
          {t("ai.feedbackOffline")}
        </p>
      )}
      {choosing && (
        <fieldset className="ai-feedback__reasons">
          <legend className="h-label">{t("ai.whatWrong")}</legend>
          {REASONS.map((r) => (
            <Btn key={r.code} variant="text" mod={["sm"]} disabled={!online || phase === "sending"} onClick={() => void send(r.code)}>
              {t(r.label)}
            </Btn>
          ))}
        </fieldset>
      )}
      {phase === "up" && (
        <p role="status" className="h-soft">
          {t("ai.thanksUp")}
        </p>
      )}
      {phase === "sent" && (
        <p role="status" className="h-soft">
          {t("ai.thanksReport")}
        </p>
      )}
      {(phase === "error" || phase === "rate") && (
        <p role="alert" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {t(phase === "rate" ? "ai.feedbackRate" : "ai.feedbackError")}
        </p>
      )}
    </div>
  )
}
