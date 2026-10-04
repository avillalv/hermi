/** Shown when there is no price to show. */
export const NO_PRICE = 'No price'

const formatters = new Map<string, Intl.NumberFormat>()

function formatter(currency: string, compact: boolean): Intl.NumberFormat {
  const key = `${currency}:${compact}`
  let f = formatters.get(key)
  if (!f) {
    f = new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
      notation: compact ? 'compact' : 'standard',
    })
    formatters.set(key, f)
  }
  return f
}

/** Digits after the decimal point in the currency's minor unit (JPY 0, USD 2, KWD 3). */
export function minorDigits(currency: string): number {
  try {
    return new Intl.NumberFormat('en', { style: 'currency', currency }).resolvedOptions().maximumFractionDigits ?? 2
  } catch {
    return 2
  }
}

/** "$1,859" from integer minor units (185900 cents) and an ISO 4217 code, as 03 stores money. */
export function formatMoney(minor: number | null | undefined, currency: string, compact = false): string {
  if (minor === null || minor === undefined || !Number.isFinite(minor)) return NO_PRICE
  const value = minor / 10 ** minorDigits(currency)
  try {
    return formatter(currency, compact).format(value)
  } catch {
    return `${currency} ${Math.round(value).toLocaleString()}`
  }
}

/** "12h 40m" from minutes. */
export function formatDuration(minutes: number | null | undefined): string {
  if (!minutes) return 'Unknown'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`
}
