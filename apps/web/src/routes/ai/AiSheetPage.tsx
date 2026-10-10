import { Navigate, useNavigate, useParams } from "react-router"
import { AiSheet, type SheetAction } from "../../components/ai"
import { useAuth } from "../auth/authStore"
import { TripOverview } from "../trips/TripOverview"

/** Where each sheet row goes. Result screens are `AiActionPage`; research and credits history (WF-132.3) still land on `ActionStub`. */
const TARGET: Record<SheetAction, string> = {
  agent: "agents",
  explain: "ai/explain",
  packing: "ai/packing",
  day: "ai/day",
  trip: "ai/trip",
  research: "ai/research",
}

/** `/trips/:id/ai`: the AI sheet (05 6.15) over the trip overview, so closing it returns to the trip. */
export function AiSheetPage() {
  const { token } = useAuth()
  const { id = "" } = useParams()
  const nav = useNavigate()
  if (!token) return <Navigate to="/welcome" replace />
  const base = `/trips/${encodeURIComponent(id)}`
  return (
    <>
      <TripOverview />
      <AiSheet tripId={id} onClose={() => nav(base, { replace: true })} onRun={(a) => void nav(`${base}/${TARGET[a]}`, { replace: true })} />
    </>
  )
}
