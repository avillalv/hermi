import { Fragment, useEffect, useState, type DragEvent, type KeyboardEvent } from "react"
import { Navigate, useNavigate, useParams } from "react-router"
import { EmptyState } from "../../components/EmptyState"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { Btn, DayChip, DayChips, Icon, SegItem, SegmentedControl, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { formatTimeRange } from "../../lib/itinerary-time"
import { track, firstItem } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { useTrip } from "../trips/api"
import { tripStrip } from "../trips/TripStrip"
import "../trips/trips.css"
import { CATEGORIES, createItem, downloadIcs, moveItem, updateItem, useDays, useItems, type Category, type Item } from "./api"
import { CalendarMoveSheet, CalendarView, patchBody, type Change } from "./CalendarView"
import { AddActivity } from "../places/AddActivity"
import { PlacesMap } from "../places/PlacesMap"
import { dayText, GROUP, ICON, IDEAS, inOrder } from "./meta"
import { Modal } from "./Modal"
import "./plan.css"


/** Today as a calendar day at the trip's first destination, else the device's day. */
function today(timeZone: string | null | undefined): string {
  const opts = { year: "numeric", month: "2-digit", day: "2-digit" } as const
  try {
    return new Intl.DateTimeFormat("en-CA", { ...opts, timeZone: timeZone ?? undefined }).format(new Date())
  } catch {
    return new Intl.DateTimeFormat("en-CA", opts).format(new Date())
  }
}

type Target = { day: string | null; before_id: string | null }
type Method = "drag" | "move_to_sheet" | "actions"
type Conflict = { item: Item; to: Target; where: string; method: Method; change?: Change }
type NumberedDay = { day: string; n: number }

/** The server orders by start time first (04 5.10), so two items swap places only when they start at the same time (05 4.8). */
const sameSlot = (a: Item | undefined, b: Item) => !!a && a.start_time === b.start_time

/** "9:00 AM" into the clock and the AM or PM line the kit timeline stacks. */
function clockParts(item: Item): [string, string] {
  if (!item.start_time) return [t("plan.anyTime"), ""]
  const text = formatTimeRange(item.start_time, null)
  const m = /^(.*?)\s*(AM|PM)$/i.exec(text)
  return m ? [m[1], m[2]] : [text, ""]
}

function ItemRow({ item, list, index, canEdit, busy, showBy, onMove, onOpen, dragId, onDragId }: {
  item: Item; list: Item[]; index: number; canEdit: boolean; busy: boolean; showBy: boolean
  onMove: (item: Item, to: Target, method: Method) => void; onOpen: (item: Item) => void; dragId: string | null; onDragId: (id: string | null) => void
}) {
  const [over, setOver] = useState(false)
  const draggable = canEdit && !busy
  const [clock, ampm] = clockParts(item)
  const stub = canEdit || showBy
  return (
    <li
      className={`h-timeline__row h-timeline__row--${GROUP[item.category]}${dragId === item.id ? " plan__lifted" : ""}${over ? " plan__over" : ""}`}
      draggable={draggable}
      onDragStart={(e) => {
        if (!draggable) return e.preventDefault()
        e.dataTransfer?.setData("text/plain", item.id)
        if (e.dataTransfer) e.dataTransfer.effectAllowed = "move"
        onDragId(item.id)
      }}
      onDragEnd={() => onDragId(null)}
      onDragOver={(e) => {
        if (!dragId || dragId === item.id) return
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e: DragEvent) => {
        e.preventDefault()
        setOver(false)
        const moved = list.find((i) => i.id === dragId)
        onDragId(null)
        if (moved && moved.id !== item.id) onMove(moved, { day: item.day, before_id: item.id }, "drag")
      }}
    >
      <div className="h-timeline__time">
        <span className="h-timeline__clock">{clock}</span>
        {ampm && <span className="h-timeline__ampm">{ampm}</span>}
      </div>
      <span className="h-timeline__node" aria-hidden="true">{index + 1}</span>
      <div className={`h-ticket h-ticket--side${stub ? "" : " plan__nostub"}`}>
        <div className="h-ticket__card">
          <div className="h-ticket__body">
            <h3 className="h-timeline__title">{item.title}</h3>
            <span className="h-timeline__meta">
              <Icon name={ICON[item.category]} size={16} />
              {t(`plan.cat.${item.category}`)}
            </span>
          </div>
          {stub && (
            <div className="h-ticket__stub">
              <span className="h-ticket__tear" aria-hidden="true" />
              {showBy && item.added_by?.display_name && (
                <>
                  <span className="h-label">{t("plan.addedBy")}</span>
                  <span className="h-timeline__by">{item.added_by.display_name}</span>
                </>
              )}
              {canEdit && (
                <Btn variant="text" mod={["sm"]} disabled={busy} aria-label={t("plan.moveAria", { title: item.title })} onClick={() => onOpen(item)}>
                  {t("plan.move")}
                </Btn>
              )}
            </div>
          )}
        </div>
      </div>
    </li>
  )
}

/** 05 4.7 Move-to sheet: Move up, Move down and Move to day. Up and down are for neighbors that start at the same time. */
function MoveSheet({ item, list, days, onMove, onClose }: { item: Item; list: Item[]; days: NumberedDay[]; onMove: (item: Item, to: Target, method: Method) => void; onClose: () => void }) {
  const i = list.findIndex((x) => x.id === item.id)
  const prev = list[i - 1]
  const next = list[i + 1]
  const canUp = sameSlot(prev, item)
  const canDown = sameSlot(next, item)
  const blocked = (!!prev && !canUp) || (!!next && !canDown)
  return (
    <Modal title={t("plan.moveTitle", { title: item.title })} onClose={onClose}>
      <Btn variant="secondary" disabled={!canUp} aria-label={t("plan.moveUpAria", { title: item.title })} onClick={() => onMove(item, { day: item.day, before_id: prev.id }, "actions")}>
        <Icon name="arrow-up" size={16} />
        {t("plan.moveUp")}
      </Btn>
      <Btn variant="secondary" disabled={!canDown} aria-label={t("plan.moveDownAria", { title: item.title })} onClick={() => onMove(item, { day: item.day, before_id: list[i + 2]?.id ?? null }, "actions")}>
        <Icon name="arrow-down" size={16} />
        {t("plan.moveDown")}
      </Btn>
      {blocked && <p className="h-soft">{t("plan.sameTime")}</p>}
      <div className="h-input">
        <label className="h-input__label" htmlFor="plan-move-day">{t("plan.moveToDay")}</label>
        <select
          id="plan-move-day"
          className="h-input__field"
          aria-label={t("plan.moveToAria", { title: item.title })}
          value=""
          onChange={(e) => {
            const v = e.target.value
            if (v) onMove(item, { day: v === IDEAS ? null : v, before_id: null }, "move_to_sheet")
          }}
        >
          <option value="">{t("plan.moveToDay")}</option>
          {days.filter((d) => d.day !== item.day).map((d) => (
            <option key={d.day} value={d.day}>{t("plan.dayChip", { n: d.n, date: dayText(d.day) })}</option>
          ))}
          {item.day !== null && <option value={IDEAS}>{t("plan.ideas")}</option>}
        </select>
      </div>
      <Btn variant="text" onClick={onClose}>{t("plan.close")}</Btn>
    </Modal>
  )
}

function ConflictSheet({ c, onKeep, onTheirs, onDismiss, busy }: { c: Conflict; onKeep: () => void; onTheirs: () => void; onDismiss: () => void; busy: boolean }) {
  const them = c.item
  return (
    <Modal title={t("plan.conflict.title")} onClose={onDismiss}>
      <div className="plan__versions">
        <section aria-label={t("plan.conflict.theirs")} className="h-listcard plan__version">
          <span className="h-label">{t("plan.conflict.theirs")}</span>
          <strong>{them.title}</strong>
          <span className="h-soft">{them.day ? dayText(them.day) : t("plan.ideas")}{them.start_time ? `, ${formatTimeRange(them.start_time, them.end_time)}` : ""}</span>
        </section>
        <section aria-label={t("plan.conflict.mine")} className="h-listcard plan__version">
          <span className="h-label">{t("plan.conflict.mine")}</span>
          <strong>{t("plan.conflict.mineMove", { where: c.where })}</strong>
        </section>
      </div>
      <Btn variant="primary" busy={busy} onClick={onKeep}>{t("plan.conflict.keepMine")}</Btn>
      <Btn variant="secondary" disabled={busy} onClick={onTheirs}>{t("plan.conflict.useTheirs")}</Btn>
    </Modal>
  )
}

function AddItem({ tripId, days, start, canWrite, onClose, onAdded }: { tripId: string; days: NumberedDay[]; start: string; canWrite: boolean; onClose: () => void; onAdded: (day: string, title: string) => void }) {
  const [title, setTitle] = useState("")
  const [category, setCategory] = useState<Category>("sights")
  const [day, setDay] = useState(start)
  const [time, setTime] = useState("")
  const [error, setError] = useState<string>()
  const [failed, setFailed] = useState<"failed" | "forbidden" | null>(null)
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    if (!title.trim()) return setError(t("plan.titleRequired"))
    setError(undefined)
    setBusy(true)
    const scheduled = day !== IDEAS
    const r = await createItem(tripId, { title: title.trim(), category, day: scheduled ? day : null, ...(scheduled && time ? { start_time: `${time}:00` } : {}) })
    setBusy(false)
    if (!r.ok) return setFailed(r.reason === "forbidden" ? "forbidden" : "failed")
    track("itinerary_item_added", { category, source: "manual" })
    firstItem()
    onAdded(day, title.trim())
  }
  return (
    <Modal title={t("plan.addTitle")} onClose={onClose}>
      <form className="plan__form" noValidate onSubmit={(e) => (e.preventDefault(), void submit())}>
        <TextField label={t("plan.fieldTitle")} value={title} error={error} maxLength={200} autoComplete="off" onChange={(e) => setTitle(e.target.value)} />
        <div className="h-input">
          <label className="h-input__label" htmlFor="plan-cat">{t("plan.fieldCategory")}</label>
          <select id="plan-cat" className="h-input__field" value={category} onChange={(e) => setCategory(e.target.value as Category)}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{t(`plan.cat.${c}`)}</option>)}
          </select>
        </div>
        <div className="h-input">
          <label className="h-input__label" htmlFor="plan-day">{t("plan.fieldDay")}</label>
          <select id="plan-day" className="h-input__field" value={day} onChange={(e) => setDay(e.target.value)}>
            {days.map((d) => <option key={d.day} value={d.day}>{t("plan.dayChip", { n: d.n, date: dayText(d.day) })}</option>)}
            <option value={IDEAS}>{t("plan.ideas")}</option>
          </select>
        </div>
        <TextField label={t("plan.fieldTime")} type="time" value={day === IDEAS ? "" : time} disabled={day === IDEAS} helper={t("plan.fieldTimeHelp")} onChange={(e) => setTime(e.target.value)} />
        {failed && <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{t(failed === "forbidden" ? "plan.forbidden" : "plan.addFailed")}</p>}
        <Btn variant="primary" type="submit" busy={busy} disabled={!canWrite}>{t("plan.save")}</Btn>
        <Btn variant="text" onClick={onClose}>{t("plan.close")}</Btn>
      </form>
    </Modal>
  )
}

/** 05 6.12 Plan: the Days, Calendar and Map views, and the Add sheet (05 6.13). */
export function Plan() {
  const { token } = useAuth()
  const { id = "" } = useParams()
  const nav = useNavigate()
  const online = useOnline()
  const trip = useTrip(id, !!token)
  const days = useDays(id, !!token)
  const items = useItems(id, !!token)
  const [view, setView] = useState<"days" | "calendar" | "map">("days")
  const [picked, setPicked] = useState<string | null>(null)
  const [adding, setAdding] = useState<"search" | "custom" | null>(null)
  const [moving, setMoving] = useState<string | null>(null)
  const [dragId, setDragId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [conflict, setConflict] = useState<Conflict | null>(null)
  const [note, setNote] = useState<{ kind: "ok" | "error"; text: string } | null>(null)
  useEffect(() => void track("plan_viewed", { mode: view }), [view])
  if (!token) return <Navigate to="/welcome" replace />

  const canEdit = !!trip.data && trip.data.my_role !== "viewer"
  const numbered: NumberedDay[] = (days.data ?? []).map((d, i) => ({ day: d.day, n: i + 1 }))
  const all = items.data ?? []
  const todayIso = today(trip.data?.destinations.find((d) => d.timezone)?.timezone ?? days.data?.find((d) => d.timezone)?.timezone)
  const first = numbered.find((d) => d.day === todayIso)?.day ?? numbered[0]?.day ?? IDEAS
  const sel0 = picked && (picked === IDEAS || numbered.some((d) => d.day === picked)) ? picked : first
  const sel = view === "calendar" && sel0 === IDEAS && numbered[0] ? numbered[0].day : sel0 // Ideas have no time, so the calendar has no Ideas chip
  const list = inOrder(all, sel === IDEAS ? null : sel)
  const short = (day: string | null) => (day ? `${t("plan.dayLabel")} ${numbered.find((d) => d.day === day)?.n ?? ""}`.trim() : t("plan.ideas"))
  const showBy = (trip.data?.travelers.length ?? 0) >= 2 // 05 4.8: a solo trip hides "Added by"
  const moveItemRow = moving ? all.find((i) => i.id === moving) : undefined

  const move = async (item: Item, to: Target, method: Method, version = item.version) => {
    if (!canEdit || !online || busy) return
    if (method === "drag" && to.before_id) {
      const target = all.find((i) => i.id === to.before_id)
      if (target && target.day === item.day && !sameSlot(target, item)) return setNote({ kind: "error", text: t("plan.dropBlocked") })
    }
    setBusy(true)
    setNote(null)
    const r = await moveItem(id, { id: item.id, version }, to)
    setBusy(false)
    setMoving(null)
    if (r.ok) {
      track("itinerary_item_moved", { method })
      setConflict(null)
      return setNote({ kind: "ok", text: t("plan.moved", { title: item.title }) })
    }
    if (r.reason === "conflict" && r.current) return setConflict({ item: r.current, to, where: short(to.day), method })
    setNote({ kind: "error", text: t(r.reason === "forbidden" ? "plan.forbidden" : "plan.moveFailed") }) // a 409 with no latest row falls here
  }
  /** Calendar edits: a day or time change by PATCH. Resolves true when saved, so a dragged block can snap back on false. */
  const reschedule = async (item: Item, change: Change, method: Method): Promise<boolean> => {
    if (!canEdit || !online || busy) return false
    setBusy(true)
    setNote(null)
    const r = await updateItem(id, item, patchBody(item, change))
    setBusy(false)
    setMoving(null)
    if (r.ok) {
      track("itinerary_item_moved", { method })
      setConflict(null)
      setNote({ kind: "ok", text: t("plan.moved", { title: item.title }) })
      return true
    }
    const where = `${short(change.day)}${change.start_time ? `, ${formatTimeRange(change.start_time, null)}` : ""}`
    if (r.reason === "conflict" && r.current) setConflict({ item: r.current, to: { day: change.day, before_id: null }, where, method, change })
    else setNote({ kind: "error", text: t(r.reason === "forbidden" ? "plan.forbidden" : "plan.moveFailed") })
    return false
  }
  const keepMine = async () => {
    if (!conflict) return
    track("edit_conflict_shown", { resolution: "keep_mine" })
    const { item, to, method, change } = conflict
    setConflict(null)
    if (change) await reschedule(item, change, method)
    else await move(item, to, method, item.version)
  }
  const resolve = (resolution: "use_theirs" | "dismissed") => {
    track("edit_conflict_shown", { resolution })
    setConflict(null)
  }

  const failed = (days.isError && !days.data) || (items.isError && !items.data) || trip.isError
  const pending = !failed && (days.isPending || items.isPending || trip.isPending)
  const empty = !failed && !pending && all.length === 0
  const retry = () => void Promise.all([days.refetch(), items.refetch(), trip.refetch()])
  const chips = [
    ...numbered.map((d) => ({ key: d.day, label: `D${d.n}`, aria: t("plan.dayChip", { n: d.n, date: dayText(d.day) }), to: d.day as string | null })),
    ...(view === "days" ? [{ key: IDEAS, label: t("plan.ideas"), aria: t("plan.ideasAria"), to: null as string | null }] : []),
  ]
  const pick = (key: string) => {
    setPicked(key)
    document.getElementById(`plan-tab-${key}`)?.focus()
  }
  const tabKeys = (i: number) => (e: KeyboardEvent) => {
    const n = chips.length
    const to = e.key === "ArrowRight" ? (i + 1) % n : e.key === "ArrowLeft" ? (i - 1 + n) % n : e.key === "Home" ? 0 : e.key === "End" ? n - 1 : -1
    if (to < 0) return
    e.preventDefault()
    pick(chips[to].key)
  }

  return (
    <AppShell active="trips" strip={tripStrip(nav, id, "plan")}>
      <div className="overview">
        {!online && (
          <p role="status" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("plan.offline")}
          </p>
        )}
        <div className="plan__bar">
          <h1 className="h-title">{t("plan.title")}</h1>
          <div className="plan__bar-actions">
            <Btn variant="secondary" mod={["sm"]} disabled={!online} onClick={async () => setNote((await downloadIcs(id)) ? null : { kind: "error", text: t("plan.exportFailed") })}>
              {t("plan.export")}
            </Btn>
            {canEdit && (
              <Btn variant="primary" mod={["sm"]} disabled={!online} onClick={() => setAdding("search")}>
                <Icon name="plus" size={18} />
                {t("plan.add")}
              </Btn>
            )}
          </div>
        </div>
        {!failed && !pending && !empty && (
          <SegmentedControl aria-label={t("plan.viewTabs")}>
            <SegItem selected={view === "days"} onClick={() => setView("days")}>{t("plan.viewDays")}</SegItem>
            <SegItem selected={view === "calendar"} onClick={() => setView("calendar")}>{t("plan.viewCalendar")}</SegItem>
            <SegItem selected={view === "map"} onClick={() => setView("map")}>{t("plan.viewMap")}</SegItem>
          </SegmentedControl>
        )}
        {trip.data && !canEdit && <p className="h-soft">{t("plan.viewerNote")}</p>}
        {note && (
          <p role={note.kind === "error" ? "alert" : "status"} className={note.kind === "error" ? "h-input__error trips__note" : "trips__note"}>
            {note.kind === "error" && <Icon name="circle-alert" size={16} />}
            {note.text}
          </p>
        )}
        {pending && <Skeleton shape="dayCard" count={3} onRetry={retry} />}
        {failed && <QueryError error={trip.error ?? days.error ?? items.error} message={t("plan.error")} onRetry={retry} />}
        {empty && (
          <EmptyState
            icon="compass"
            title={t("plan.emptyTripTitle")}
            body={t("plan.emptyTripBody")}
            action={canEdit && online ? { label: t("plan.addFirst"), onClick: () => setAdding("search") } : undefined}
          />
        )}
        {!failed && !pending && !empty && view === "map" && <PlacesMap items={all} days={numbered} online={online} />}
        {!failed && !pending && !empty && view !== "map" && (
          <>
            <DayChips aria-label={t("plan.daysAria")}>
              {chips.map((c, i) => (
                <DayChip
                  key={c.key}
                  id={`plan-tab-${c.key}`}
                  href={`#${c.key}`}
                  selected={sel === c.key}
                  current={c.to === todayIso}
                  tabIndex={sel === c.key ? 0 : -1}
                  aria-controls="plan-panel"
                  aria-label={c.aria}
                  onClick={(e) => (e.preventDefault(), setPicked(c.key))}
                  onKeyDown={tabKeys(i)}
                  onDragOver={(e) => canEdit && dragId && e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault()
                    const moved = all.find((x) => x.id === dragId)
                    setDragId(null)
                    if (moved && moved.day !== c.to) void move(moved, { day: c.to, before_id: null }, "drag")
                  }}
                >
                  {c.label}
                </DayChip>
              ))}
            </DayChips>
            <div role="tabpanel" id="plan-panel" aria-labelledby={`plan-tab-${sel}`} className="overview">
              {sel === IDEAS ? (
                <h2 className="h-title">{t("plan.ideasTitle")}</h2>
              ) : (
                <div className="h-dayhead">
                  <div className="h-dayhead__col h-dayhead__col--num">
                    <span className="h-label">{t("plan.dayLabel")}</span>
                    <h2 className="h-dayhead__num">{numbered.find((d) => d.day === sel)?.n}</h2>
                  </div>
                  <div className="h-dayhead__col">
                    <span className="h-label">{t("plan.dateLabel")}</span>
                    <span className="h-dayhead__date">{dayText(sel)}</span>
                    <span className="h-dayhead__place">{days.data?.find((d) => d.day === sel)?.destination_name}</span>
                  </div>
                </div>
              )}
              {view === "calendar" ? (
                <CalendarView day={sel === IDEAS ? null : sel} items={list} canEdit={canEdit} locked={busy || !online} onOpen={(m) => setMoving(m.id)} onChange={(m, ch) => reschedule(m, ch, "drag")} />
              ) : (
                <>
              {canEdit && list.length > 1 && <p className="h-soft">{t("plan.dragHint")}</p>}
              {list.length === 0 ? (
                <p className="h-soft plan__free">{t(sel === IDEAS ? "plan.emptyIdeas" : "plan.emptyDay")}</p>
              ) : (
                <ol className="h-timeline plan__timeline" aria-label={sel === IDEAS ? t("plan.ideas") : `${t("plan.dayLabel")} ${numbered.find((d) => d.day === sel)?.n}`}>
                  {list.map((it, i) => (
                    <Fragment key={it.id}>
                      {i > 0 && (
                        <li className="h-timeline__row h-timeline__row--link-short" aria-hidden="true">
                          <span />
                          <span className="h-timeline__spine" />
                          <span />
                        </li>
                      )}
                      <ItemRow item={it} list={list} index={i} canEdit={canEdit} busy={busy || !online} showBy={showBy} onMove={(m, to, how) => void move(m, to, how)} onOpen={(m) => setMoving(m.id)} dragId={dragId} onDragId={setDragId} />
                    </Fragment>
                  ))}
                  {sel !== IDEAS && canEdit && (
                    <>
                      <li className="h-timeline__row h-timeline__row--link-end" aria-hidden="true">
                        <span />
                        <span className="h-timeline__spine" />
                        <span />
                      </li>
                      <li className="h-timeline__row h-timeline__row--add">
                        <span />
                        <span className="h-timeline__node h-timeline__node--open" aria-hidden="true" />
                        <Btn variant="secondary" mod={["sm"]} disabled={!online} onClick={() => setAdding("search")}>
                          <Icon name="plus" size={20} />
                          {t("plan.addToDay", { n: numbered.find((d) => d.day === sel)?.n ?? "" })}
                        </Btn>
                      </li>
                    </>
                  )}
                </ol>
              )}
                </>
              )}
            </div>
          </>
        )}
      </div>
      {adding === "search" && (
        <AddActivity
          tripId={id}
          days={numbered}
          start={sel}
          destination={trip.data?.destinations[0] ?? null}
          canWrite={canEdit && online}
          online={online}
          onClose={() => setAdding(null)}
          onCustom={() => setAdding("custom")}
          onAdded={(day, title) => {
            setAdding(null)
            setPicked(day)
            setNote({ kind: "ok", text: t("plan.added", { title }) })
          }}
        />
      )}
      {adding === "custom" && (
        <AddItem
          tripId={id}
          days={numbered}
          start={sel}
          canWrite={canEdit && online}
          onClose={() => setAdding(null)}
          onAdded={(day, title) => {
            setAdding(null)
            setPicked(day)
            setNote({ kind: "ok", text: t("plan.added", { title }) })
          }}
        />
      )}
      {moveItemRow && !conflict && view === "calendar" && <CalendarMoveSheet item={moveItemRow} days={numbered} onSave={(ch) => void reschedule(moveItemRow, ch, "move_to_sheet")} onClose={() => setMoving(null)} />}
      {moveItemRow && !conflict && view === "days" && <MoveSheet item={moveItemRow} list={list} days={numbered} onMove={(m, to, how) => void move(m, to, how)} onClose={() => setMoving(null)} />}
      {conflict && <ConflictSheet c={conflict} busy={busy} onKeep={() => void keepMine()} onTheirs={() => resolve("use_theirs")} onDismiss={() => resolve("dismissed")} />}
    </AppShell>
  )
}
