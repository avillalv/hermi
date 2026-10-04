/** Dates in this app are calendar days ("2026-11-05"), handled in local time to avoid UTC shifts. */

export function parseDate(iso: string): Date {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function toISODate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function daysBetween(from: Date, to: Date): number {
  const utc = (d: Date) => Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())
  return Math.round((utc(to) - utc(from)) / 86_400_000)
}

const rangeFormat = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

/** "Nov 5 to 15, 2026" style ranges, from the viewer's locale. Intl joins with a dash; we swap it for "to". */
export function formatDateRange(start: string, end: string): string {
  return rangeFormat
    .formatRange(parseDate(start), parseDate(end))
    .replace(/\s*[\u2013\u2014]\s*/g, ' to ')
}

export function tripLengthDays(start: string, end: string): number {
  return daysBetween(parseDate(start), parseDate(end)) + 1
}

export type TripTiming =
  | { kind: 'upcoming'; days: number }
  | { kind: 'ongoing'; day: number; total: number }
  | { kind: 'past'; daysAgo: number }

export function tripTiming(start: string, end: string, today: Date = new Date()): TripTiming {
  const untilStart = daysBetween(today, parseDate(start))
  if (untilStart > 0) return { kind: 'upcoming', days: untilStart }
  const sinceEnd = daysBetween(parseDate(end), today)
  if (sinceEnd > 0) return { kind: 'past', daysAgo: sinceEnd }
  return { kind: 'ongoing', day: 1 - untilStart, total: tripLengthDays(start, end) }
}

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

function relativeDays(days: number): string {
  const abs = Math.abs(days)
  if (abs < 45) return relative.format(days, 'day')
  if (abs < 320) return relative.format(Math.round(days / 30.44), 'month')
  return relative.format(Math.round(days / 365.25), 'year')
}

/** "In 40 days", "Tomorrow", "Day 3 of 11", "Ended 2 months ago". */
export function timingLabel(timing: TripTiming): string {
  switch (timing.kind) {
    case 'upcoming':
      return capitalize(relativeDays(timing.days))
    case 'ongoing':
      return `Day ${timing.day} of ${timing.total}`
    case 'past':
      return `Ended ${relativeDays(-timing.daysAgo)}`
  }
}
