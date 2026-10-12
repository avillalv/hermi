import { expect, test } from "vitest"
import { adminAvailable, isAdminHost } from "./adminHost"

test("the admin host and its staging twin are admin hosts", () => {
  expect(isAdminHost("admin.hermi.world")).toBe(true)
  expect(isAdminHost("admin.staging.hermi.world")).toBe(true)
  expect(isAdminHost("app.hermi.world")).toBe(false)
  expect(isAdminHost("hermi.world")).toBe(false)
  expect(isAdminHost("evil-admin.hermi.world.example.com")).toBe(false)
  expect(isAdminHost("admin.evil.com")).toBe(false)
  expect(isAdminHost("admin.hermi.world.evil.com")).toBe(false)
})

test("the console is served on the admin host and on localhost, never on the customer host", () => {
  expect(adminAvailable("admin.hermi.world")).toBe(true)
  expect(adminAvailable("localhost")).toBe(true)
  expect(adminAvailable("app.hermi.world")).toBe(false)
})
