import { beforeEach, expect, test, vi } from "vitest"
import { queryClient } from "../../lib/queryClient"
import { ONBOARDED_KEY } from "../onboarding/trips"
import { authStore } from "./authStore"

beforeEach(() => authStore.signOut())

test("starts signed out", () => {
  expect(authStore.get().token).toBeNull()
})

test("sign-in keeps the token for the tab and sign-out clears state, storage and the query cache", () => {
  queryClient.setQueryData(["trips"], [1])
  authStore.signIn("tok", "free")
  expect(authStore.get()).toEqual({ token: "tok", persona: "free" })
  expect(sessionStorage.getItem("hermi.auth")).toContain("tok")
  authStore.signOut()
  expect(authStore.get().token).toBeNull()
  expect(sessionStorage.getItem("hermi.auth")).toBeNull()
  expect(queryClient.getQueryData(["trips"])).toBeUndefined()
})

test("subscribers hear about changes", () => {
  const fn = vi.fn()
  const off = authStore.subscribe(fn)
  authStore.signIn("t")
  off()
  authStore.signOut()
  expect(fn).toHaveBeenCalledTimes(1)
})

test("sign-out clears the onboarded flag", () => {
  sessionStorage.setItem(ONBOARDED_KEY, "1")
  authStore.signOut()
  expect(sessionStorage.getItem(ONBOARDED_KEY)).toBeNull()
})
