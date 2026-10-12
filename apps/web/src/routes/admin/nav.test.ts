import { expect, test } from "vitest"
import { canOpen, NAV, visibleNav } from "./nav"

// The nav-relevant cells of the 08 section 3 matrix (owner, engineer, support, finance, content). The API test
// (tests/test_admin_permissions.py) keeps the full table equal to 08; this one keeps the console's menu equal to it.
const CELLS: Record<string, string> = {
  "overview.read": "RRrr-",
  "imports.read": "RRr--",
  "system.health": "RR-r-",
  "users.read": "RRRr-",
  "referrals.read": "RRrr-",
  "tickets.manage": "WWW--",
  "moderation.act": "WWW-W",
  "subscriptions.read": "RRrR-",
  "aispend.read": "RRrR-",
  "affiliate.read": "RR-Rr",
  "finance.reports": "Rr-X-",
  "killswitch.read": "RRRRR",
  "flags.write": "WW---",
  "settings.ceilings.write": "XW-R-",
  "admin_users.manage": "X----",
  "audit.read": "RRrrr",
}
const ROLES = ["owner", "engineer", "support", "finance", "content"] as const
const permsFor = (role: (typeof ROLES)[number]) =>
  Object.fromEntries(
    Object.entries(CELLS)
      .map(([name, cells]) => [name, cells[ROLES.indexOf(role)]] as const)
      .filter(([, level]) => level !== "-"),
  )

const EXPECTED: Record<(typeof ROLES)[number], string[]> = {
  owner: ["overview", "imports", "providers", "system", "users", "referrals", "support", "moderation", "subscriptions", "credits", "affiliate", "finance", "killswitches", "flags", "settings", "admins", "audit"],
  engineer: ["overview", "imports", "providers", "system", "users", "referrals", "support", "moderation", "subscriptions", "credits", "affiliate", "finance", "killswitches", "flags", "settings", "audit"],
  support: ["overview", "imports", "users", "referrals", "support", "moderation", "subscriptions", "credits", "killswitches", "audit"],
  finance: ["overview", "providers", "system", "users", "referrals", "subscriptions", "credits", "affiliate", "finance", "killswitches", "settings", "audit"],
  content: ["moderation", "affiliate", "killswitches", "audit"],
}

test.each(ROLES)("role by route matrix: %s sees only the 08 section 3 items", (role) => {
  expect(visibleNav(permsFor(role)).map((i) => i.key).sort()).toEqual([...EXPECTED[role]].sort())
})

test("canOpen follows the same rule as the menu, so a typed address is gated too", () => {
  for (const role of ROLES)
    for (const item of NAV) expect(canOpen(permsFor(role), item.key)).toBe(EXPECTED[role].includes(item.key))
  expect(canOpen({}, "nope")).toBe(false)
})

test("the menu groups follow 08 section 5 and every item has a unique path", () => {
  expect([...new Set(NAV.map((i) => i.group))]).toEqual(["monitor", "people", "money", "control", "audit"])
  expect(new Set(NAV.map((i) => i.path)).size).toBe(NAV.length)
})
