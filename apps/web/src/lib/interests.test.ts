import { describe, expect, it } from 'vitest'
import { addInterests, MAX_INTERESTS } from './interests'

describe('addInterests', () => {
  it('tidies spaces and skips blanks and repeats in any case', () => {
    expect(addInterests(['Beaches'], ['  ATV   tours ', 'beaches', '', '   ', 'Local markets', 'ATV TOURS'])).toEqual([
      'Beaches',
      'ATV tours',
      'Local markets',
    ])
  })

  it('stops at the limit', () => {
    const full = Array.from({ length: MAX_INTERESTS }, (_, i) => `Thing ${i}`)
    expect(addInterests(full, ['One more'])).toEqual(full)
  })
})
