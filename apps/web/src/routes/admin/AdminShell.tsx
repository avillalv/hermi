import { useQueryClient } from "@tanstack/react-query"
import { useState, type ReactNode } from "react"
import { NavLink } from "react-router"
import { Btn } from "../../components/kit"
import { env } from "../../lib/env"
import { t } from "../../lib/i18n"
import { adminRequest } from "./adminClient"
import { GROUP_LABEL, visibleNav, type NavGroup } from "./nav"
import { SESSION_KEY, type AdminSession } from "./session"
import { StepUpDialog } from "./StepUpDialog"
import "./admin.css"

export type EnvTone = "production" | "staging" | "local"

/** 08 section 5: production is a thin route-a-ink bar, staging a sky bar; every other run reads as local. */
export function envLabel(appEnv: string): { label: string; tone: EnvTone } {
  if (appEnv === "production") return { label: t("admin.env.production"), tone: "production" }
  if (appEnv === "staging") return { label: t("admin.env.staging"), tone: "staging" }
  return { label: t("admin.env.local"), tone: "local" }
}

const GROUPS: NavGroup[] = ["monitor", "people", "money", "control", "audit"]

/** 08 6.1 and 7.1: the environment bar, a neutral "Hermi admin" header, the role-filtered menu and the page. */
export function AdminShell({ session, children }: { session: AdminSession; children: ReactNode }) {
  const qc = useQueryClient()
  const [leaving, setLeaving] = useState(false)
  const bar = envLabel(env.appEnv)
  const items = visibleNav(session.permissions)

  const signOut = async () => {
    setLeaving(true)
    await adminRequest("POST", "/v1/admin/auth/signout")
    setLeaving(false)
    await qc.invalidateQueries({ queryKey: SESSION_KEY })
  }

  return (
    <div className="admin">
      <div role="status" aria-label={t("admin.env.label")} className={`admin-env admin-env--${bar.tone}`}>
        {bar.label}
      </div>
      <header className="admin-header">
        <span className="h-heading admin-header__brand">{t("admin.brand")}</span>
        <span className="admin-header__who">
          <span>{session.admin.email}</span>
          <span className="admin-role h-mono">{session.admin.role}</span>
        </span>
        <Btn variant="secondary" mod={["sm"]} busy={leaving} onClick={() => void signOut()}>
          {t("admin.signOut")}
        </Btn>
      </header>
      <div className="admin-body">
        <nav className="admin-nav" aria-label={t("admin.nav")}>
          {GROUPS.map((g) => {
            const inGroup = items.filter((i) => i.group === g)
            return inGroup.length === 0 ? null : (
              <section key={g} className="admin-nav__group" aria-label={GROUP_LABEL[g]}>
                <h2 className="h-label">{GROUP_LABEL[g]}</h2>
                <ul>
                  {inGroup.map((i) => (
                    <li key={i.key}>
                      <NavLink to={i.path === "" ? "/admin" : `/admin/${i.path}`} end className="admin-nav__link">
                        {i.label}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </section>
            )
          })}
        </nav>
        <main className="admin-main">{children}</main>
      </div>
      <StepUpDialog factors={session.factors} />
    </div>
  )
}
