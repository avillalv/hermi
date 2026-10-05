import { useQuery } from "@tanstack/react-query"
import { queryClient } from "../../lib/queryClient"
import { ApiError } from "../../lib/api/client"
import { api } from "../auth/api"
import type { Trip } from "../trips/api"

// shortcut: hand-written from apps/api/hermi/modules/collaboration/schemas.py until gen:api is real.
export type Role = "owner" | "editor" | "viewer"
export type Member = { user_id: string; display_name: string | null; role: Role; person_id: string | null; joined_at: string }
export type Invite = { id: string; role: "editor" | "viewer"; email: string | null; url: string | null; uses_left: number; expires_at: string; status: "pending" | "used" | "expired" | "revoked" }
export type InvitePreview = { trip_name: string; cover_url: string | null; inviter_name: string; role: "editor" | "viewer" }
export type ShareLink = { id: string; url: string | null }

export type Result<T = unknown> = { ok: true; data: T } | { ok: false; reason: "paywall" | "cap" | "pending" | "forbidden" | "gone" | "member" | "failed"; tripId?: string }

const trip = (id: string, tail: string) => `/v1/trips/${encodeURIComponent(id)}${tail}`
const keys = (id: string) => ({ members: ["members", id], invites: ["invites", id] })

function useList<T>(key: unknown[], path: string, enabled: boolean) {
  return useQuery(
    {
      queryKey: key,
      enabled,
      queryFn: async () => {
        const r = await api.get<T[]>(path)
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )
}
export const useMembers = (id: string) => useList<Member>(keys(id).members, trip(id, "/members"), true)
/** Owner only on the API. */
export const useInvites = (id: string, enabled: boolean) => useList<Invite>(keys(id).invites, trip(id, "/invites"), enabled)

/** The collaborator cap for this trip: the plan's limit, or the larger cap of an active Trip Pass on it (04 5.19). */
export function useCollaboratorMax(tripId: string, enabled: boolean) {
  return useQuery(
    {
      queryKey: ["entitlements"],
      enabled,
      queryFn: async () => {
        const r = await api.get<{ limits: { collaborators?: number }; trip_passes: { trip_id: string | null; status: string; collaborators_max: number }[] }>("/v1/me/entitlements")
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        const passes = r.data.trip_passes.filter((p) => p.trip_id === tripId && p.status === "active").map((p) => p.collaborators_max)
        return Math.max(r.data.limits.collaborators ?? 1, ...passes)
      },
    },
    queryClient,
  ).data
}

type Send<T> = () => Promise<{ data?: T; error?: unknown; response: Response }>
async function write<T>(id: string | null, send: Send<T>): Promise<Result<T>> {
  try {
    const r = await send()
    const s = r.response.status
    const body = (r.error ?? {}) as { detail?: string; paywall?: unknown; trip_id?: string }
    if (s === 402) return { ok: false, reason: body.paywall ? "paywall" : "cap" }
    if (s === 429) return { ok: false, reason: /open invites/.test(body.detail ?? "") ? "pending" : "failed" }
    if (s === 403) return { ok: false, reason: "forbidden" }
    if (s === 410) return { ok: false, reason: "gone" }
    if (s === 409) return { ok: false, reason: "member", tripId: body.trip_id }
    if (r.error !== undefined) return { ok: false, reason: "failed" }
    if (id) await Promise.all([queryClient.invalidateQueries({ queryKey: keys(id).members }), queryClient.invalidateQueries({ queryKey: keys(id).invites }), queryClient.invalidateQueries({ queryKey: ["trip", id] })])
    return { ok: true, data: r.data as T }
  } catch {
    return { ok: false, reason: "failed" }
  }
}

export const createInvite = (id: string, role: "editor" | "viewer", email?: string) => write(id, () => api.post<Invite>(trip(id, "/invites"), { role, ...(email ? { email } : {}) }))
export const revokeInvite = (id: string, inviteId: string) => write(id, () => api.delete(trip(id, `/invites/${encodeURIComponent(inviteId)}`)))
export const setRole = (id: string, userId: string, role: "editor" | "viewer") => write(id, () => api.patch<Member>(trip(id, `/members/${encodeURIComponent(userId)}`), { role }))
export const removeMember = (id: string, userId: string) => write(id, () => api.delete(trip(id, `/members/${encodeURIComponent(userId)}`)))
export const leaveTrip = (id: string) => write(id, () => api.post(trip(id, "/leave")))
export const transferTrip = (id: string, newOwnerId: string) => write(id, () => api.post(trip(id, "/transfer"), { new_owner_id: newOwnerId }))
export const createShareLink = (id: string) => write(id, () => api.post<ShareLink>(trip(id, "/share-links"), {}))

export const getPreview = (token: string) => api.get<InvitePreview>(`/v1/invites/${encodeURIComponent(token)}`)
export const acceptInvite = (token: string) => write<Trip>(null, () => api.post<Trip>(`/v1/invites/${encodeURIComponent(token)}/accept`, {}))

const PENDING = "hermi.invite"
/** A signed-out person who taps Join signs in first; the sign-in screens send them back to the invite. */
export const pendingInvite = {
  set: (token: string) => sessionStorage.setItem(PENDING, token),
  clear: () => sessionStorage.removeItem(PENDING),
  /** Where to go after sign in. */
  target: () => {
    const t = sessionStorage.getItem(PENDING)
    return t ? `/invite/${encodeURIComponent(t)}` : "/"
  },
}
