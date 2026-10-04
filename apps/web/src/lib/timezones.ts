/** Minutes east of UTC for a time zone at a given instant (handles daylight saving). */
export function utcOffsetMinutes(timeZone: string, at: Date = new Date()): number {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'longOffset' }).formatToParts(at)
  const name = parts.find((p) => p.type === 'timeZoneName')?.value ?? 'GMT'
  const match = name.match(/GMT([+-])(\d{1,2}):?(\d{2})?/)
  if (!match) return 0
  const minutes = Number(match[2]) * 60 + Number(match[3] ?? 0)
  return match[1] === '-' ? -minutes : minutes
}

export function localTime(timeZone: string, at: Date = new Date()): string {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZone }).format(at)
}

/** "7 hours ahead of you", "Same time as you", "5.5 hours behind you". */
export function offsetFromViewer(
  timeZone: string,
  at: Date = new Date(),
  viewerOffsetMinutes: number = -at.getTimezoneOffset(),
): string {
  const diff = utcOffsetMinutes(timeZone, at) - viewerOffsetMinutes
  if (diff === 0) return 'Same time as you'
  const hours = Math.abs(diff) / 60
  const amount = Number.isInteger(hours) ? String(hours) : hours.toFixed(1)
  return `${amount} hour${hours === 1 ? '' : 's'} ${diff > 0 ? 'ahead of' : 'behind'} you`
}
