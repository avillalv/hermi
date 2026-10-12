// @vitest-environment node
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { build } from "vite"
import type { RollupOutput } from "rollup"
import { expect, test } from "vitest"

// The marker constant sits in AdminRoutes.tsx; read it as text so this test runs in the node environment esbuild needs.
const ADMIN_CHUNK_MARKER = /ADMIN_CHUNK_MARKER = "([^"]+)"/.exec(readFileSync(resolve(__dirname, "AdminRoutes.tsx"), "utf8"))![1]

// Runs the real production build twice, in memory. Slow on purpose: it is the only proof that the admin route group
// is its own chunk and that VITE_BUILD_TARGET=ios leaves it out (08 section 2.1).
async function bundle(target: string | undefined) {
  const prev = process.env.VITE_BUILD_TARGET
  if (target) process.env.VITE_BUILD_TARGET = target
  else delete process.env.VITE_BUILD_TARGET
  try {
    const out = (await build({
      configFile: resolve(__dirname, "../../../vite.config.ts"),
      logLevel: "silent",
      mode: "production",
      build: { write: false, outDir: resolve(__dirname, "../../../../../.autopilot/tmp/web-build-test"), emptyOutDir: false },
    })) as RollupOutput | RollupOutput[]
    const chunks = (Array.isArray(out) ? out : [out]).flatMap((o) => o.output).filter((o) => o.type === "chunk")
    return chunks.map((c) => ({ name: c.fileName, code: c.code, entry: c.isEntry }))
  } finally {
    if (prev === undefined) delete process.env.VITE_BUILD_TARGET
    else process.env.VITE_BUILD_TARGET = prev
  }
}

test("the admin routes are a separate chunk on the web and are gone from the iOS bundle", { timeout: 240_000 }, async () => {
  const web = await bundle(undefined)
  const withAdmin = web.filter((c) => c.code.includes(ADMIN_CHUNK_MARKER))
  expect(withAdmin).toHaveLength(1)
  expect(withAdmin[0].entry).toBe(false) // lazy: customers on the web do not download it with the app entry

  const ios = await bundle("ios")
  expect(ios.filter((c) => c.code.includes(ADMIN_CHUNK_MARKER))).toEqual([])
  // Nothing of the console's own code or copy ships either.
  expect(ios.some((c) => c.code.includes("/v1/admin/auth/stepup"))).toBe(false)
  expect(ios.length).toBeLessThan(web.length)
})
