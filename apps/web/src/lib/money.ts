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

/** Exchange rates as fx_rates stores them: units of each currency per 1 EUR as decimal strings (numeric(20,8)), the ECB date, and when they were fetched. */
export type FxRates = { perEur: Record<string, string>; rateDate: string; fetchedAt: string }

/** The refresh job runs daily, so rates older than 2 days mean it is failing (ECB weekend gaps do not move fetchedAt). */
export const FX_STALE_MS = 48 * 60 * 60 * 1000
export const FX_STALE_NOTICE = 'Exchange rates are out of date. Converted amounts are approximate.'

export function isFxStale(rates: FxRates | null | undefined, now: Date = new Date()): boolean {
  if (!rates) return true
  const fetched = Date.parse(rates.fetchedAt)
  return Number.isNaN(fetched) || now.getTime() - fetched > FX_STALE_MS
}

const SCALE = 8
/** "0.85" to 85000000n. Null for anything that is not a positive plain decimal. Digits beyond 8 decimals are truncated, which is exact for numeric(20,8). */
function scaledRate(value: string | undefined): bigint | null {
  const m = value?.match(/^(\d+)(?:\.(\d+))?$/)
  if (!m) return null
  const n = BigInt(m[1] + (m[2] ?? '').slice(0, SCALE).padEnd(SCALE, '0'))
  return n > 0n ? n : null
}

/** num / den rounded half away from zero (den > 0), like SQL round() on numeric. */
function divRound(num: bigint, den: bigint): bigint {
  const abs = num < 0n ? -num : num
  const q = (2n * abs + den) / (2n * den)
  return num < 0n ? -q : q
}

/**
 * Same result as SQL fx_convert_minor() (03 section 3): integer minor units in and out, rounded half away from
 * zero in the target currency's minor unit, exact (BigInt over 8-decimal rates). Null when a rate is missing.
 * Display only, never stored. Safe for amounts below 2^53 minor units.
 */
export function convertMinor(
  minor: number | null | undefined,
  from: string,
  to: string,
  rates: FxRates | null | undefined,
): number | null {
  if (minor === null || minor === undefined || !Number.isSafeInteger(minor)) return null
  if (from === to) return minor
  const rate = (c: string) => (c === 'EUR' ? 10n ** BigInt(SCALE) : scaledRate(rates?.perEur[c]))
  const f = rate(from)
  const t = rate(to)
  if (!f || !t) return null
  const num = BigInt(minor) * t * 10n ** BigInt(minorDigits(to))
  const den = f * 10n ** BigInt(minorDigits(from))
  return Number(divRound(num, den))
}

export type MoneyPair = {
  original: string
  converted: string | null
  stale: boolean
  notice: string | null
  /** The ECB publication date of the rates used, for "rates from 2 Oct". Null when nothing was converted. */
  rateDate: string | null
}

/** The amount in its own currency, plus the converted amount in the viewer's currency when a rate exists. */
export function formatMoneyPair(
  minor: number | null | undefined,
  currency: string,
  display: string,
  rates: FxRates | null | undefined,
  now: Date = new Date(),
): MoneyPair {
  const original = formatMoney(minor, currency)
  const convertedMinor = currency === display ? null : convertMinor(minor, currency, display, rates)
  if (convertedMinor === null) return { original, converted: null, stale: false, notice: null, rateDate: null }
  const stale = isFxStale(rates, now)
  return { original, converted: formatMoney(convertedMinor, display), stale, notice: stale ? FX_STALE_NOTICE : null,
    rateDate: rates?.rateDate ?? null,
  }
}
