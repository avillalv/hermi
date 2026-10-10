import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Btn, Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { createGuestTripFromSample } from "../../features/guest/store"
import { useAuth } from "../auth/authStore"
import { copySample, useSample } from "./api"
import { SampleBody } from "./SampleBody"
import { ThirdTripSheet } from "./ThirdTripSheet"
import "./discover.css"

/** 05 6.23 and 6.35: a sample opened read-only, with the one "Use this plan" button. A guest builds the local guest trip, with no server write. */
export function SampleView() {
  const { slug } = useParams()
  const nav = useNavigate()
  const { token } = useAuth()
  const online = useOnline()
  const q = useSample(slug)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const [paywall, setPaywall] = useState(false)
  useEffect(() => {
    if (slug) track("sample_trip_opened", { slug })
  }, [slug])

  const use = async () => {
    if (!slug || !q.data || busy) return
    setNote(null)
    if (!token) {
      if (!createGuestTripFromSample(q.data)) return setNote(t("discover.guestLimit"))
      track("sample_trip_copied", { slug, was_guest: true }) // the server sends the signed-in event itself
      return nav("/guest-trip")
    }
    setBusy(true)
    const r = await copySample(slug)
    setBusy(false)
    if (r.ok) {
      return nav(`/trips/${r.trip.id}`)
    }
    if (r.reason === "limit") setPaywall(true)
    else setNote(t("discover.copyFailed"))
  }

  return (
    <AppShell active="discover">
      <Link to="/discover" className="h-btn h-btn--text discover__back">
        <Icon name="chevron-left" size={20} />
        {t("discover.back")}
      </Link>
      {q.isPending && <Skeleton shape="overview" onRetry={() => void q.refetch()} />}
      {q.isError && <QueryError error={q.error} message={t("discover.sampleError")} onRetry={() => void q.refetch()} />}
      {q.data && (
        <>
          <p role="note" className="discover__banner">
            {t("discover.banner")}
          </p>
          <h1 className="h-pagehead__title">{q.data.title}</h1>
          <p className="h-soft">{q.data.summary}</p>
          <SampleBody sample={q.data} />
          <div className="discover__cta">
            {!online && !!token && (
              <p role="status" className="h-input__error">
                {t("discover.offline")}
              </p>
            )}
            {note && (
              <p role="alert" className="h-input__error">
                {note}
              </p>
            )}
            <Btn variant="primary" busy={busy} disabled={!online && !!token} onClick={() => void use()}>
              {t("discover.use")}
            </Btn>
          </div>
        </>
      )}
      {paywall && <ThirdTripSheet onClose={() => setPaywall(false)} />}
    </AppShell>
  )
}
