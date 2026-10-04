import { Link } from "react-router"
import { Btn } from "../../components/kit"
import { t } from "../../lib/i18n"
import { useAuth } from "./authStore"
import { signOutEverywhere } from "./signOut"

/** Sign in link when signed out, Sign out button when signed in. The Account screen (later ticket) hosts it. */
export function SessionControl() {
  const { token } = useAuth()
  if (!token)
    return (
      // A router <Link> wearing the kit classes: LinkBtn emits a plain <a href>, which would reload the page.
      <Link className="h-btn h-btn--secondary" to="/sign-in">
        {t("auth.signIn")}
      </Link>
    )
  return (
    <Btn variant="secondary" onClick={() => void signOutEverywhere().catch(() => {})}>
      {t("auth.signOut")}
    </Btn>
  )
}
