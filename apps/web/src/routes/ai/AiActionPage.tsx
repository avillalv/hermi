import { useParams } from "react-router"
import { ActionStub } from "./ActionStub"
import { DraftDay, DraftTrip } from "./Draft"
import { Explain } from "./Explain"
import { Packing } from "./Packing"

/** `/trips/:id/ai/:action`: the result screen of one AI action. Research (WF-132.3) still lands on the stub. */
export function AiActionPage() {
  const { action = "" } = useParams()
  if (action === "explain") return <Explain />
  if (action === "packing") return <Packing />
  if (action === "day") return <DraftDay />
  if (action === "trip") return <DraftTrip />
  return <ActionStub />
}
