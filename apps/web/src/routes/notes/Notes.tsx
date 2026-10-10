import { Fragment, useState } from "react"
import { Navigate, useNavigate, useParams } from "react-router"
import { EmptyState } from "../../components/EmptyState"
import { QueryError } from "../../components/ErrorState"
import { Skeleton } from "../../components/Skeleton"
import { SourceChip } from "../../components/SourceChip"
import { EvidenceLabel } from "../../components/evidence"
import { Avatar, Btn, Icon, SegItem, SegmentedControl, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { AppShell } from "../../shell/AppShell"
import { useAuth } from "../auth/authStore"
import { Modal } from "../itinerary/Modal"
import { useTrip } from "../trips/api"
import { tripStrip } from "../trips/TripStrip"
import "../trips/trips.css"
import "../itinerary/plan.css"
import { useMe } from "../lodging/api"
import { createNote, deleteNote, patchNote, useEvidence, useNotes, type Note } from "./api"
import "./notes.css"

const day = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" })
const URL_RE = /(https?:\/\/[^\s<>"]+)/g
const initials = (name: string) => name.slice(0, 2).toUpperCase()
const scopeOf = (n: Note) => (n.item_id ? (n.day ? t("notes.scopeItemDay", { date: day(n.day) }) : t("notes.scopeItem")) : n.day ? t("notes.scopeDay", { date: day(n.day) }) : t("notes.scopeTrip"))
const scopeKind = (n: Note) => (n.item_id ? "item" : n.day ? "day" : "trip")

/** Links in a note's text become anchors (http and https only); the rest stays text and is never truncated. */
function Linked({ text }: { text: string }) {
  return (
    <>
      {text.split(URL_RE).map((part, i) =>
        i % 2 === 1 ? (
          <a key={i} href={part} target="_blank" rel="noopener noreferrer">{part}</a>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  )
}

function AddNote({ tripId, onClose }: { tripId: string; onClose: () => void }) {
  const [body, setBody] = useState("")
  const [source, setSource] = useState("")
  const [priv, setPriv] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    if (!body.trim()) return setError(t("notes.bodyRequired"))
    setError(null)
    setBusy(true)
    const link = source.trim()
    const r = await createNote(tripId, { body: body.trim(), is_private: priv, ...(link ? { source_url: link } : {}) })
    setBusy(false)
    if (!r.ok) return setError(r.reason === "forbidden" ? t("notes.forbidden") : t("notes.saveFailed"))
    track("note_added", { scope: "trip", private: priv })
    onClose()
  }
  return (
    <Modal title={t("notes.addTitle")} onClose={onClose}>
      <form className="plan__form" noValidate onSubmit={(ev) => (ev.preventDefault(), void submit())}>
        <TextField label={t("notes.fieldBody")} value={body} error={error && !body.trim() ? error : undefined} maxLength={10000} autoComplete="off" onChange={(ev) => setBody(ev.target.value)} />
        <TextField label={t("notes.fieldSource")} type="text" inputMode="url" autoComplete="off" spellCheck={false} value={source} helper={t("notes.sourceHelp")} onChange={(ev) => setSource(ev.target.value)} />
        <label className="notes__toggle">
          <input type="checkbox" checked={priv} onChange={(ev) => setPriv(ev.target.checked)} aria-label={t("notes.privateToggle")} />
          <span>
            <Icon name="lock" size={16} /> {t("notes.privateToggle")}
            <span className="h-soft notes__help">{t("notes.privateHelp")}</span>
          </span>
        </label>
        {error && body.trim() && (
          <p role="alert" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {error}
          </p>
        )}
        <Btn variant="primary" type="submit" busy={busy}>{t("notes.save")}</Btn>
        <Btn variant="text" onClick={onClose}>{t("notes.close")}</Btn>
      </form>
    </Modal>
  )
}

function NoteRow({ note, canEdit, onFail, tripId }: { note: Note; canEdit: boolean; onFail: (reason: string) => void; tripId: string }) {
  const name = note.author?.display_name ?? t("notes.formerMember")
  const [confirm, setConfirm] = useState(false)
  const label = note.title || note.body.slice(0, 40) || t("notes.untitled")
  const run = async (p: Promise<{ ok: boolean; reason?: string }>) => {
    const r = await p
    if (!r.ok) onFail(r.reason ?? "failed")
  }
  return (
    <article className="notes__item" aria-label={`${t("notes.by", { name })}, ${scopeOf(note)}`}>
      <div className="notes__head">
        <Avatar tone="t1" size="sm">{initials(name)}</Avatar>
        <span className="h-soft">{t("notes.by", { name })}</span>
        <span className="h-label notes__scope" data-scope={scopeKind(note)}>{scopeOf(note)}</span>
        {note.is_private && (
          <span className="h-chip notes__private">
            <Icon name="lock" size={14} />
            {t("notes.private")}
          </span>
        )}
        {note.pinned && <span className="h-chip">{t("notes.pinned")}</span>}
      </div>
      <p className="notes__body"><Linked text={note.body} /></p>
      {note.sources.map((s) => (
        <SourceChip key={s.url} url={s.url} site={s.site} checkedAt={note.checked_at} stale={note.stale} agent={false} onOpen={() => track("evidence_opened")} />
      ))}
      {canEdit && (
        <>
        <div className="notes__actions">
          <Btn variant="text" mod={["sm"]} aria-pressed={note.pinned} aria-label={t(note.pinned ? "notes.unpinAria" : "notes.pinAria", { title: label })} onClick={() => void run(patchNote(tripId, note, { pinned: !note.pinned }))}>
            {t(note.pinned ? "notes.unpin" : "notes.pin")}
          </Btn>
          <Btn variant="text" mod={["sm"]} aria-label={t("notes.deleteAria", { title: label })} onClick={() => setConfirm(true)}>{t("notes.delete")}</Btn>
        </div>
        {confirm && (
          <Modal title={t("notes.confirmTitle")} onClose={() => setConfirm(false)}>
            <div className="plan__form">
              <Btn variant="primary" className="notes__danger" onClick={() => { setConfirm(false); void run(deleteNote(tripId, note.id)) }}>{t("notes.deleteConfirm")}</Btn>
              <Btn variant="secondary" onClick={() => setConfirm(false)}>{t("notes.cancel")}</Btn>
            </div>
          </Modal>
        )}
        </>
      )}
    </article>
  )
}

/** One finding: its source chip, and a button that loads the saved excerpt (04 5.14 evidence). */
function FindingRow({ note }: { note: Note }) {
  const [open, setOpen] = useState(false)
  const ev = useEvidence(note.id, open)
  const site = note.sources[0]?.site ?? note.title
  return (
    <article className="notes__item" aria-label={note.title}>
      <p className="notes__body"><Linked text={note.body} /></p>
      {note.sources.length === 0 && <EvidenceLabel kind="note" url="" />}
      {note.sources.map((s) => (
        <EvidenceLabel key={s.url} kind="note" url={s.url} site={s.site} checkedAt={note.checked_at} stale={note.stale} onOpen={() => track("evidence_opened")} />
      ))}
      <Btn variant="text" mod={["sm"]} aria-expanded={open} onClick={() => setOpen(!open)}>{t("notes.showMore")}</Btn>
      {open && ev.isPending && <p className="h-soft" aria-live="polite">{t("notes.loading")}</p>}
      {open && ev.isError && <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{t("notes.evidenceFailed")}</p>}
      {open && ev.data && (
        <blockquote className="notes__quote" aria-label={t("notes.excerptFor", { site: site ?? "" })}>
          {ev.data.excerpt ?? t("notes.noExcerpt")}
        </blockquote>
      )}
    </article>
  )
}

/** 05 6.18 Notes and evidence. shortcut: offline, adding is disabled (no offline queue exists yet; upgrade: WF-089). "Research this" is omitted until an AI research endpoint exists. */
export function Notes() {
  const { token } = useAuth()
  const { id = "" } = useParams()
  const nav = useNavigate()
  const online = useOnline()
  const trip = useTrip(id, !!token)
  const me = useMe(!!token)
  const list = useNotes(id, !!token)
  const [view, setView] = useState<"notes" | "found">("notes")
  const [adding, setAdding] = useState(false)
  const [fail, setFail] = useState<string | null>(null)
  if (!token) return <Navigate to="/welcome" replace />

  const canEdit = !!trip.data && trip.data.my_role !== "viewer"
  const items = list.data?.items ?? []
  const mine = items.filter((n) => n.kind === "user").sort((a, b) => b.created_at.localeCompare(a.created_at))
  const found = items.filter((n) => n.kind === "agent")
  const groups = found.reduce<[string, Note[]][]>((g, n) => {
    const k = n.title || t("notes.topic")
    const hit = g.find(([x]) => x === k)
    if (hit) hit[1].push(n)
    else g.push([k, [n]])
    return g
  }, [])
  const failed = (list.isError && !list.data) || trip.isError
  const pending = !failed && (list.isPending || trip.isPending)
  const ready = !failed && !pending
  const retry = () => void Promise.all([list.refetch(), trip.refetch()])
  const onFail = (reason: string) => setFail(reason === "forbidden" ? t("notes.forbidden") : reason === "conflict" ? t("notes.conflict") : t("notes.saveFailed"))
  const addBtn = (
    <Btn variant="primary" disabled={!online} onClick={() => setAdding(true)}>{t("notes.add")}</Btn>
  )

  return (
    <AppShell active="trips" strip={tripStrip(nav, id, "overview")}>
      <div className="overview">
        {!online && (
          <p role="status" className="h-soft trips__note">
            <Icon name="circle-alert" size={16} />
            {t("notes.offline")}
          </p>
        )}
        <h1 className="h-sr-only">{t("notes.title")}</h1>
        <div className="h-row">
          <SegmentedControl narrow aria-label={t("notes.views")}>
            <SegItem selected={view === "notes"} onClick={() => setView("notes")}>{t("notes.mine")}</SegItem>
            <SegItem selected={view === "found"} onClick={() => setView("found")}>{t("notes.found")}</SegItem>
          </SegmentedControl>
          {canEdit && ready && mine.length > 0 && view === "notes" && addBtn}
        </div>
        {trip.data && !canEdit && <p className="h-soft">{t("notes.viewerNote")}</p>}
        {fail && (
          <p role="alert" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {fail}
          </p>
        )}
        {pending && <Skeleton shape="lines" onRetry={retry} />}
        {failed && <QueryError error={trip.error ?? list.error} message={t("notes.error")} onRetry={retry} />}
        {ready && view === "notes" && (mine.length === 0 ? (
          <EmptyState
            icon="pencil"
            title={t("notes.emptyTitle")}
            body={t("notes.emptyBody")}
            action={canEdit && online ? { label: t("notes.add"), onClick: () => setAdding(true) } : undefined}
          />
        ) : (
          <div className="h-stack">{mine.map((n) => <NoteRow key={n.id} note={n} canEdit={canEdit && (trip.data?.my_role === "owner" || (!!me.data && n.author?.id === me.data.id))} tripId={id} onFail={onFail} />)}</div>
        ))}
        {ready && view === "found" && (groups.length === 0 ? (
          <p className="h-soft">{t("notes.foundEmpty")}</p>
        ) : (
          groups.map(([topic, rows]) => (
            <section key={topic} className="h-stack" aria-label={topic}>
              <h2 className="h-label">{topic}</h2>
              {rows.map((n) => <FindingRow key={n.id} note={n} />)}
            </section>
          ))
        ))}
      </div>
      {adding && <AddNote tripId={id} onClose={() => setAdding(false)} />}
    </AppShell>
  )
}
