import { Route, Routes } from "react-router";
import { AppShell, TABS } from "./AppShell";

/** Placeholder until each tab's ticket lands. Trips is the home route `/` (05 5.4). */
function Placeholder({ tab }: { tab: (typeof TABS)[number] }) {
  return (
    <AppShell active={tab.key}>
      <h1 className="h-title">{tab.label}</h1>
    </AppShell>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      {TABS.map((t) => (
        <Route key={t.key} path={t.href} element={<Placeholder tab={t} />} />
      ))}
    </Routes>
  );
}
