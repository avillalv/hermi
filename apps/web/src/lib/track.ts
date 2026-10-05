/** Product events (05 section 6 "Events"). shortcut: no analytics sink exists yet, so events go to a window event that tests and a later sink can listen to. */
export function track(event: string, props: Record<string, string | number | boolean> = {}) {
  window.dispatchEvent(new CustomEvent("hermi:event", { detail: { event, props } }))
}
