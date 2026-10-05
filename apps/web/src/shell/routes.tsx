import { Route, Routes } from "react-router";
import { Activity } from "../routes/activity/Activity";
import { SessionControl } from "../routes/auth/SessionControl";
import { SignIn } from "../routes/auth/SignIn";
import { InviteLanding } from "../routes/invite/InviteLanding";
import { CreateTrip } from "../routes/onboarding/CreateTrip";
import { Onboarding } from "../routes/onboarding/Onboarding";
import { TripGroup } from "../routes/trips/TripGroup";
import { TripEdit } from "../routes/trips/TripEdit";
import { TripOverview } from "../routes/trips/TripOverview";
import { TripsHome } from "../routes/trips/TripsHome";
import { Welcome } from "../routes/onboarding/Welcome";
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
      <Route path="/welcome" element={<Welcome />} />
      <Route path="/sign-in" element={<SignIn />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/invite/:token" element={<InviteLanding />} />
      <Route path="/trips/new" element={<CreateTrip />} />
      <Route path="/trips/:id/edit" element={<TripEdit />} />
      <Route path="/trips/:id/group" element={<TripGroup />} />
      <Route path="/trips/:id" element={<TripOverview />} />
      <Route path="/" element={<TripsHome />} />
      <Route path="/activity" element={<Activity />} />
      {TABS.filter((t) => t.key !== "trips" && t.key !== "activity").map((t) => (
        <Route key={t.key} path={t.href} element={<Placeholder tab={t} />} />
      ))}
    </Routes>
  );
}
