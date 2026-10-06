import { SourceChip } from "../../components/SourceChip"
import { Icon } from "../../components/kit"
import { formatDateRange } from "../../lib/dates"
import { t } from "../../lib/i18n"
import { formatMoney } from "../../lib/money"
import type { Sample } from "./api"

const dated = (iso: string) => formatDateRange(iso.slice(0, 10), iso.slice(0, 10))

/** The read-only plan of 05 6.35: days and items, then the stay shortlist. Every price and fact carries its date. Never flights. */
export function SampleBody({ sample }: { sample: Sample }) {
  const { days, stays } = sample.presentation
  const seen = dated(sample.updated_at)
  return (
    <div className="discover__plan">
      {days.map((d) => (
        <section key={d.day} className="discover__day" aria-labelledby={`day-${d.day}`}>
          <h2 className="h-heading h-heading--section" id={`day-${d.day}`}>
            {[formatDateRange(d.day, d.day), d.title].filter(Boolean).join(", ")}
          </h2>
          <ul className="discover__items">
            {d.items.map((i) => (
              <li key={i.id} className="discover__item">
                <span className="h-field__value">{i.start_time?.slice(0, 5) ?? ""}</span>
                <span className="discover__item-text">
                  <strong>{i.title}</strong>
                  {i.location_name && <span className="h-soft">{i.location_name}</span>}
                  {i.estimated_cost_minor !== null && i.cost_currency && (
                    <span className="h-soft">{t("discover.examplePrice", { price: formatMoney(i.estimated_cost_minor, i.cost_currency), date: seen })}</span>
                  )}
                  {i.check_url && <SourceChip url={i.check_url} checkedAt={i.checked_at} agent={false} />}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {stays.length > 0 && (
        <section className="discover__day" aria-labelledby="sample-stays">
          <h2 className="h-heading h-heading--section" id="sample-stays">
            {t("discover.stays")}
          </h2>
          <ul className="discover__items">
            {stays.map((s) => (
              <li key={s.id} className="discover__item">
                <Icon name="bed" size={20} />
                <span className="discover__item-text">
                  <strong>{s.title}</strong>
                  {s.price_total_minor !== null && s.currency && (
                    <span className="h-soft">{t("discover.examplePrice", { price: formatMoney(s.price_total_minor, s.currency), date: seen })}</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
