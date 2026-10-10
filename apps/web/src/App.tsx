import { GuestClaimHost } from "./features/guest/GuestClaimHost";
import { SaveSheetHost } from "./features/guest/SaveSheet";
import { AppRoutes } from "./shell/routes";

export function App() {
  return (
    <>
      <AppRoutes />
      <SaveSheetHost />
      <GuestClaimHost />
    </>
  );
}
