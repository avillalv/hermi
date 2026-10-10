import { t } from "../../lib/i18n"
import { Icon } from "../kit"
import "./ai.css"

type Props = {
  credits: number
  /** What the caller can spend now. A price above it makes the chip warn and say "You have N". */
  available?: number
  /** Served from the shared cache: the cheaper price, said in text. */
  fromCache?: boolean
  /** Free, like the one-time taster: no number. */
  free?: boolean
  /** Which pool pays first. The Trip Pass pool is named, your own credits are the default and stay unnamed. */
  payer?: "own" | "trip_pass"
}

/** The spoken form, for a button's accessible name: "costs 4 credits", "costs 40 credits. You have 12". */
export function creditsLabel({ credits, available, fromCache, free, payer }: Props): string {
  if (free) return t("ai.chip.freeLabel")
  const base = t(credits === 1 ? "ai.chip.costsOne" : "ai.chip.costs", { credits })
  const parts = [fromCache ? `${base}, ${t("ai.chip.fromCache")}` : base]
  if (available !== undefined && credits > available) parts.push(t("ai.chip.have", { available }))
  if (payer === "trip_pass") parts.push(t("ai.pool.tripPass"))
  return parts.join(". ")
}

/**
 * 05 4.11 credit cost chip: coin glyph, the number in mono, "credit" or "credits". Variants: cost, from shared cache,
 * insufficient (warning with "You have N"), and free. `payer` "trip_pass" adds the pool name under it.
 */
export function CreditChip({ credits, available, fromCache, free, payer }: Props) {
  const short = !free && available !== undefined && credits > available
  return (
    <>
      <span className={short ? "h-credit h-credit--warn" : "h-credit"}>
        <Icon name="coins" size={14} />
        {free ? (
          t("ai.chip.free")
        ) : (
          <>
            <span className="h-credit__n">{credits}</span> {t(credits === 1 ? "ai.chip.credit" : "ai.chip.credits")}
          </>
        )}
      </span>
      {fromCache && !free && <span className="h-action__desc h-action__desc--cache">{t("ai.chip.fromCache")}</span>}
      {short && <span className="h-action__note">{t("ai.chip.have", { available })}</span>}
      {payer === "trip_pass" && !free && <span className="ai-chip__pool">{t("ai.pool.tripPass")}</span>}
    </>
  )
}
