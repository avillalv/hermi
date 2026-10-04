const FALLBACK = ['USD', 'EUR', 'GBP', 'JPY', 'MXN', 'CAD', 'AUD', 'CHF', 'CNY', 'KRW', 'THB', 'INR', 'BRL', 'NZD']

export type CurrencyOption = { code: string; name: string }

let cached: CurrencyOption[] | null = null

/** Every ISO 4217 currency the browser knows, with its display name ("USD, US Dollar"). */
export function currencyOptions(): CurrencyOption[] {
  if (cached) return cached
  const codes = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('currency') : FALLBACK
  const names = new Intl.DisplayNames(undefined, { type: 'currency' })
  cached = codes.map((code) => ({ code, name: names.of(code) ?? code }))
  return cached
}
