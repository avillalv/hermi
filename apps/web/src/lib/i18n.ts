import en from "../../../../locales/en.json"

/** Look up a string in `locales/en.json` by dotted key. `{name}` slots are filled from `vars`. English only for now. */
export function t(key: string, vars: Record<string, string | number> = {}): string {
  const hit = key.split(".").reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], en)
  if (typeof hit !== "string") throw new Error(`Missing copy key: ${key}`)
  return hit.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`))
}
