import FullCalendar, { type EventDisplayInfo } from "@fullcalendar/react"
import interactionPlugin from "@fullcalendar/react/interaction"
import listPlugin from "@fullcalendar/react/list"
import "@fullcalendar/react/skeleton.css"
import classicThemePlugin from "@fullcalendar/react/themes/classic"
import "@fullcalendar/react/themes/classic/theme.css"
import timeGridPlugin from "@fullcalendar/react/timegrid"
import "temporal-polyfill/global"
import { useMemo } from "react"
import { Btn, Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { eventRange, formatTimeRange, fromMinutes, toMinutes } from "../../lib/itinerary-time"
import type { Item } from "./api"
import { dropChange, type Change } from "./CalendarView"
import { GROUP, ICON } from "./meta"
import "./calendar.css"

type Props = { day: string; items: Item[]; phone: boolean; canEdit: boolean; locked: boolean; onOpen: (item: Item) => void; onChange: (item: Item, ch: Change) => Promise<boolean> }

/** A tinted block: group color edge, icon, title, mono time and category. Editors also get Move, the keyboard way to reschedule. */
function Block({ info, canEdit, locked, onOpen }: { info: EventDisplayInfo; canEdit: boolean; locked: boolean; onOpen: (item: Item) => void }) {
  const item = info.event.extendedProps.item as Item
  return (
    <div className={`plan__event h-timeline__row--${GROUP[item.category]}`} title={`${item.title}, ${formatTimeRange(item.start_time, item.end_time)}`}>
      <Icon name={ICON[item.category]} size={16} />
      <div className="plan__event-text">
        <span className="plan__event-title">{item.title}</span>
        <span className="plan__event-time">{item.start_time ? formatTimeRange(item.start_time, item.end_time) : t("plan.anyTime")}</span>
        <span className="plan__event-cat">{t(`plan.cat.${item.category}`)}</span>
      </div>
      {canEdit && (
        <Btn variant="text" mod={["sm"]} disabled={locked} aria-label={t("plan.moveAria", { title: item.title })} onClick={() => onOpen(item)}>
          {t("plan.move")}
        </Btn>
      )}
    </div>
  )
}

export default function CalendarGrid({ day, items, phone, canEdit, locked, onOpen, onChange }: Props) {
  const events = useMemo(
    () =>
      items.map((item) => ({
        id: item.id,
        title: item.title,
        ...eventRange({ ...item, day: item.day ?? day }),
        color: `color-mix(in oklab, var(--cat-${GROUP[item.category]}) 22%, var(--tp-sheet))`,
        contrastColor: "var(--tp-ink)",
        extendedProps: { item },
      })),
    [items, day],
  )
  const starts = items.filter((i) => i.start_time).map((i) => toMinutes(i.start_time!))
  const firstAt = starts.length ? Math.min(...starts) : 8 * 60
  const scrollTime = fromMinutes(Math.max(0, firstAt - 60)) // open on the first timed block, not on empty morning
  const drag = canEdit && !locked && !phone // 05 4.7: on phones drag is off and Move opens the sheet
  return (
    <div className="plan__cal">
      <FullCalendar
        key={`${day}-${phone}`}
        plugins={[timeGridPlugin, listPlugin, interactionPlugin, classicThemePlugin]}
        initialView={phone ? "listWeek" : "timeGridDay"}
        initialDate={day}
        headerToolbar={false}
        dayHeaders={false}
        timeZone="UTC"
        height="34rem"
        slotMinTime="00:00"
        slotMaxTime="24:00"
        scrollTime={scrollTime}
        slotDuration="00:30"
        snapDuration="00:15"
        slotHeaderFormat={{ hour: "numeric" }}
        allDayText={t("plan.anyTime")}
        nowIndicator={false}
        editable={drag}
        eventDurationEditable={false}
        longPressDelay={350}
        defaultTimedEventDuration="01:00"
        noEventsText={t("plan.calEmpty")}
        events={events}
        eventContent={(info) => <Block info={info} canEdit={canEdit} locked={locked} onOpen={onOpen} />}
        eventDrop={async (info) => {
          const item = info.event.extendedProps.item as Item
          if (!(await onChange(item, dropChange(item, info.event.startStr, info.event.endStr || null, info.event.allDay)))) info.revert()
        }}
      />
    </div>
  )
}
