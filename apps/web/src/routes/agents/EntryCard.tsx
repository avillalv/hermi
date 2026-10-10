import { useEffect, useRef } from "react"
import { Btn, TicketStub, TripTicket } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useTaster } from "./api"
import "./agents.css"

/**
 * 05 6.17 entry card. `free` is the taster: "Try a deep run, free once", with the chip "Free, one time" stated in text.
 * Once the taster is used it is the normal "Deep run, N credits" action.
 */
export function EntryCard({ free, price, onStart, disabled, busy }: { free: boolean; price: number; onStart: () => void; disabled?: boolean; busy?: boolean }) {
  const offered = useRef(false)
  useEffect(() => {
    if (free && !offered.current) {
      offered.current = true
      track("taster_offered")
    }
  }, [free])
  return (
    <TripTicket mod={["actions"]} role="group" aria-label={free ? t("agents.entryTitle") : t("agents.paidTitle", { credits: price })}>
      <div className="h-ticket__body agents__entry">
        <h2 className="h-heading">{free ? t("agents.entryTitle") : t("agents.paidTitle", { credits: price })}</h2>
        <p className="h-soft">{free ? t("agents.entryBody") : t("agents.paidBody", { credits: price })}</p>
      </div>
      <TicketStub>
        {free && <span className="h-chip">{t("agents.entryChip")}</span>}
        <Btn variant="primary" mod={["sm"]} disabled={disabled} busy={busy} onClick={onStart}>
          {free ? t("agents.entryStart") : t("agents.paidStart")}
        </Btn>
      </TicketStub>
    </TripTicket>
  )
}

/** The card on Flights: asks the API whether the taster is unused and opens the start screen. Renders nothing until it knows. */
export function AgentEntry({ enabled, onOpen, online }: { enabled: boolean; onOpen: () => void; online: boolean }) {
  const taster = useTaster(enabled)
  if (!taster.data) return null
  return <EntryCard free={taster.data.available} price={taster.data.credits || 40} onStart={onOpen} disabled={!online} />
}
