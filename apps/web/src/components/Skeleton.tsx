import { useEffect, useState, type ReactNode } from "react"
import { t } from "../lib/i18n"
import { ErrorState } from "./ErrorState"
import "./states.css"

export type SkeletonShape = "lines" | "block" | "tripCard" | "dayCard"

const Lines = ({ n }: { n: number }) => (
  <>
    {Array.from({ length: n }, (_, i) => (
      <span key={i} className="state-skel state-skel--line" />
    ))}
  </>
)

const SHAPES: Record<SkeletonShape, () => ReactNode> = {
  lines: () => <Lines n={3} />,
  block: () => <span className="state-skel state-skel--block" />,
  // Ticket body plus its stub, like the final trip card.
  tripCard: () => (
    <div className="state-card">
      <div className="state-card__main"><Lines n={3} /></div>
      <span className="state-skel state-skel--stub" />
    </div>
  ),
  // Day card: a heading line and three rows.
  dayCard: () => (
    <div className="state-card state-card--day">
      <span className="state-skel state-skel--line" />
      <Lines n={3} />
    </div>
  ),
}

/**
 * Content placeholder (05 4.18): nothing for `delayMs` (150), then the shape with a shimmer (static under reduced
 * motion), and after `timeoutMs` (8000) the error state. Never a spinner.
 */
export function Skeleton({
  shape,
  delayMs = 150,
  timeoutMs = 8000,
  onRetry,
}: {
  shape: SkeletonShape
  delayMs?: number
  timeoutMs?: number
  onRetry?: () => void
}) {
  const [phase, setPhase] = useState<"wait" | "show" | "failed">("wait")
  useEffect(() => {
    const show = setTimeout(() => setPhase("show"), delayMs)
    const fail = setTimeout(() => setPhase("failed"), timeoutMs)
    return () => {
      clearTimeout(show)
      clearTimeout(fail)
    }
  }, [delayMs, timeoutMs])
  if (phase === "failed") return <ErrorState kind={navigator.onLine ? "server" : "offline"} onRetry={onRetry} />
  if (phase === "wait") return null
  return (
    <div role="status" aria-label={t("states.loading")} aria-busy="true" className="state-skel-wrap">
      {SHAPES[shape]()}
    </div>
  )
}
