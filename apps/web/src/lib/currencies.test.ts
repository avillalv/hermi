import { describe, expect, it } from 'vitest'
import { currencyOptions } from './currencies'

describe('currencyOptions', () => {
  it('lists ISO 4217 codes with names', () => {
    const usd = currencyOptions().find((c) => c.code === 'USD')
    expect(usd?.name).toMatch(/dollar/i)
    expect(currencyOptions()).toBe(currencyOptions())
  })
})
