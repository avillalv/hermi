import { authStore } from "./authStore"
import { identity } from "./identity"

/** Ends the provider session, then clears the store (also in `finally`), so restore() cannot sign the person back in. */
export async function signOutEverywhere(): Promise<void> {
  try {
    await identity.signOut?.()
  } finally {
    authStore.signOut()
  }
}
