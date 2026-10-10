import { useEffect, useRef, useState } from "react"
import { useLocation, useNavigate } from "react-router"
import { Btn } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useAuth } from "../../routes/auth/authStore"
import { Modal } from "../../routes/itinerary/Modal"
import { useMe } from "../../routes/onboarding/trips"
import { claimGuestTrip, type ClaimOutcome } from "./claim"
import { clearGuest, setKeptSeparate, useGuest } from "./store"
import "./guest.css"

type Step =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "choose"; trips: number; people: number }
  | { kind: "failed" }
  | { kind: "kept" }
  | { kind: "done"; archived: boolean; tripId: string | null }

/**
 * Claims the guest trip into the account after sign-in (05 6.2, F-ACC-3). It runs once the account row exists (`GET /me`
 * answers), with the claim id stored beside the trip so a retry is the same claim. Nothing is cleared until the server
 * answered ok, so a failure leaves the trip on the phone.
 */
export function GuestClaimHost() {
  const { token } = useAuth()
  const guest = useGuest()
  const nav = useNavigate()
  const path = useLocation().pathname
  const waiting = !!token && !!guest && !guest.kept_separate
  const me = useMe(token, waiting)
  const [step, setStep] = useState<Step>({ kind: "idle" })
  const started = useRef<string | null>(null)
  const existing = useRef(0)
  const wasKept = useRef(!!guest?.kept_separate)

  // A new account row appears when onboarding finishes: look again whenever the screen changes.
  useEffect(() => {
    if (waiting && me.data === false) void me.refetch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path])

  const finish = (r: ClaimOutcome) => {
    if (r.kind === "ok") {
      clearGuest()
      setStep({ kind: "done", archived: r.archived, tripId: r.tripId })
    } else if (r.kind === "choose") {
      existing.current = r.trips
      setStep({ kind: "choose", trips: r.trips, people: r.people })
    } else setStep({ kind: "failed" })
  }
  const run = async (merge?: boolean) => {
    if (!guest) return
    setStep({ kind: "busy" })
    finish(await claimGuestTrip(guest, merge))
  }

  // The trip stays on the phone; the banner Save is the way back to the claim.
  const notNow = () => {
    setKeptSeparate(true)
    setStep({ kind: "idle" })
  }

  useEffect(() => {
    if (!waiting || !guest || me.data !== true || started.current === guest.claim_id) return
    if (wasKept.current) return // kept to not kept is the merge effect's claim, so it is sent once
    started.current = guest.claim_id
    void run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [waiting, guest?.claim_id, me.data])

  // Save in the banner after "Keep separate" (or "Not now" on a failed claim): claim again as a merge, same claim id.
  useEffect(() => {
    const kept = !!guest?.kept_separate
    if (wasKept.current && !kept && token && guest) {
      started.current = guest.claim_id
      void run(true)
    }
    wasKept.current = kept
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [guest?.kept_separate])

  if (!token) return null
  if (step.kind === "choose")
    return (
      <Modal
        title={t("guest.mergeTitle")}
        onClose={() => {
          setKeptSeparate(true)
          setStep({ kind: "idle" })
        }}
      >
        <p className="h-soft">{t(step.trips === 1 ? "guest.mergeBodyOne" : "guest.mergeBody", { trips: step.trips })}</p>
        <div className="h-stack h-stack--roomy">
          <Btn variant="primary" onClick={() => void run(true)}>
            {t("guest.merge")}
          </Btn>
          <Btn
            variant="secondary"
            onClick={() => {
              setKeptSeparate(true)
              setStep({ kind: "kept" })
            }}
          >
            {t("guest.keepSeparate")}
          </Btn>
        </div>
      </Modal>
    )
  if (step.kind === "failed")
    return (
      <Modal title={t("guest.errorTitle")} onClose={notNow}>
        <p role="alert" className="h-soft">
          {t("guest.error")}
        </p>
        <div className="h-stack h-stack--roomy">
          <Btn variant="primary" onClick={() => void run(existing.current ? true : undefined)}>
            {t("guest.retry")}
          </Btn>
          <Btn variant="text" onClick={notNow}>
            {t("guest.notNow")}
          </Btn>
        </div>
      </Modal>
    )
  if (step.kind === "kept")
    return (
      <Modal title={t("guest.keptTitle")} onClose={() => setStep({ kind: "idle" })}>
        <p className="h-soft">{t("guest.keptBody")}</p>
        <Btn variant="primary" onClick={() => setStep({ kind: "idle" })}>
          {t("guest.ok")}
        </Btn>
      </Modal>
    )
  if (step.kind === "done") {
    const { archived, tripId } = step
    return (
      <Modal title={t("guest.doneTitle")} onClose={() => setStep({ kind: "idle" })}>
        <p className="h-soft">{t(archived ? "guest.doneArchived" : "guest.doneBody")}</p>
        <Btn
          variant="primary"
          onClick={() => {
            setStep({ kind: "idle" })
            nav(tripId ? `/trips/${tripId}` : "/")
          }}
        >
          {t("guest.viewTrip")}
        </Btn>
      </Modal>
    )
  }
  return step.kind === "busy" ? <p role="status" className="h-sr-only">{t("guest.saving")}</p> : null
}
