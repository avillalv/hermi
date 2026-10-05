import { useQueries } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { Link } from "react-router"
import { Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { queryClient } from "../../lib/queryClient"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { api } from "../auth/api"
import { useAuth } from "../auth/authStore"
import { useTrips } from "../onboarding/trips"
import "../trips/trips.css"
import "./activity.css"

// shortcut: hand-written from apps/api/hermi/modules/activity until gen:api is real.
type Entry = { verb: string; entity_type: string; entity_id: string | null; summary: string; at: string; actor: { id: string | null; display_name: string } }
type Row = Entry & { tripId: string; tripName: string }

const FILTERS = ["all", "alerts", "group", "ai"] as const
type Filter = (typeof FILTERS)[number]

/** Poll so an edit by another member shows within 30 seconds (WF-027 Accept). */
const POLL_MS = 15_000

const dayKey = (iso: string) => new Date(iso).toDateString()
function dayLabel(iso: string) {
  const d = new Date(iso)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return t("activity.today")
  if (d.toDateString() === new Date(today.getTime() - 86_400_000).toDateString()) return t("activity.yesterday")
  return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })
}

/** 05 6.24 (partial): per-trip feeds merged into one list by day. shortcut: no unread dots, swipe, mark read or undo until the server tracks read state; Alerts and AI are empty until those sources land. */
export function Activity() {
  const { token } = useAuth()
  const online = useOnline()
  const [filter, setFilter] = useState<Filter>("all")
  const trips = useTrips(!!token)
  const feeds = useQueries(
    {
      queries: (trips.data ?? []).map((tr) => ({
        queryKey: ["activity", tr.id],
        refetchInterval: POLL_MS,
        queryFn: async () => {
          const r = await api.get<{ items: Entry[] }>(`/v1/trips/${encodeURIComponent(tr.id)}/activity?limit=20`)
          if (r.error !== undefined || !r.data) throw new Error(`activity ${r.response.status}`)
          return r.data.items.map((e): Row => ({ ...e, tripId: tr.id, tripName: tr.name }))
        },
      })),
    },
    queryClient,
  )
  useEffect(() => {
    // shortcut: no unread count until the server tracks read state, so the bucket is always none.
    if (token) track("activity_viewed", { unread_bucket: "none" })
  }, [token])

  const pending = trips.isPending || feeds.some((f) => f.isPending)
  const retry = () => {
    if (trips.isError) void trips.refetch()
    feeds.forEach((f) => f.isError && void f.refetch())
  }
  const all = feeds.flatMap((f) => f.data ?? [])
  const rows = filter === "alerts" || filter === "ai" ? [] : all.sort((a, b) => Date.parse(b.at) - Date.parse(a.at))
  const failed = rows.length === 0 ? trips.isError || feeds.some((f) => f.isError && !f.data) : false
  const staleError = rows.length > 0 && feeds.some((f) => f.isError)
  const days: { key: string; label: string; rows: Row[] }[] = []
  for (const r of rows) {
    const k = dayKey(r.at)
    const last = days[days.length - 1]
    if (last?.key === k) last.rows.push(r)
    else days.push({ key: k, label: dayLabel(r.at), rows: [r] })
  }

  return (
    <AppShell active="activity">
      <h1 className="h-title">{t("activity.title")}</h1>
      {!token && (
        <section className="trips__empty">
          <p className="h-soft">{t("activity.guest")}</p>
          <Link to="/sign-in" className="h-btn h-btn--primary">
            {t("activity.signIn")}
          </Link>
        </section>
      )}
      {token && !online && (
        <p role="status" className="h-input__error trips__note">
          <Icon name="circle-alert" size={16} />
          {t("activity.offline")}
        </p>
      )}
      {token && (
        <>
          <div className="h-seg activity__filters" role="tablist" aria-label={t("activity.filters")}>
            {FILTERS.map((f) => (
              <button key={f} type="button" role="tab" className="h-seg__item" aria-selected={filter === f} onClick={() => setFilter(f)}>
                {t(`activity.${f}`)}
              </button>
            ))}
          </div>
          {pending && online && (
            <>
              <p className="h-soft" aria-live="polite">
                {t("activity.loading")}
              </p>
              <div className="trips__list trips__section">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="trips__skel group__skel" aria-hidden="true" />
                ))}
              </div>
            </>
          )}
          {staleError && (
            <p role="alert" className="h-input__error trips__note">
              <Icon name="circle-alert" size={16} />
              {t("activity.error")}{" "}
              <button type="button" className="h-btn h-btn--secondary" onClick={retry}>
                {t("trips.retry")}
              </button>
            </p>
          )}
          {!pending && failed && (
            <div className="trips__stack">
              <p role="alert" className="h-input__error trips__note">
                <Icon name="circle-alert" size={16} />
                {t("activity.error")}
              </p>
              <button type="button" className="h-btn h-btn--secondary" onClick={retry}>
                {t("trips.retry")}
              </button>
            </div>
          )}
          {!pending && !failed && rows.length === 0 && (
            <section className="trips__empty">
              <h2 className="h-heading">{t("activity.emptyTitle")}</h2>
              <p className="h-soft">{t("activity.emptyBody")}</p>
            </section>
          )}
          {!pending && !failed && rows.length > 0 && (
            <ul className="activity__list" aria-label={t("activity.title")}>
              {days.map((d) => (
                <li key={d.key} className="trips__section">
                  <h2 className="h-label">{d.label}</h2>
                  <ul className="h-listcard activity__rows">
                    {d.rows.map((r, i) => (
                      <li key={`${r.tripId}-${r.entity_id}-${r.at}-${i}`}>
                        <Link
                          className="h-listcard__row activity__row"
                          to={r.entity_type === "member" ? `/trips/${r.tripId}/group` : `/trips/${r.tripId}`}
                          onClick={() => track("activity_item_opened", { kind: "change" })}
                        >
                          <span className="h-listcard__text">
                            {r.actor.display_name} {r.summary}
                          </span>
                          <span className="h-soft">
                            {r.tripName}, <time dateTime={r.at}>{new Date(r.at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}</time>
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </AppShell>
  )
}
