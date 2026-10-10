import { Link, Navigate } from "react-router"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { useCredits, useLedger, type Credits as Balance, type LedgerEntry } from "../../components/ai"
import { Btn, Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { useTrip } from "../trips/api"
import "../../components/ai/ai.css"

const date = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
const ACTIONS = ["explain", "live_search", "draft_day", "draft_trip", "research", "agent_run", "verify_plan"]
const actionName = (a: string | null) => t(a && ACTIONS.includes(a) ? `ai.credits.action.${a}` : "ai.credits.unknown")

/** One ledger row in words. A settle row moves nothing (the reserve and refund rows carry the numbers) and is not listed. */
function label(e: LedgerEntry): string {
  switch (e.kind) {
    case "grant":
      return t("ai.credits.grant")
    case "refund":
      return t(e.delta === 1 ? "ai.credits.refundOne" : "ai.credits.refund", { credits: e.delta })
    case "expire":
      return t("ai.credits.expire")
    case "clawback":
      return t("ai.credits.clawback")
    case "adjust":
      return t("ai.credits.adjust")
    default:
      return actionName(e.action)
  }
}
const signed = (n: number) => (n > 0 ? `+${n}` : `${n}`)
const spoken = (n: number) => (n > 0 ? t(n === 1 ? "ai.credits.plusOne" : "ai.credits.plusN", { n }) : t(n === -1 ? "ai.credits.minusOne" : "ai.credits.minusN", { n: -n }))

/** Rows with a key that survives paging: the row's own fields, plus a count for exact twins. The API never exposes the bigint id. */
function keyed(items: LedgerEntry[]) {
  const seen = new Map<string, number>()
  return items.map((e) => {
    const base = `${e.at}|${e.kind}|${e.reservation_id ?? ""}|${e.delta}`
    const n = seen.get(base) ?? 0
    seen.set(base, n + 1)
    return { e, key: `${base}#${n}` }
  })
}

/** A Trip Pass pool: pass credits are a trip pool, not part of the person's own balance (05 6.26). */
function PassLine({ tripId, credits }: { tripId: string; credits: number }) {
  const { token } = useAuth()
  const trip = useTrip(tripId, !!token)
  return <p className="h-soft">{t("ai.credits.tripPassPool", { trip: trip.data?.name ?? t("ai.credits.thisTrip"), credits })}</p>
}

function Pools({ c }: { c: Balance }) {
  const grants = c.grants ?? []
  const promo = grants.filter((g) => g.kind === "promo")
  const bought = grants.filter((g) => g.kind === "purchase")
  const passes = grants.filter((g) => g.kind === "trip_pass" && g.trip_id)
  const adjust = grants.filter((g) => g.kind === "adjustment").reduce((n, g) => n + g.remaining, 0)
  const own = c.total - c.trip_pass
  // Without grant rows (an older API), what is left over is shown as one line.
  const other = grants.length ? adjust : Math.max(0, own - c.monthly - c.purchased)
  return (
    <>
      <p className="h-soft">
        {c.next_monthly_grant_at
          ? t("ai.credits.monthlyRenew", { credits: c.monthly, date: date(c.next_monthly_grant_at) })
          : t("ai.credits.monthly", { credits: c.monthly })}
      </p>
      {promo.map((g, i) => (
        <p key={`promo-${g.expires_at ?? i}-${g.remaining}`} className="h-soft">
          {g.expires_at ? t("ai.credits.promo", { credits: g.remaining, date: date(g.expires_at) }) : t("ai.credits.promoNoDate", { credits: g.remaining })}
        </p>
      ))}
      {bought.length > 0
        ? bought.map((g, i) => (
            <p key={`bought-${g.expires_at ?? i}-${g.remaining}`} className="h-soft">
              {g.expires_at ? t("ai.credits.boughtUntil", { credits: g.remaining, date: date(g.expires_at) }) : t("ai.credits.bought", { credits: g.remaining })}
            </p>
          ))
        : c.purchased > 0 && <p className="h-soft">{t("ai.credits.bought", { credits: c.purchased })}</p>}
      {other > 0 && <p className="h-soft">{t("ai.credits.other", { credits: other })}</p>}
      {passes.map((g) => (
        <PassLine key={g.trip_id} tripId={g.trip_id!} credits={g.remaining} />
      ))}
    </>
  )
}

/**
 * 05 6.26 Plan and credits, the credits part only: the balance by pool and the History list. Plans, purchase and
 * restore are the subscription screen (WF-094); nothing can be bought on web, so the note names the iOS app.
 */
export function Credits() {
  const { token } = useAuth()
  const online = useOnline()
  const bal = useCredits(null, !!token)
  const ledger = useLedger(!!token)
  if (!token) return <Navigate to="/welcome" replace />
  const c = bal.data
  const rows = keyed((ledger.data?.pages.flatMap((p) => p.items) ?? []).filter((e) => e.kind !== "settle"))
  return (
    <AppShell active="account">
      <div className="overview ai-screen">
        <Link className="h-btn h-btn--text h-btn--sm" to="/account">
          <Icon name="chevron-left" size={16} />
          {t("ai.credits.back")}
        </Link>
        <h1 className="h-title">{t("ai.credits.title")}</h1>
        {!online && (
          <p role="status" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {t("ai.credits.offline")}
          </p>
        )}
        {bal.isPending && online && <Skeleton shape="lines" />}
        {bal.isError && online && <QueryError error={bal.error} message={t("ai.credits.balanceError")} onRetry={() => void bal.refetch()} />}
        {c && (
          <section className="ai-result" aria-labelledby="ai-balance-h">
            <h2 className="h-title" id="ai-balance-h">
              {t(c.total - c.trip_pass === 1 ? "ai.credits.leftOne" : "ai.credits.left", { credits: c.total - c.trip_pass })}
            </h2>
            <Pools c={c} />
            <p className="h-soft">{t("ai.credits.iosOnly")}</p>
          </section>
        )}
        <section className="ai-result" aria-labelledby="ai-history-h">
          <h2 className="h-label" id="ai-history-h">
            {t("ai.credits.history")}
          </h2>
          {ledger.isPending && online && <Skeleton shape="lines" />}
          {ledger.isError && online && <QueryError error={ledger.error} message={t("ai.credits.error")} onRetry={() => void ledger.refetch()} />}
          {ledger.data && rows.length === 0 && !ledger.hasNextPage && <p className="h-soft">{t("ai.credits.empty")}</p>}
          {rows.length > 0 && (
            <ul className="ai-ledger" aria-label={t("ai.credits.list")}>
              {rows.map(({ e, key }) => (
                <li key={key} className="ai-ledger__row">
                  <span className="ai-ledger__what">
                    <span>{label(e)}</span>
                    <span className="h-soft">{date(e.at)}</span>
                  </span>
                  <span className="h-num" aria-label={spoken(e.delta)}>
                    {signed(e.delta)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {ledger.hasNextPage && (
            <Btn variant="secondary" busy={ledger.isFetchingNextPage} disabled={!online} onClick={() => void ledger.fetchNextPage()}>
              {t("ai.credits.more")}
            </Btn>
          )}
        </section>
      </div>
    </AppShell>
  )
}
