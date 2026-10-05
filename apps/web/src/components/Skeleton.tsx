import { Fragment, useEffect, useState, type ReactNode } from "react"
import { t } from "../lib/i18n"
import { ErrorState } from "./ErrorState"
import "./states.css"

export type SkeletonShape = "lines" | "block" | "tripCard" | "dayCard" | "routeCard" | "stayCard" | "overview"

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
  // Trip overview (05 6.7): the header pass, then five cards.
  overview: () => (
    <>
      <span className="state-skel state-skel--block" />
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="state-card"><div className="state-card__main"><Lines n={2} /></div></div>
      ))}
    </>
  ),
  // Stays card: a photo block, lines and a price stub.
  stayCard: () => (
    <div className="state-card">
      <span className="state-skel state-skel--photo" />
      <div className="state-card__main"><Lines n={3} /></div>
      <span className="state-skel state-skel--stub" />
    </div>
  ),
  // Flights route card: a title, a chip row and the chart frame with its axes.
  routeCard: () => (
    <div className="state-card state-card--day state-card--route">
      <span className="state-skel state-skel--line" />
      <span className="state-skel state-skel--chips" />
      <span className="state-skel state-skel--block state-skel--chart" />
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
  count = 1,
  delayMs = 150,
  timeoutMs = 8000,
  onRetry,
}: {
  shape: SkeletonShape
  /** Repeats the shape inside the one status region. */
  count?: number
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
      {Array.from({ length: count }, (_, i) => <Fragment key={i}>{SHAPES[shape]()}</Fragment>)}
    </div>
  )
}
