import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { expect, test } from "vitest"

// apps/web/public/_headers is read by Cloudflare Pages. Header names are keyed by the full URL so the strict policy
// applies to the admin hosts only (08 section 9 rule 7).
const raw = readFileSync(resolve(__dirname, "../../../public/_headers"), "utf8")
const blocks = raw.split(/\n(?=\S)/).map((b) => b.trim().split("\n").map((l) => l.trim()))
const forHost = (host: string) => blocks.find((b) => b[0] === `https://${host}/*`)
const header = (block: string[], name: string) =>
  block.slice(1).find((l) => l.toLowerCase().startsWith(`${name.toLowerCase()}:`))?.slice(name.length + 1).trim() ?? ""
const directives = (csp: string) =>
  Object.fromEntries(csp.split(";").map((d) => d.trim().split(/\s+/)).filter((d) => d[0]).map(([k, ...v]) => [k, v]))

test.each([
  ["admin.hermi.world", "https://api.hermi.world"],
  ["admin.staging.hermi.world", "https://api.staging.hermi.world"],
])("%s answers with a strict CSP", (host) => {
  const block = forHost(host)
  expect(block, `no rule for ${host}`).toBeDefined()
  const csp = directives(header(block!, "Content-Security-Policy"))
  expect(csp["default-src"]).toEqual(["'none'"])
  expect(csp["script-src"]).toEqual(["'self'"])
  expect(csp["connect-src"]).toEqual(["'self'"]) // the API is reached same-origin under /v1/admin (access.md)
  expect(csp["frame-ancestors"]).toEqual(["'none'"])
  expect(csp["base-uri"]).toEqual(["'none'"])
  expect(csp["form-action"]).toEqual(["'self'"])
  const all = Object.values(csp).flat().join(" ")
  expect(all).not.toMatch(/unsafe-eval|unsafe-inline|https?:|\*/)
  expect(all).not.toMatch(/googleapis|gstatic|posthog|sentry/)
  expect(header(block!, "X-Frame-Options")).toBe("DENY")
  expect(header(block!, "Referrer-Policy")).toBe("no-referrer")
  expect(header(block!, "X-Content-Type-Options")).toBe("nosniff")
  expect(header(block!, "X-Robots-Tag")).toMatch(/noindex/)
  expect(header(block!, "Cache-Control")).toMatch(/no-store/)
})

test("the SPA entry has no inline script, so script-src 'self' holds", () => {
  const html = readFileSync(resolve(__dirname, "../../../index.html"), "utf8")
  expect([...html.matchAll(/<script\b([^>]*)>/g)].every((m) => /\bsrc=/.test(m[1]))).toBe(true)
  expect(html).not.toMatch(/\son\w+=/)
})
