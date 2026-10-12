import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useCallback, useEffect, useState } from "react"
import { Route, Routes, useParams } from "react-router"
import { EmptyState } from "../../components/EmptyState"
import { ErrorState } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Btn, Sprite, TextField } from "../../components/kit"
import { env } from "../../lib/env"
import { t } from "../../lib/i18n"
import { adminRequest, onSessionEnded, setDevAssertion } from "./adminClient"
import { AdminShell } from "./AdminShell"
import { Enrol } from "./Enrol"
import { NAV, canOpen } from "./nav"
import { fetchSession, SESSION_KEY, type AdminSession } from "./session"
import { SignInPanel } from "./SignInPanel"
import "./admin.css"

/** Present only in the admin chunk: the iOS build test looks for it to prove the chunk is gone (WF-058.3). */
export const ADMIN_CHUNK_MARKER = "hermi-admin-console"

const LOCAL_ENVS = ["local", "ci", "test"]

function Overview() {
  return (
    <>
      <h1 className="h-title">{t("admin.overview.title")}</h1>
      <p className="h-soft">{t("admin.overview.intro")}</p>
    </>
  )
}

/** A menu item whose screen is a later ticket. Gated by the same permission as the menu, so a typed address is too. */
function Section({ perms }: { perms: Record<string, string> }) {
  const { section = "" } = useParams()
  const item = NAV.find((i) => i.path === section)
  if (!item) return <ErrorState kind="notFound" message={t("states.page.notFound")} />
  if (!canOpen(perms, item.key)) {
    return (
      <EmptyState
        icon="lock"
        title={t("admin.forbidden.title")}
        body={t("admin.forbidden.body")}
        link={{ label: t("admin.forbidden.action"), href: "/admin" }}
      />
    )
  }
  return (
    <>
      <h1 className="h-title">{item.label}</h1>
      <EmptyState icon="compass" title={t("admin.soon.title")} body={t("admin.soon.body")} />
    </>
  )
}

function DevIdentity({ onSignedIn }: { onSignedIn: () => void }) {
  const [email, setEmail] = useState("admin@hermi.test")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const go = async () => {
    setBusy(true)
    setError(null)
    // The fake-Access signer exists only with ADMIN_AUTH_MODE=dev in local and ci (apps/api/hermi/main.py).
    const r = await adminRequest<{ assertion: string }>("POST", "/v1/dev/admin-session", { email: email.trim() })
    setBusy(false)
    if (r.ok) {
      setDevAssertion(r.data.assertion)
      onSignedIn()
    } else setError(r.offline ? t("states.error.offline") : t("admin.dev.failed"))
  }
  return (
    <main className="admin-center">
      <form
        className="admin-panel"
        onSubmit={(e) => {
          e.preventDefault()
          void go()
        }}
      >
        <h1 className="h-title">{t("admin.dev.title")}</h1>
        <p className="h-soft">{t("admin.dev.body")}</p>
        <TextField label={t("admin.dev.email")} type="email" autoComplete="off" value={email} error={error} onChange={(e) => setEmail(e.target.value)} />
        <Btn variant="primary" type="submit" busy={busy}>
          {t("admin.dev.action")}
        </Btn>
      </form>
    </main>
  )
}

const reload = () => window.location.reload()

/**
 * Everything a signed in admin sees sits behind this: the session read decides between the Access and identity
 * screens, enrolment, sign in and the shell. The 8 hour clock and any 401 send the admin back to sign in.
 */
function AdminGate() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: SESSION_KEY, queryFn: fetchSession, refetchOnWindowFocus: false })
  const [ended, setEnded] = useState(false)
  const [enrolling, setEnrolling] = useState(false)
  const [enrolDone, setEnrolDone] = useState(false)
  const refresh = useCallback(() => qc.invalidateQueries({ queryKey: SESSION_KEY }), [qc])

  const endSession = useCallback(() => {
    setEnded(true)
    void refresh()
  }, [refresh])
  useEffect(() => onSessionEnded(endSession), [endSession])

  const session = q.data?.ok ? q.data.data : null
  const expiresAt = session?.signed_in ? session.expires_at : null
  useEffect(() => {
    if (!expiresAt) return
    const wait = Math.min(Math.max(new Date(expiresAt).getTime() - Date.now(), 0), 2 ** 31 - 1)
    const id = setTimeout(endSession, wait)
    return () => clearTimeout(id)
  }, [expiresAt, endSession])

  // The recovery codes must outlive the session read that turns `mfa_enrolled` on (they are shown once).
  if (session && !session.admin.mfa_enrolled && !enrolling && !enrolDone) setEnrolling(true)

  if (q.isPending) {
    return (
      <main className="admin-center">
        <Skeleton shape="lines" onRetry={() => void q.refetch()} />
      </main>
    )
  }
  const r = q.data
  if (q.isError || !r) return <ErrorState kind="server" fullScreen onRetry={() => void q.refetch()} />
  if (!r.ok) {
    if (r.offline) return <ErrorState kind="offline" fullScreen onRetry={() => void q.refetch()} />
    if (r.status === 403 && r.code === "admin_not_enabled") {
      return (
        <main className="admin-center">
          <EmptyState icon="lock" title={t("admin.denied.title")} body={t("admin.denied.body")} action={{ label: t("admin.denied.action"), onClick: reload }} />
        </main>
      )
    }
    if (r.status === 401) {
      if (LOCAL_ENVS.includes(env.appEnv)) return <DevIdentity onSignedIn={() => void refresh()} />
      return (
        <main className="admin-center">
          <EmptyState icon="lock" title={t("admin.access.title")} body={t("admin.access.body")} action={{ label: t("admin.access.action"), onClick: reload }} />
        </main>
      )
    }
    return <ErrorState kind={r.status === 429 ? "rateLimited" : "server"} requestId={r.requestId} fullScreen onRetry={() => void q.refetch()} />
  }

  const s: AdminSession = r.data
  if (enrolling) {
    return (
      <Enrol
        session={s}
        onDone={() => {
          setEnrolling(false)
          setEnrolDone(true)
          void refresh()
        }}
      />
    )
  }
  if (!s.signed_in) {
    return (
      <SignInPanel
        session={s}
        ended={ended}
        onSignedIn={(next) => {
          setEnded(false)
          qc.setQueryData(SESSION_KEY, { ok: true, status: 200, data: next })
        }}
      />
    )
  }
  return (
    <AdminShell session={s}>
      <Routes>
        <Route index element={<Overview />} />
        <Route path=":section" element={<Section perms={s.permissions} />} />
      </Routes>
    </AdminShell>
  )
}

/** The `/admin/*` route group. Lazy loaded by `shell/routes.tsx`, and left out of the iOS build (08 2.1). */
export default function AdminRoutes() {
  return (
    <div data-console={ADMIN_CHUNK_MARKER}>
      <Sprite />
      <AdminGate />
    </div>
  )
}

