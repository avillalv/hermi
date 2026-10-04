/**
 * Activity times are wall-clock times at the destination ("14:00:00"). The day calendar runs in
 * UTC mode, so those times show exactly as stored, whatever time zone the viewer is in.
 */
import { parseDate, toISODate } from './dates'

const MINUTES_PER_DAY = 24 * 60

export function toMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number)
  return h * 60 + m
}

export function fromMinutes(minutes: number): string {
  const wrapped = ((minutes % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(Math.floor(wrapped / 60))}:${pad(wrapped % 60)}:00`
}

export function addMinutes(time: string, minutes: number): string {
  return fromMinutes(toMinutes(time) + minutes)
}

export function addDays(iso: string, days: number): string {
  const date = parseDate(iso)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

/** An end at or before the start means it finishes after midnight. */
export function endsNextDay(start: string, end: string): boolean {
  return toMinutes(end) <= toMinutes(start)
}

const clock = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })

/** "2:00 PM" or "14:00", following the viewer's locale. */
export function formatTime(time: string): string {
  const minutes = toMinutes(time)
  return clock.format(new Date(Date.UTC(2000, 0, 1, Math.floor(minutes / 60), minutes % 60)))
}

export function formatTimeRange(start: string | null, end: string | null): string {
  if (!start) return 'Any time'
  if (!end) return formatTime(start)
  return `${formatTime(start)} to ${formatTime(end)}${endsNextDay(start, end) ? ' (next day)' : ''}`
}

type TimedFields = { day: string | null; start_time: string | null; end_time: string | null }

/** Where an activity sits on the calendar. Without an end time it shows as one hour. */
export function eventRange(activity: TimedFields & { day: string }): { start: string; end?: string; allDay: boolean } {
  if (!activity.start_time) return { start: activity.day, allDay: true }
  const start = `${activity.day}T${activity.start_time.slice(0, 5)}:00`
  if (!activity.end_time) return { start, allDay: false }
  const endDay = endsNextDay(activity.start_time, activity.end_time) ? addDays(activity.day, 1) : activity.day
  return { start, end: `${endDay}T${activity.end_time.slice(0, 5)}:00`, allDay: false }
}

/** Back from the calendar, whose strings look like "2026-11-05T14:00:00Z" (or "2026-11-05" all day). */
export function fromCalendar(startStr: string, endStr: string | null, allDay: boolean): TimedFields & { day: string } {
  const day = startStr.slice(0, 10)
  if (allDay) return { day, start_time: null, end_time: null }
  const start_time = `${startStr.slice(11, 16)}:00`
  const end_time = endStr ? `${endStr.slice(11, 16)}:00` : null
  return { day, start_time, end_time: end_time === start_time ? null : end_time }
}

/** A sensible start for something new: after the day's last timed activity, else 10:00. */
export function suggestStart(activities: TimedFields[]): string {
  const ends = activities
    .filter((a) => a.start_time)
    .map((a) => {
      const start = toMinutes(a.start_time!)
      if (!a.end_time) return start + 60
      const end = toMinutes(a.end_time)
      return end <= start ? MINUTES_PER_DAY : end
    })
  if (ends.length === 0) return '10:00:00'
  const latest = Math.max(...ends)
  const rounded = Math.ceil(latest / 30) * 30
  return rounded >= 23 * 60 ? '10:00:00' : fromMinutes(rounded)
}
