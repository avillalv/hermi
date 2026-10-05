import { createApiClient } from "../../lib/api/client"
import { authStore } from "./authStore"
import { signOutEverywhere } from "./signOut"

/** The app's API client, wired to the auth store. A 401 that survives a refresh signs the person out. */
export const api = createApiClient({
  auth: {
    getAccessToken: () => authStore.get().token,
    refresh: async () => null, // shortcut: dev tokens last an hour and have no refresh token. Real providers refresh via Supabase.
    onSignedOut: () => signOutEverywhere().catch(() => {}),
  },
})
