import { Link, useLocation, useNavigate } from "react-router"
import type { ErrorKind } from "../lib/api/client"
import { t } from "../lib/i18n"
import "./states.css"
import { Btn, Icon, LinkBtn } from "./kit"

const KINDS: ErrorKind[] = ["offline", "server", "notFound", "permission", "limit", "conflict", "unauthorized", "rateLimited", "maintenance", "forcedUpdate"]
export const ERROR_COPY = Object.fromEntries(KINDS.map((k) => [k, t(`states.error.${k}`)])) as Record<ErrorKind, string>

/** Back never traps: with no earlier page in this app it goes Home. */
function BackButton() {
  const navigate = useNavigate()
  // The first entry of this session has the key "default"; there is nothing earlier to go back to.
  const canGoBack = useLocation().key !== "default"
  return (
    <Btn variant="secondary" onClick={() => (canGoBack ? navigate(-1) : navigate("/"))}>
      {t("states.back")}
    </Btn>
  )
}

/**
 * Danger icon, what happened and how to fix it, a retry and a way out (05 4.17). `fullScreen` adds Back and Home and
 * needs a Router; inline does not. `message` replaces the default sentence (for example the credits renewal date).
 */
export function ErrorState({
  kind,
  message,
  requestId,
  retryAfter,
  onRetry,
  updateHref = "/",
  secondary,
  fullScreen,
}: {
  kind: ErrorKind
  message?: string
  requestId?: string
  retryAfter?: number
  onRetry?: () => void
  updateHref?: string
  /** A second way out, such as "Keep planning offline". */
  secondary?: { label: string; href: string }
  fullScreen?: boolean
}) {
  const wait = kind === "rateLimited" && retryAfter ? ` ${t("states.waitSeconds", { seconds: retryAfter })}` : ""
  return (
    <section role="alert" className={fullScreen ? "state state--error state--full" : "state state--error"}>
      <Icon name="circle-alert" size={48} className="state__icon" />
      <p className="state__body">{(message ?? ERROR_COPY[kind]) + wait}</p>
      {requestId && <p className="state__ref h-mono">{t("states.reference", { id: requestId })}</p>}
      <div className="state__actions">
        {kind === "unauthorized" && <LinkBtn variant="primary" href="/sign-in">{t("states.signIn")}</LinkBtn>}
        {kind === "forcedUpdate" && <LinkBtn variant="primary" href={updateHref}>{t("states.update")}</LinkBtn>}
        {onRetry && kind !== "forcedUpdate" && (
          <Btn variant={kind === "unauthorized" ? "secondary" : "primary"} onClick={onRetry}>{t("states.retry")}</Btn>
        )}
        {secondary && <a className="state__link" href={secondary.href}>{secondary.label}</a>}
        {fullScreen && (
          <div className="state__row">
            <BackButton />
            <Link className="state__link" to="/">{t("states.home")}</Link>
          </div>
        )}
      </div>
    </section>
  )
}
