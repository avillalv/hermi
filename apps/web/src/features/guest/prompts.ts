import { useSyncExternalStore } from "react"
import { authStore } from "../../routes/auth/authStore"
import { track } from "../../lib/track"

/** The triggers of the `save_prompt_*` events (10 section 4). "import" has no trigger of its own in the catalogue, so it reports as "sync". */
export type Trigger = "invite" | "sync" | "ai" | "export" | "alert" | "purchase" | "banner"
export type Need = Trigger | "import"

const MUTE_KEY = "hermi.guest.mutes"
export const MUTE_DAYS = 7
const DAY_MS = 86_400_000

type View = { open: Trigger | null; hint: Trigger | null }
let view: View = { open: null, hint: null }
const listeners = new Set<() => void>()
const set = (next: View) => {
  view = next
  listeners.forEach((l) => l())
}

const mutes = (): Record<string, number> => {
  try {
    return JSON.parse(localStorage.getItem(MUTE_KEY) ?? "{}") as Record<string, number>
  } catch {
    return {}
  }
}
export const isMuted = (trigger: Trigger, now = Date.now()) => (mutes()[trigger] ?? 0) > now

/** Opens the sheet and emits `save_prompt_shown`. */
export function showSavePrompt(trigger: Trigger) {
  if (view.open === trigger) return
  track("save_prompt_shown", { trigger })
  set({ open: trigger, hint: null })
}

/** "Not now", Escape or the scrim: emits `save_prompt_dismissed` and mutes that trigger for 7 days. The banner is never muted. */
export function dismissSavePrompt() {
  const trigger = view.open
  if (!trigger) return
  track("save_prompt_dismissed", { trigger })
  if (trigger !== "banner") {
    try {
      localStorage.setItem(MUTE_KEY, JSON.stringify({ ...mutes(), [trigger]: Date.now() + MUTE_DAYS * DAY_MS }))
    } catch {
      /* the mute is a courtesy, not a rule */
    }
  }
  set({ open: null, hint: null })
}

export const closeSavePrompt = () => set({ open: null, hint: null })
export const clearHint = () => set({ ...view, hint: null })

/**
 * Call at an entry point that needs the server (invite, sync, AI beyond the guest allowance, export, alerts, import,
 * purchase). Returns true when the caller is signed in and should carry on. For a guest it returns false and shows the
 * Save sheet; when that trigger was dismissed within 7 days it shows a quiet line with a Save button instead, so the tap
 * is never silent and the sheet is not pushed again (05 6.2).
 */
export function requireAccount(need: Need): boolean {
  if (authStore.get().token) return true
  const trigger: Trigger = need === "import" ? "sync" : need
  if (isMuted(trigger)) set({ open: null, hint: trigger })
  else showSavePrompt(trigger)
  return false
}

export const useSavePrompt = (): View =>
  useSyncExternalStore(
    (fn) => {
      listeners.add(fn)
      return () => void listeners.delete(fn)
    },
    () => view,
  )
