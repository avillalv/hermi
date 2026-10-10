import { useEffect } from "react"
import { Link } from "react-router"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { Btn, Icon } from "../kit"
import type { Fail, Receipt } from "./run"
import "./ai.css"

const FAIL_COPY: Record<Fail["reason"], string> = {
  credits: "ai.act.credits",
  blocked: "ai.sheet.blocked",
  consent: "ai.consentOff",
  aiOff: "ai.tripOff",
  forbidden: "ai.act.forbidden",
  invalid: "ai.act.invalid",
  rate: "ai.sheet.rate",
  paused: "ai.act.paused",
  unavailable: "ai.act.unavailable",
  failed: "ai.sheet.failed",
}

/**
 * The failure of an AI call, in words (05 6.15 States): what happened, that nothing was charged, and a way on. A server
 * sentence (the pause names its end date) wins over the default. Rate limits say how long when the API did.
 */
export function FailNotice({ fail, onRetry, onAllow }: { fail: Fail; onRetry?: () => void; onAllow?: () => void }) {
  const base = fail.reason === "paused" && fail.message ? fail.message : t(FAIL_COPY[fail.reason])
  const wait = fail.reason === "rate" && fail.retryAfter ? ` ${t("states.waitSeconds", { seconds: fail.retryAfter })}` : ""
  const retry = fail.reason === "rate" || fail.reason === "unavailable" || fail.reason === "failed" || fail.reason === "invalid"
  return (
    <div role="alert" className="ai-fail">
      <p className="h-input__error">
        <Icon name="circle-alert" size={16} />
        {fail.reason === "invalid" && fail.message ? fail.message : base + wait}
      </p>
      <div className="ai-actions">
        {retry && onRetry && (
          <Btn variant="secondary" mod={["sm"]} onClick={onRetry}>
            {t("ai.act.retry")}
          </Btn>
        )}
        {fail.reason === "consent" && onAllow && (
          <Btn variant="primary" mod={["sm"]} onClick={onAllow}>
            {t("ai.consentReview")}
          </Btn>
        )}
        {(fail.reason === "credits" || fail.reason === "blocked") && (
          <Link className="h-btn h-btn--secondary h-btn--sm" to="/account">
            {t("ai.sheet.seePlans")}
          </Link>
        )}
      </div>
    </div>
  )
}

/** After a result: a free repeat says so, a paid one says what it used and what is left. */
export function ReceiptLine({ receipt }: { receipt: Receipt }) {
  const free = receipt.from_cache // a refund or a free action charges 0 too, and is not a repeat
  const used = receipt.charged ?? receipt.reserved
  return (
    <p role="status" className="h-soft ai-receipt">
      <Icon name="coins" size={14} />
      {free
        ? t("ai.act.freeRepeat")
        : t(used === 1 ? "ai.act.usedOne" : "ai.act.used", { credits: used }) +
          (receipt.balance_after === null ? "" : ` ${t("ai.act.left", { credits: receipt.balance_after })}`)}
    </p>
  )
}

/** Three plain rows, so the wait has the shape of the answer (05 4.17 loading). */
export function Waiting({ label }: { label: string }) {
  return (
    <div role="status" aria-live="polite" className="ai-wait">
      <p className="h-soft">{label}</p>
      <div className="ai-wait__rows" aria-hidden="true">
        <span className="ai-bar ai-bar--long" />
        <span className="ai-bar" />
        <span className="ai-bar ai-bar--short" />
      </div>
    </div>
  )
}

/**
 * 05 4.2 locked card + 07 section 6.2 `out_of_credits_draft`: day one of a draft, blurred, with the offer beside it and
 * the free path first. The preview is a layout sample, not a real draft: a real one would cost provider money the person
 * did not pay for. On web there is nothing to buy (WF-018), so the offer points to Account and the iOS app.
 */
export function OutOfCreditsDraft({ planHref }: { planHref: string }) {
  useEffect(() => void track("paywall_viewed", { placement: "credits", offer_shown: [] }), [])
  return (
    <section className="ai-locked" aria-labelledby="ai-locked-h">
      <div className="ai-locked__card">
        <div className="ai-locked__preview" aria-hidden="true">
          {["09:00", "12:30", "15:00", "19:00"].map((time) => (
            <div key={time} className="ai-locked__row">
              <span className="h-num">{time}</span>
              <span className="ai-bar ai-bar--long" />
            </div>
          ))}
        </div>
        <p className="ai-locked__over">
          <Icon name="lock" size={18} />
          {t("ai.act.lockedDay")}
        </p>
      </div>
      <h2 className="h-title" id="ai-locked-h">
        {t("ai.act.outTitle")}
      </h2>
      <p className="h-soft">{t("ai.act.outBody")}</p>
      <div className="ai-actions">
        <Link className="h-btn h-btn--primary" to={planHref}>
          {t("ai.act.planMyself")}
        </Link>
        <Link className="h-btn h-btn--secondary" to="/account">
          {t("ai.act.seeCredits")}
        </Link>
      </div>
      <p className="h-soft">{t("ai.act.iosOnly")}</p>
    </section>
  )
}
