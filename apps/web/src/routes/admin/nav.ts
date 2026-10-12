export type NavGroup = "monitor" | "people" | "money" | "control" | "audit"
export type NavItem = { key: string; path: string; label: string; group: NavGroup; permission: string }

/**
 * The console menu (08 section 5) and the permission that opens each item (08 section 3, `admin/permissions.py`).
 * An item shows when the session's permission map holds the name at any level above `-`; the API still enforces it.
 */
export const NAV: NavItem[] = [
  { key: "overview", path: "", label: "Overview", group: "monitor", permission: "overview.read" },
  { key: "imports", path: "imports", label: "Imports", group: "monitor", permission: "imports.read" },
  { key: "providers", path: "providers", label: "Provider health", group: "monitor", permission: "system.health" },
  { key: "system", path: "system", label: "System health", group: "monitor", permission: "system.health" },
  { key: "users", path: "users", label: "Users", group: "people", permission: "users.read" },
  { key: "referrals", path: "referrals", label: "Referrals", group: "people", permission: "referrals.read" },
  { key: "support", path: "support", label: "Support inbox", group: "people", permission: "tickets.manage" },
  { key: "moderation", path: "moderation", label: "Moderation", group: "people", permission: "moderation.act" },
  { key: "subscriptions", path: "subscriptions", label: "Subscriptions", group: "money", permission: "subscriptions.read" },
  { key: "credits", path: "credits", label: "Credits and AI spend", group: "money", permission: "aispend.read" },
  { key: "affiliate", path: "affiliate", label: "Affiliate", group: "money", permission: "affiliate.read" },
  { key: "finance", path: "finance", label: "Finance", group: "money", permission: "finance.reports" },
  { key: "killswitches", path: "kill-switches", label: "Kill switches", group: "control", permission: "killswitch.read" },
  { key: "flags", path: "flags", label: "Flags", group: "control", permission: "flags.write" },
  { key: "settings", path: "settings", label: "Settings", group: "control", permission: "settings.ceilings.write" },
  { key: "admins", path: "admin-users", label: "Admin users", group: "control", permission: "admin_users.manage" },
  { key: "audit", path: "audit", label: "Audit log", group: "audit", permission: "audit.read" },
]

export const GROUP_LABEL: Record<NavGroup, string> = { monitor: "Monitor", people: "People", money: "Money", control: "Control", audit: "Audit" }

type Perms = Record<string, string>
const holds = (perms: Perms, name: string) => Boolean(perms[name]) && perms[name] !== "-"

export const visibleNav = (perms: Perms): NavItem[] => NAV.filter((i) => holds(perms, i.permission))

export const canOpen = (perms: Perms, key: string): boolean => {
  const item = NAV.find((i) => i.key === key)
  return item !== undefined && holds(perms, item.permission)
}
