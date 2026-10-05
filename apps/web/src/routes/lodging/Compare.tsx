import { useEffect, useState } from "react"
import { Btn, Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { formatMoney } from "../../lib/money"
import { fetchCompare, type Compare as Data, type CompareRow } from "./api"

const PRICES = new Set(["price_per_night", "price_total"])
const LOW = new Set([...PRICES, "distance_to_center_km"])
const HIGH = new Set(["rating", "votes"])

const show = (row: CompareRow, v: CompareRow["values"][number] | string[], currency: string) => {
  if (Array.isArray(v)) return v.length ? v.join(", ") : t("stays.compareNone")
  if (v === null || v === "") return t("stays.compareNone")
  if (PRICES.has(row.key)) return formatMoney(Number(v), currency)
  if (row.key === "rating") return Number(v).toFixed(1)
  // the API label already says (km)
  return String(v)
}

/** The best cell of a row says so in words as well as a pattern (05 6.11: never color alone). Only rows whose numbers differ get one. */
function best(row: CompareRow, currency: string): { at: number; chip: string; said: string } | null {
  const low = LOW.has(row.key)
  if (!low && !HIGH.has(row.key)) return null
  const nums = row.values.map((v) => (typeof v === "number" ? v : null))
  const have = nums.filter((n): n is number => n !== null).sort((a, b) => a - b)
  if (have.length < 2 || have[0] === have[have.length - 1]) return null
  const pick = low ? have[0] : have[have.length - 1]
  const next = low ? have[1] : have[have.length - 2]
  const at = nums.indexOf(pick)
  const by = formatMoney(Math.abs(next - pick), currency)
  return {
    at,
    chip: t(low ? "stays.lowest" : "stays.highest"),
    said: PRICES.has(row.key) ? t("stays.cheaper", { amount: by }) : t("stays.best"),
  }
}

/** 05 6.11 compare: a real table, a sticky row-header column and horizontal scroll on phones. The API enforces 2 to 4 and the plan's cap. */
export function Compare({ tripId, ids, onBack }: { tripId: string; ids: string[]; onBack: () => void }) {
  const [data, setData] = useState<Data | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const key = ids.join(",")
  useEffect(() => {
    let live = true
    setData(null)
    setProblem(null)
    void fetchCompare(tripId, ids).then((r) => {
      if (!live) return
      if (r.ok) setData(r.data)
      else setProblem(r.reason === "limit" && r.detail ? r.detail : t("stays.compareError"))
    })
    return () => {
      live = false
    }
    // `key` stands for `ids`: the same picks in a new array must not reload.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId, key])
  const [head, ...rows] = data?.rows ?? []
  return (
    <div className="stays__compare">
      <Btn variant="text" onClick={onBack}>{t("stays.compareBack")}</Btn>
      {!data && !problem && <p className="h-soft" aria-live="polite">{t("stays.compareLoading")}</p>}
      {problem && (
        <p role="alert" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {problem}
        </p>
      )}
      {data && head && (
        <>
          <div className="stays__scroll">
            <table className="stays__table" aria-label={t("stays.compareTitle")}>
              <thead>
                <tr>
                  <th scope="col"><span className="h-sr-only">{head.label}</span></th>
                  {head.values.map((v, i) => (
                    <th key={data.columns[i]} scope="col">{String(v)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const b = best(row, data.home_currency)
                  return (
                    <tr key={row.key}>
                      <th scope="row">{row.label}</th>
                      {row.values.map((v, i) => (
                        <td key={data.columns[i]} className={b?.at === i ? "stays__best" : undefined}>
                          <span className="h-mono">{show(row, v, data.home_currency)}</span>
                          {b?.at === i && (
                            <>
                              <span className="h-chip">{b.chip}</span>
                              <span className="h-sr-only">{b.said}</span>
                            </>
                          )}
                        </td>
                      ))}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="h-soft">{t("stays.diffNote")}</p>
        </>
      )}
    </div>
  )
}
