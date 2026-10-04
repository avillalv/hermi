// The server enforces the same limits.
export const MAX_INTERESTS = 25
export const MAX_INTEREST_LENGTH = 60

export const SUGGESTED_INTERESTS = [
  'Beaches',
  'Nature',
  'Culture',
  'Food',
  'Nightlife',
  'Markets',
  'Art',
  'Shopping',
  'Adventure',
]

export const hasInterest = (list: string[], interest: string) =>
  list.some((x) => x.toLowerCase() === interest.toLowerCase())

/** The list with each entry added like the server would: spaces collapsed, blanks and repeats (in any case) skipped. */
export function addInterests(current: string[], entries: string[]): string[] {
  const next = [...current]
  for (const entry of entries) {
    const text = entry.replace(/\s+/g, ' ').trim().slice(0, MAX_INTEREST_LENGTH)
    if (text && next.length < MAX_INTERESTS && !hasInterest(next, text)) next.push(text)
  }
  return next
}
