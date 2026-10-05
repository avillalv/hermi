import { lazy, Suspense, useState, useSyncExternalStore } from "react"
import { Btn, Icon, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { endsNextDay, fromCalendar, fromMinutes, toMinutes } from "../../lib/itinerary-time"
import type { Item } from "./api"
import { Modal } from "./Modal"

const CalendarGrid = lazy(() => import("./CalendarGrid"))

/** A day and time change for one item. `day` null puts it back in Ideas. */
export type Change = { day: string | null; start_time: string | null; end_time: string | null }

/** The PATCH body for a change: an end time goes along only when the item had one or the change sets one. */
export const patchBody = (item: Pick<Item, "end_time">, ch: Change) => ({ day: ch.day, start_time: ch.start_time, ...(item.end_time || ch.end_time ? { end_time: ch.end_time } : {}) })

/** An end that would pass midnight (or land at or before the start) is capped at 23:59, because the server rejects an end before the start. */
export const capEnd = (start: string, end: string | null) => (end && (toMinutes(end) <= toMinutes(start) || end === "00:00:00" ? "23:59:00" : end))

/** A dragged block's new day and times from FullCalendar's strings. An item that had no end time keeps none. */
export function dropChange(item: Pick<Item, "end_time">, startStr: string, endStr: string | null, allDay: boolean): Change {
  const c = fromCalendar(startStr, endStr || null, allDay)
  return { day: c.day, start_time: c.start_time, end_time: c.start_time && item.end_time ? capEnd(c.start_time, c.end_time) : null }
}

const PHONE = "(max-width: 767px)"
const watch = (cb: () => void) => {
  const m = window.matchMedia?.(PHONE)
  m?.addEventListener("change", cb)
  return () => m?.removeEventListener("change", cb)
}
/** True on phone widths, where the calendar is a list and drag is off (05 4.7). */
const usePhone = () => useSyncExternalStore(watch, () => !!window.matchMedia?.(PHONE).matches)

const span = (i: Item): [number, number] => {
  const s = toMinutes(i.start_time!)
  return [s, i.end_time ? (endsNextDay(i.start_time!, i.end_time) ? 24 * 60 : toMinutes(i.end_time)) : s + 60]
}

/** Pairs of timed items on one day whose times overlap. An item without an end time counts as one hour. */
export function overlaps(items: Item[]): [Item, Item][] {
  const timed = items.filter((i) => i.start_time).sort((a, b) => toMinutes(a.start_time!) - toMinutes(b.start_time!) || a.id.localeCompare(b.id))
  const out: [Item, Item][] = []
  timed.forEach((a, n) => timed.slice(n + 1).forEach((b) => span(b)[0] < span(a)[1] && out.push([a, b])))
  return out
}

/** 05 6.12 Calendar view of one day: FullCalendar timeGridDay, or listWeek on phones. */
export function CalendarView({ day, items, canEdit, locked, onOpen, onChange }: { day: string | null; items: Item[]; canEdit: boolean; locked: boolean; onOpen: (item: Item) => void; onChange: (item: Item, ch: Change) => Promise<boolean> }) {
  const phone = usePhone()
  const lap = overlaps(items)
  if (!day) return <p className="h-soft plan__free">{t("plan.calNoDates")}</p>
  if (items.length === 0) return <p className="h-soft plan__free">{t("plan.calEmpty")}</p>
  return (
    <>
      <Suspense fallback={<div className="plan__skel" aria-hidden="true" />}>
        <CalendarGrid day={day} items={items} phone={phone} canEdit={canEdit} locked={locked} onOpen={onOpen} onChange={onChange} />
      </Suspense>
      {lap.length > 0 && (
        <ul className="plan__laps" aria-label={t("plan.overlapsAria")}>
          {lap.map(([a, b]) => (
            <li key={`${a.id}-${b.id}`} className="h-soft">
              <Icon name="circle-alert" size={16} />
              {t("plan.overlap", { a: a.title, b: b.title })}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

const fmt = new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" })
const dayText = (iso: string) => fmt.format(new Date(`${iso}T00:00:00Z`))

/** 05 4.7 "Move to..." for the calendar: a day and a start time. Moving the start keeps the item's length. */
export function CalendarMoveSheet({ item, days, onSave, onClose }: { item: Item; days: { day: string; n: number }[]; onSave: (ch: Change) => void; onClose: () => void }) {
  const [day, setDay] = useState(item.day ?? "")
  const [time, setTime] = useState(item.start_time?.slice(0, 5) ?? "")
  const start = day && time ? `${time}:00` : null
  const shift = item.start_time && item.end_time && start ? toMinutes(start) - toMinutes(item.start_time) : null
  const save = () => onSave({ day: day || null, start_time: start, end_time: shift === null || !start ? null : capEnd(start, fromMinutes(toMinutes(item.end_time!) + shift)) })
  return (
    <Modal title={t("plan.moveTitle", { title: item.title })} onClose={onClose}>
      <form className="plan__form" noValidate onSubmit={(e) => (e.preventDefault(), save())}>
        <div className="h-input">
          <label className="h-input__label" htmlFor="plan-cal-day">{t("plan.fieldDay")}</label>
          <select id="plan-cal-day" className="h-input__field" value={day} onChange={(e) => setDay(e.target.value)}>
            {days.map((d) => <option key={d.day} value={d.day}>{t("plan.dayChip", { n: d.n, date: dayText(d.day) })}</option>)}
            <option value="">{t("plan.ideas")}</option>
          </select>
        </div>
        <TextField label={t("plan.fieldTime")} type="time" value={day ? time : ""} disabled={!day} onChange={(e) => setTime(e.target.value)} />
        <Btn variant="primary" type="submit">{t("plan.saveMove")}</Btn>
        <Btn variant="text" onClick={onClose}>{t("plan.close")}</Btn>
      </form>
    </Modal>
  )
}
