import { formatMoney } from "../../lib/money"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { useHistory, type PriceHistory } from "./api"

const W = 334
const H = 52
const LEFT = 44
const day = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })
export const shortDay = (iso: string) => day.format(new Date(`${iso}T00:00:00Z`))

/** Daily minimum across sources, oldest first. */
function daily(h: PriceHistory) {
  const m = new Map<string, number>()
  for (const p of h.points) m.set(p.day, Math.min(m.get(p.day) ?? Infinity, p.price.amount_minor))
  return [...m].sort(([a], [b]) => a.localeCompare(b)).map(([d, minor]) => ({ day: d, minor }))
}

/** 05 4.6 price chart: the kit's static plot (`.h-chart`), a text summary and a hidden data table. shortcut: no Recharts, scrubber or pinned points yet; add them with the fare detail screen. */
export function PriceChart({ tripId, routeId }: { tripId: string; routeId: string }) {
  const q = useHistory(tripId, routeId)
  const online = useOnline()
  const body = () => {
    if (q.isPending) return <div className="flights__chartskel" aria-hidden="true" />
    if (q.isError && !q.data)
      return (
        <p role="alert" className="h-soft">
          {t("flights.chartError")}
        </p>
      )
    const pts = daily(q.data!)
    if (pts.length === 0) return <p className="h-soft">{t("flights.chartEmpty")}</p>
    if (pts.length === 1) return <p className="h-soft">{t("flights.chartOne")}</p>
    const cur = q.data!.currency
    const money = (n: number) => formatMoney(n, cur)
    const lo = Math.min(...pts.map((p) => p.minor))
    const hi = Math.max(...pts.map((p) => p.minor))
    const span = Math.max(1, hi - lo)
    const x = (i: number) => LEFT + (i * (W - LEFT - 8)) / (pts.length - 1)
    const y = (n: number) => 9 + ((hi - n) * 28) / span
    const first = pts[0]!
    const last = pts[pts.length - 1]!
    const lowest = pts.reduce((a, p) => (p.minor < a.minor ? p : a))
    const prev = pts[pts.length - 2]!
    const delta = last.minor - prev.minor
    const series = q.data!.points.some((p) => p.source !== "travelpayouts") ? "live" : "cached"
    const summary = t("flights.chartSummary", { low: money(lowest.minor), lowDay: shortDay(lowest.day), now: money(last.minor) })
    return (
      <>
        {delta !== 0 && <p className="h-soft">{t(delta < 0 ? "flights.fell" : "flights.rose", { amount: money(Math.abs(delta)), day: shortDay(prev.day) })}</p>}
        <p className="h-soft">{summary}</p>
        <svg className="h-chart__plot" role="img" aria-label={summary} viewBox={`0 0 ${W} ${H}`}>
          <line className="h-chart__grid" x1={LEFT} y1="9" x2={W - 8} y2="9" />
          <line className="h-chart__grid" x1={LEFT} y1="37" x2={W - 8} y2="37" />
          <text className="h-chart__axis" x="0" y="13">{formatMoney(hi, cur, true)}</text>
          <text className="h-chart__axis" x="0" y="41">{formatMoney(lo, cur, true)}</text>
          <polyline className={`h-chart__line h-chart__line--${series}`} points={pts.map((p, i) => `${x(i).toFixed(1)},${y(p.minor).toFixed(1)}`).join(" ")} />
          <circle className={`h-chart__dot h-chart__dot--${series}`} cx={x(pts.length - 1)} cy={y(last.minor)} r="4.5" />
          <text className="h-chart__axis" x={LEFT} y="50">{shortDay(first.day)}</text>
          <text className="h-chart__axis" x={W - 8} y="50" textAnchor="end">{shortDay(last.day)}</text>
        </svg>
        <table className="h-sr-only" aria-label={t("flights.chartData")}>
          <thead>
            <tr>
              <th scope="col">{t("flights.colDay")}</th>
              <th scope="col">{t("flights.colPrice")}</th>
            </tr>
          </thead>
          <tbody>
            {pts.map((p) => (
              <tr key={p.day}>
                <th scope="row">{shortDay(p.day)}</th>
                <td>{money(p.minor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!online && <p className="h-soft">{t("flights.offline")}</p>}
      </>
    )
  }
  return (
    <section className="h-chart" aria-label={t("flights.chartTitle")}>
      <div className="h-chart__head">
        <h3 className="h-label h-chart__title">{t("flights.chartTitle")}</h3>
        <span className="h-chart__legend">
          <span className="h-chart__swatch h-chart__swatch--cached" />
          {t("flights.cached")}
        </span>
      </div>
      {body()}
    </section>
  )
}
