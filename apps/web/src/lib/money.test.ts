import { describe, expect, it } from 'vitest'
import {
  convertMinor,
  formatMoney,
  formatDuration,
  formatMoneyPair,
  FX_STALE_NOTICE,
  isFxStale,
  minorDigits,
  NO_PRICE,
  type FxRates,
} from './money'

describe('money', () => {
  it('knows the minor unit of a currency', () => {
    expect(minorDigits('USD')).toBe(2)
    expect(minorDigits('JPY')).toBe(0)
    expect(minorDigits('KWD')).toBe(3)
  })

  it('formats integer minor units', () => {
    expect(formatMoney(185900, 'USD')).toContain('1,859')
    expect(formatMoney(1859, 'JPY')).toContain('1,859')
    expect(formatMoney(185900, 'USD', true)).toMatch(/K/)
  })

  it('says so when there is no price', () => {
    expect(formatMoney(null, 'USD')).toBe(NO_PRICE)
    expect(formatMoney(Number.NaN, 'USD')).toBe(NO_PRICE)
  })

  it('formats durations', () => {
    expect(formatDuration(760)).toBe('12h 40m')
    expect(formatDuration(45)).toBe('45m')
    expect(formatDuration(null)).toBe('Unknown')
  })
})

const NOW = new Date('2026-10-05T12:00:00Z')
const rates: FxRates = {
  perEur: { USD: '1.1', JPY: '160', GBP: '0.85', KWD: '0.34' },
  rateDate: '2026-10-02',
  fetchedAt: '2026-10-05T06:00:00Z',
}

describe('conversion', () => {
  it('converts integer minor units through EUR and rounds to the target minor unit', () => {
    expect(convertMinor(10000, 'USD', 'USD', rates)).toBe(10000)
    expect(convertMinor(11000, 'USD', 'EUR', rates)).toBe(10000)
    expect(convertMinor(10000, 'EUR', 'JPY', rates)).toBe(16000)
    expect(convertMinor(10000, 'USD', 'JPY', rates)).toBe(14545)
    expect(convertMinor(10000, 'EUR', 'KWD', rates)).toBe(34000)
  })

  // The same vectors are in apps/api/tests/test_fx_refresh.py (HALF_VECTORS), run against SQL fx_convert_minor().
  it.each([
    [5, 'EUR', 'GBP', 3],
    [-5, 'EUR', 'GBP', -3],
    [1, 'EUR', 'GBP', 1],
    [50, 'EUR', 'JPY', 1],
    [-50, 'EUR', 'JPY', -1],
    [5, 'KWD', 'EUR', 1],
    [-5, 'KWD', 'EUR', -1],
    [4, 'KWD', 'EUR', 0],
    [1, 'CHF', 'CAD', 1],
    [-1, 'CHF', 'CAD', -1],
  ])('rounds exact halves away from zero: %i %s to %s is %i', (minor, from, to, expected) => {
    const half: FxRates = { perEur: { GBP: '0.5', JPY: '1', KWD: '1', CHF: '3', CAD: '1.5' }, rateDate: '2026-10-02', fetchedAt: rates.fetchedAt }
    expect(convertMinor(minor, from, to, half)).toBe(expected)
  })

  it('returns null when a rate is missing, never a made-up number', () => {
    expect(convertMinor(100, 'USD', 'ZZZ', rates)).toBeNull()
    expect(convertMinor(100, 'USD', 'JPY', null)).toBeNull()
    expect(convertMinor(null, 'USD', 'JPY', rates)).toBeNull()
  })

  it('shows original and converted amounts', () => {
    const p = formatMoneyPair(10000, 'USD', 'JPY', rates, NOW)
    expect(p.original).toContain('100')
    expect(p.converted).toContain('14,545')
    expect(p.stale).toBe(false)
    expect(p.notice).toBeNull()
    expect(p.rateDate).toBe('2026-10-02')
  })

  it('shows only the original when currencies match or no rate exists', () => {
    expect(formatMoneyPair(10000, 'USD', 'USD', rates, NOW).converted).toBeNull()
    expect(formatMoneyPair(10000, 'USD', 'ZZZ', rates, NOW).converted).toBeNull()
  })
})

describe('stale rates', () => {
  it('is stale after 48 hours, fresh before', () => {
    expect(isFxStale(rates, new Date('2026-10-07T05:59:00Z'))).toBe(false)
    expect(isFxStale(rates, new Date('2026-10-07T06:01:00Z'))).toBe(true)
  })

  it('treats missing or unreadable rates as stale', () => {
    expect(isFxStale(null, NOW)).toBe(true)
    expect(isFxStale({ perEur: {}, rateDate: '', fetchedAt: 'nope' }, NOW)).toBe(true)
  })

  it('adds a notice to a converted amount, without dashes', () => {
    const p = formatMoneyPair(10000, 'USD', 'JPY', rates, new Date('2026-10-09T00:00:00Z'))
    expect(p.stale).toBe(true)
    expect(p.notice).toBe(FX_STALE_NOTICE)
    expect(FX_STALE_NOTICE).not.toMatch(/[\u2013\u2014]/)
  })
})
