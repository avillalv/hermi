import { useEffect } from "react"
import { Link, useSearchParams } from "react-router"
import { EmptyState } from "../../components/EmptyState"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Field, Icon, TicketStub, TripTicket } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { AppShell } from "../../shell/AppShell"
import { useSamples } from "./api"
import "../trips/trips.css"
import "./discover.css"

const TAGS = ["beach", "city", "mountains", "food"] as const

/** 05 6.23: a fixed gallery of sample trips written by the Hermi team. No search, no partner cards, no ranking. Works signed out. */
export function Discover() {
  const [params, setParams] = useSearchParams()
  const tag = TAGS.find((x) => x === params.get("tag"))
  const q = useSamples(tag)
  useEffect(() => void track("discover_viewed"), [])
  const retry = () => void q.refetch()
  return (
    <AppShell active="discover">
      <header className="h-pagehead">
        <div className="h-pagehead__text">
          <h1 className="h-pagehead__title">{t("discover.title")}</h1>
        </div>
      </header>
      <p className="h-soft">{t("discover.lead")}</p>
      <div role="group" className="discover__chips" aria-label={t("discover.filters")}>
        {[undefined, ...TAGS].map((k) => (
          <button key={k ?? "all"} type="button" className="h-daychip" aria-pressed={k === tag} onClick={() => setParams(k ? { tag: k } : {})}>
            {k ? t(`discover.tags.${k}`) : t("discover.all")}
          </button>
        ))}
      </div>
      {q.isPending && <Skeleton shape="tripCard" count={3} onRetry={retry} />}
      {q.isError && <QueryError error={q.error} message={t("discover.error")} onRetry={retry} />}
      {q.data?.length === 0 && <EmptyState icon="compass" title={t("discover.emptyTitle")} body={t("discover.emptyBody")} action={{ label: t("discover.tryAgain"), onClick: retry }} />}
      {!!q.data?.length && (
        <ul className="trips__list discover__grid">
          {q.data.map((s) => (
            <li key={s.slug} className="trips__item">
              <TripTicket as={Link} to={`/discover/${s.slug}`} aria-label={t("discover.cardLabel", { title: s.title, destination: s.destination_name, days: s.days, suits: s.suits })}>
                <div className="h-ticket__body h-ticket__body--split">
                  <div className="h-ticket__id">
                    <h2 className="h-ticket__name">{s.title}</h2>
                    <span className="h-ticket__dates">{s.destination_name}</span>
                    <span className="h-soft">{s.suits}</span>
                  </div>
                  <dl className="h-ticket__fields">
                    <Field label={t("discover.days")}>{s.days}</Field>
                  </dl>
                </div>
                <TicketStub>
                  <span className="h-chip">{t("discover.sampleChip")}</span>
                  <Icon name="chevron-right" size={20} className="h-ticket__go" />
                </TicketStub>
              </TripTicket>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  )
}
