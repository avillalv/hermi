import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate, useParams } from "react-router"
import { Btn, Icon, Logo } from "../../components/kit"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { ApiError } from "../../lib/api/client"
import { t } from "../../lib/i18n"
import { queryClient } from "../../lib/queryClient"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { useAuth } from "../auth/authStore"
import { linkMe } from "../trips/people"
import type { Trip } from "../trips/api"
import { isOnboarded, useMe } from "../onboarding/trips"
import { acceptInvite, getPreview, pendingInvite } from "./collab"
import "../auth/auth.css"
import "../trips/trips.css"

/**
 * 05 6.8 recipient landing at /invite/:token. The preview is public, so the title shows with no sign-in. Join signs in
 * first when needed. shortcut: the preview has no trip dates, so the line reads "Sam invited you to Lisbon"; add the dates
 * when the preview returns them. The API answers 410 for expired, used and revoked alike, so all three show "no longer
 * valid" (the spec's expired line needs the API to tell them apart). "None of these" skips linking; Group adds a traveler.
 */
export function InviteLanding() {
  const { token = "" } = useParams()
  const auth = useAuth()
  const nav = useNavigate()
  const online = useOnline()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [joined, setJoined] = useState<{ trip: Trip; by: string } | null>(null)
  const q = useQuery(
    {
      queryKey: ["invite", token],
      retry: 1,
      queryFn: async () => {
        const r = await getPreview(token)
        if (r.response.status === 410 || r.response.status === 404) return null
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )
  useEffect(() => {
    if (q.data) track("invite_opened", { platform_before_install: "not_installed" })
  }, [q.data])
  // A signed-in person with no account yet goes through onboarding first; the pending invite stays until they join.
  const check = !!auth.token && !auth.persona && !isOnboarded()
  const me = useMe(auth.token, check)

  const go = (trip: Trip, by: string) => (pendingInvite.clear(), nav(`/trips/${trip.id}`, { replace: true, state: { addedBy: by } }))
  const join = async () => {
    if (!auth.token) {
      pendingInvite.set(token)
      return nav("/sign-in")
    }
    if (!q.data) return
    if (check && me.data === false) {
      pendingInvite.set(token)
      return nav("/onboarding")
    }
    setBusy(true)
    setError(null)
    const r = await acceptInvite(token)
    setBusy(false)
    if (!r.ok) {
      pendingInvite.clear()
      if (r.reason === "member" && r.tripId) return nav(`/trips/${r.tripId}`, { replace: true })
      return setError(t(r.reason === "gone" ? "invite.landing.invalid" : "invite.landing.joinFailed"))
    }
    // shortcut: minutes_to_accept_bucket is not sent, the API does not return when the invite was created. Add it when the preview returns created_at.
    track("invite_accepted", { role: q.data.role })
    const open = r.data.travelers.filter((p) => !p.linked_user_id)
    if (open.length > 0 && !r.data.travelers.some((p) => p.is_me)) setJoined({ trip: r.data, by: q.data.inviter_name })
    else go(r.data, q.data.inviter_name)
  }

  const pick = async (personId: string) => {
    if (!joined) return
    const r = await linkMe(joined.trip.id, personId)
    if (!r.ok) return setError(t("invite.landing.joinFailed"))
    track("traveler_linked")
    go(joined.trip, joined.by)
  }

  if (joined) {
    const open = joined.trip.travelers.filter((p) => !p.linked_user_id)
    return (
      <main className="auth">
        <div className="auth__panel">
          <p role="status" className="trips__note">{t("invite.landing.added", { name: joined.by })}</p>
          {error && (
            <p role="alert" className="h-input__error trips__note">
              <Icon name="circle-alert" size={16} />
              {error}
            </p>
          )}
          <div role="group" aria-label={t("group.which")} className="group__choose">
            <h1 className="h-title">{t("group.which")}</h1>
            {open.map((p) => (
              <Btn key={p.id} variant="secondary" onClick={() => void pick(p.id)}>
                {p.name}
              </Btn>
            ))}
            <Btn variant="text" onClick={() => go(joined.trip, joined.by)}>
              {t("invite.landing.none")}
            </Btn>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="auth">
      <div className="auth__panel">
        <div className="auth__brand">
          <Logo variant="lockup" height={56} />
        </div>
        {q.isPending && <Skeleton shape="block" onRetry={() => void q.refetch()} />}
        {q.isError && <QueryError error={q.error} message={t("invite.landing.error")} onRetry={() => void q.refetch()} />}
        {q.data === null && (
          <p role="alert" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("invite.landing.invalid")}
          </p>
        )}
        {q.data && (
          <>
            <h1 className="h-title">{t("invite.landing.title", { name: q.data.inviter_name, trip: q.data.trip_name })}</h1>
            <p className="h-soft">{t("invite.landing.role", { role: t(`group.role.${q.data.role}`).toLowerCase() })}</p>
            {!online && (
              <p role="status" className="h-input__error trips__note">
                <Icon name="circle-alert" size={16} />
                {t("invite.landing.offline")}
              </p>
            )}
            {error && (
              <p role="alert" className="h-input__error trips__note">
                <Icon name="circle-alert" size={16} />
                {error}
              </p>
            )}
            <Btn variant="primary" busy={busy} disabled={!online || (check && me.isPending)} onClick={() => void join()}>
              {t("invite.landing.join")}
            </Btn>
          </>
        )}
      </div>
    </main>
  )
}
