import { Route, Routes } from "react-router";
import { SessionControl } from "../routes/auth/SessionControl";
import { SignIn } from "../routes/auth/SignIn";
import { AppShell, TABS } from "./AppShell";

/** Placeholder until each tab's ticket lands. Trips is the home route `/` (05 5.4). */
function Placeholder({ tab }: { tab: (typeof TABS)[number] }) {
  return (
    <AppShell active={tab.key}>
      <h1 className="h-title">{tab.label}</h1>
      {/* shortcut: sign in and sign out live here until the Account screen lands, so the flow is reachable. */}
      {tab.key === "account" && <SessionControl />}
    </AppShell>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignIn />} />
      {TABS.map((t) => (
        <Route key={t.key} path={t.href} element={<Placeholder tab={t} />} />
      ))}
    </Routes>
  );
}
