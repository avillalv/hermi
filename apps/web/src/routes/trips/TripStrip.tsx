import type { MouseEvent } from "react"
import type { useNavigate } from "react-router"
import { t } from "../../lib/i18n"
import type { Strip } from "../../shell/AppShell"

/** 05 5.2 section strip. shortcut: only the built sections (Overview, Flights, Stays, Plan, Group) show; Present joins as their tickets land. */
export function tripStrip(nav: ReturnType<typeof useNavigate>, id: string, active: "overview" | "group" | "flights" | "stays" | "plan"): Strip {
  const go = (href: string) => (e: MouseEvent) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return
    e.preventDefault()
    nav(href)
  }
  const base = `/trips/${encodeURIComponent(id)}`
  return {
    label: t("group.section"),
    active,
    tripId: id,
    items: [
      { key: "overview", label: t("group.overview"), href: base, onClick: go(base) },
      { key: "flights", label: t("flights.tab"), href: `${base}/flights`, onClick: go(`${base}/flights`) },
      { key: "stays", label: t("stays.tab"), href: `${base}/stays`, onClick: go(`${base}/stays`) },
      { key: "plan", label: t("plan.tab"), href: `${base}/plan`, onClick: go(`${base}/plan`) },
      { key: "group", label: t("group.group"), href: `${base}/group`, onClick: go(`${base}/group`) },
    ],
  }
}
