import { useQuery } from "@tanstack/react-query"
import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"

// shortcut: hand-written from apps/api/hermi/modules/trips/notes.py until `npm run gen:api` is real (it is a stub today).
export type Source = { url: string; title: string | null; fetched_at: string; site: string | null }
export type Note = {
  id: string
  trip_id: string
  kind: "user" | "agent"
  title: string
  body: string
  pinned: boolean
  is_private: boolean
  day: string | null
  item_id: string | null
  version: number
  author: { id: string; display_name: string | null } | null
  sources: Source[]
  checked_at: string
  stale: boolean
  created_at: string
}
export type NotePage = { items: Note[]; has_more: boolean; next_cursor: string | null }
export type Evidence = { note_id: string; sources: Source[]; excerpt: string | null; checked_at: string; stale: boolean }
export type NoteIn = { body?: string; is_private?: boolean; pinned?: boolean; source_url?: string; day?: string; item_id?: string; version?: number }

const trip = (id: string) => `/v1/trips/${encodeURIComponent(id)}`
export const noteKey = (id: string, ...rest: string[]) => ["notes", id, ...rest]

export const useNotes = (id: string, on: boolean) =>
  useQuery(
    {
      queryKey: noteKey(id, "list"),
      enabled: on,
      retry: 1,
      queryFn: async () => {
        // shortcut: one page of up to 200 notes (the API maximum); a trip with more shows only the newest 200. Upgrade: follow next_cursor when a trip passes that.
        const r = await api.get<NotePage>(`${trip(id)}/notes`, { query: { limit: 200 } })
        if (r.error !== undefined || !r.data) throw new Error(`notes ${r.response.status}`)
        return r.data
      },
    },
    queryClient,
  )

export const useEvidence = (noteId: string, on: boolean) =>
  useQuery(
    {
      queryKey: ["notes", "evidence", noteId],
      enabled: on,
      retry: 1,
      queryFn: async () => {
        const r = await api.get<Evidence>(`/v1/notes/${encodeURIComponent(noteId)}/evidence`)
        if (r.error !== undefined || !r.data) throw new Error(`evidence ${r.response.status}`)
        return r.data
      },
    },
    queryClient,
  )

export type Outcome<T = unknown> = { ok: true; data: T } | { ok: false; reason: "conflict" | "forbidden" | "invalid" | "failed" }

async function send<T>(call: () => Promise<{ data?: T; error?: unknown; response: Response }>, id: string): Promise<Outcome<T>> {
  try {
    const r = await call()
    const s = r.response.status
    if (s === 409 || s === 412) return { ok: false, reason: "conflict" }
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (s === 422) return { ok: false, reason: "invalid" }
    if (r.error !== undefined) return { ok: false, reason: "failed" }
    await queryClient.invalidateQueries({ queryKey: noteKey(id) })
    return { ok: true, data: r.data as T }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

export const createNote = (tripId: string, body: NoteIn) => send<Note>(() => api.post<Note>(`${trip(tripId)}/notes`, body), tripId)
export const patchNote = (tripId: string, n: Pick<Note, "id" | "version">, body: NoteIn) =>
  send<Note>(() => api.patch<Note>(`/v1/notes/${encodeURIComponent(n.id)}`, { ...body, version: n.version }), tripId)
export const deleteNote = (tripId: string, id: string) => send<unknown>(() => api.delete<unknown>(`/v1/notes/${encodeURIComponent(id)}`), tripId)
