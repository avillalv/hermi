import { formatMoney } from "../../lib/money"
import { t } from "../../lib/i18n"
import { ageText, useGrid, type GridCell } from "./api"
import { shortDay } from "./PriceChart"

/** 05 6.9 date grid: leave dates down, return dates across, heat from the price rank and the price printed in every cell. */
export function DateGrid({ tripId, routeId }: { tripId: string; routeId: string }) {
  const q = useGrid(tripId, routeId, true)
  if (q.isPending) return <p className="h-soft">{t("flights.gridLoading")}</p>
  if (q.isError && !q.data)
    return (
      <p role="alert" className="h-soft">
        {t("flights.gridError")}
      </p>
    )
  const cells = q.data ?? []
  if (cells.length === 0) return <p className="h-soft">{t("flights.gridEmpty")}</p>
  const rows = [...new Set(cells.map((c) => c.depart_date))].sort()
  const cols = [...new Set(cells.map((c) => c.return_date ?? ""))].sort((a, b) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b)))
  const at = new Map<string, GridCell>(cells.map((c) => [`${c.depart_date}|${c.return_date ?? ""}`, c]))
  const oldest = cells.reduce((a, c) => (c.observed_at < a ? c.observed_at : a), cells[0]!.observed_at)
  const prices = cells.map((c) => c.price.amount_minor).sort((a, b) => a - b)
  const heat = (n: number) => 1 + Math.min(4, Math.floor((prices.indexOf(n) * 5) / prices.length)) // 1 cheapest, 5 dearest
  return (
    <div className="flights__gridwrap">
      <table className="flights__grid" aria-label={t("flights.gridTitle")}>
        <caption className="h-soft">{t("flights.gridAge", { tag: cells.every((c) => c.source === "travelpayouts") ? "Cached" : "Live", age: ageText(oldest) })}</caption>
        <thead>
          <tr>
            <th scope="col">{t("flights.gridDepart")}</th>
            {cols.map((c) => (
              <th key={c} scope="col">{c ? shortDay(c) : t("flights.oneWay")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <th scope="row">{shortDay(r)}</th>
              {cols.map((c) => {
                const cell = at.get(`${r}|${c}`)
                return cell ? (
                  <td key={c} className={`flights__heat flights__heat--${heat(cell.price.amount_minor)}`}>{formatMoney(cell.price.amount_minor, cell.price.currency)}</td>
                ) : (
                  <td key={c} />
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
