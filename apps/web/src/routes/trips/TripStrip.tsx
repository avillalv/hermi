import type { MouseEvent } from "react"
import type { useNavigate } from "react-router"
import { t } from "../../lib/i18n"
import type { Strip } from "../../shell/AppShell"

/** 05 5.2 section strip. shortcut: only the built sections (Overview, Group) show; Flights, Stays, Plan and Present join as their tickets land. */
export function tripStrip(nav: ReturnType<typeof useNavigate>, id: string, active: "overview" | "group"): Strip {
  const go = (href: string) => (e: MouseEvent) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return
    e.preventDefault()
    nav(href)
  }
  const base = `/trips/${encodeURIComponent(id)}`
  return {
    label: t("group.section"),
    active,
    items: [
      { key: "overview", label: t("group.overview"), href: base, onClick: go(base) },
      { key: "group", label: t("group.group"), href: `${base}/group`, onClick: go(`${base}/group`) },
    ],
  }
}
