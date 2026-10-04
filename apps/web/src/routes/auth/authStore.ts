import { useSyncExternalStore } from "react"
import { queryClient } from "../../lib/queryClient"

export type AuthState = { token: string | null; persona?: string }

const KEY = "hermi.auth"
const SIGNED_OUT: AuthState = { token: null }

function load(): AuthState {
  try {
    const raw = sessionStorage.getItem(KEY)
    const v = raw ? (JSON.parse(raw) as AuthState) : null
    return v && typeof v.token === "string" ? v : SIGNED_OUT
  } catch {
    return SIGNED_OUT
  }
}

let state = load()
const listeners = new Set<() => void>()
const set = (next: AuthState) => {
  state = next
  listeners.forEach((l) => l())
}

// shortcut: the bearer token sits in sessionStorage so a reload keeps the tab signed in. Upgrade to the Supabase
// client's own session storage and refresh when the real providers land (WF-018 follow-up, owner keys needed).
export const authStore = {
  get: () => state,
  subscribe(fn: () => void) {
    listeners.add(fn)
    return () => void listeners.delete(fn)
  },
  signIn(token: string, persona?: string) {
    state = persona ? { token, persona } : { token }
    sessionStorage.setItem(KEY, JSON.stringify(state))
    listeners.forEach((l) => l())
  },
  /** Clears the token, the stored session and every cached query. */
  signOut() {
    sessionStorage.removeItem(KEY)
    queryClient.clear()
    set(SIGNED_OUT)
  },
}

export const useAuth = () => useSyncExternalStore(authStore.subscribe, authStore.get)
