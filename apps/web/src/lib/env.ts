/**
 * The only reader of `import.meta.env`. Every value here is public by design (it ships in the
 * bundle), so a secret never gets a `VITE_` name. Documented in `.env.example` and
 * `knowledge/env-and-accounts.md`. Empty means "not set".
 */
export type WebEnv = {
  apiBaseUrl: string
  appEnv: string
  releaseSha: string
  supabaseUrl?: string
  supabaseAnonKey?: string
  revenuecatKeyIos?: string
  sentryDsn?: string
  posthogKey?: string
}

type Raw = Record<string, string | boolean | undefined>

const LOCAL_ENVS = ["local", "ci", "test"]
export const DEFAULT_API_BASE_URL = "http://localhost:8100"

export function readEnv(raw: Raw = import.meta.env as Raw): WebEnv {
  const s = (k: string) => (typeof raw[k] === "string" && raw[k] !== "" ? (raw[k] as string) : undefined)
  const appEnv = s("VITE_APP_ENV") ?? "local"
  // A hosted build must never silently call localhost.
  if (!LOCAL_ENVS.includes(appEnv) && !s("VITE_API_BASE_URL")) {
    throw new Error(`VITE_API_BASE_URL is required when VITE_APP_ENV is ${appEnv}`)
  }
  return {
    apiBaseUrl: (s("VITE_API_BASE_URL") ?? DEFAULT_API_BASE_URL).replace(/\/+$/, ""),
    appEnv,
    releaseSha: s("VITE_RELEASE_SHA") ?? "dev",
    supabaseUrl: s("VITE_SUPABASE_URL"),
    supabaseAnonKey: s("VITE_SUPABASE_ANON_KEY"),
    revenuecatKeyIos: s("VITE_REVENUECAT_KEY_IOS"),
    sentryDsn: s("VITE_SENTRY_DSN"),
    posthogKey: s("VITE_POSTHOG_KEY"),
  }
}

export const env: WebEnv = readEnv()
