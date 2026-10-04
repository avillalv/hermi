import { describe, expect, it } from 'vitest'
import { isStaleBuild } from './errors'

describe('isStaleBuild', () => {
  it('spots a failed chunk import', () => {
    expect(isStaleBuild(new Error('Failed to fetch dynamically imported module: /a.js'))).toBe(true)
    expect(isStaleBuild(new Error('network down'))).toBe(false)
    expect(isStaleBuild('x')).toBe(false)
  })
})
