import { beforeEach, expect, test, vi } from "vitest"
import { authStore } from "./authStore"
import { identity } from "./identity"
import { signOutEverywhere } from "./signOut"

beforeEach(() => authStore.signOut())

test("ends the provider session, then clears the store", async () => {
  authStore.signIn("tok")
  const order: string[] = []
  identity.signOut = vi.fn(async () => void order.push(`provider:${authStore.get().token}`))
  await signOutEverywhere()
  expect(order).toEqual(["provider:tok"])
  expect(authStore.get().token).toBeNull()
})

test("clears the store even when the provider sign-out rejects", async () => {
  authStore.signIn("tok")
  identity.signOut = vi.fn(async () => {
    throw new Error("boom")
  })
  await expect(signOutEverywhere()).rejects.toThrow("boom")
  expect(authStore.get().token).toBeNull()
})
