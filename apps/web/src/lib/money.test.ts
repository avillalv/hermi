import { describe, expect, it } from 'vitest'
import { formatDuration, formatMoney, minorDigits, NO_PRICE } from './money'

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
