import { ErrorState } from "../components/ErrorState"
import { Sprite } from "../components/kit"
import { t } from "../lib/i18n"

/** The `*` route: a full-screen not found with Back and Home. */
export function NotFound() {
  return (
    <>
      <Sprite />
      <ErrorState kind="notFound" message={t("states.page.notFound")} fullScreen />
    </>
  )
}
