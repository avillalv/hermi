import { GuestClaimHost } from "./features/guest/GuestClaimHost";
import { SaveSheetHost } from "./features/guest/SaveSheet";
import { isAdminHost } from "./routes/admin/adminHost";
import { AppRoutes } from "./shell/routes";

export function App() {
  // No guest or sharing hosts on the admin host: it loads nothing but the console.
  if (isAdminHost()) return <AppRoutes />;
  return (
    <>
      <AppRoutes />
      <SaveSheetHost />
      <GuestClaimHost />
    </>
  );
}
