import { useParams } from "react-router"
import { NotFound } from "../errors"
import { DraftDay, DraftTrip } from "./Draft"
import { Explain } from "./Explain"
import { Packing } from "./Packing"
import { Research } from "./Research"

/** `/trips/:id/ai/:action`: the result screen of one AI action. */
export function AiActionPage() {
  const { action = "" } = useParams()
  if (action === "explain") return <Explain />
  if (action === "packing") return <Packing />
  if (action === "day") return <DraftDay />
  if (action === "trip") return <DraftTrip />
  if (action === "research") return <Research />
  return <NotFound />
}
