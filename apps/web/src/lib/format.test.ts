import { describe, expect, it } from 'vitest'
import { compactNumber, formatBytes, formatElapsed, hostOf, timeAgo } from './format'

describe('format', () => {
  it('formats elapsed time', () => {
    expect(formatElapsed(42_000)).toBe('42 s')
    expect(formatElapsed(6 * 60_000)).toBe('6 min')
    expect(formatElapsed(65 * 60_000)).toBe('1 h 5 min')
    expect(formatElapsed(-5)).toBe('0 s')
  })

  it('formats sizes and counts', () => {
    expect(formatBytes(10)).toBe('1 KB')
    expect(formatBytes(2.1 * 1024 * 1024)).toBe('2.1 MB')
    expect(compactNumber(38_412)).toMatch(/38\.4/)
  })

  it('says how long ago', () => {
    const now = new Date('2026-11-05T12:00:00Z')
    expect(timeAgo('2026-11-05T09:00:00Z', now)).toMatch(/3 hours ago/)
  })

  it('shows the host of a link', () => {
    expect(hostOf('https://www.example.com/a?b=1')).toBe('example.com')
    expect(hostOf('not a link')).toBe('not a link')
  })
})
