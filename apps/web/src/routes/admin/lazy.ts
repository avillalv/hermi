import { lazy } from "react"

/**
 * The admin route group, code split into its own chunk and absent from the Capacitor iOS bundle (08 2.1).
 * `VITE_BUILD_TARGET=ios` makes the condition a build time constant, so the dynamic import below is dropped and
 * no admin code is emitted (apps/web/src/routes/admin/build.test.ts proves it). The read stays a bare
 * `import.meta.env` expression on purpose: going through `lib/env.ts` would hide the constant from the bundler.
 */
export const AdminRoutes = import.meta.env.VITE_BUILD_TARGET === "ios" ? null : lazy(() => import("./AdminRoutes"))
