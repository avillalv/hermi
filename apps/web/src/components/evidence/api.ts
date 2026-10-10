import { queryClient } from "../../lib/queryClient"
import { noteKey } from "../../routes/notes/api"
import { api } from "../../routes/auth/api"

export type RecheckResult = {
  result: "confirmed" | "changed" | "not_shown" | "unreachable"
  current_value: string | null
  source: { url: string; title: string | null; site: string | null }
  checked_at: string
  credits: { charged: number }
}
export type RecheckOutcome =
  | { ok: true; data: RecheckResult }
  | { ok: false; reason: "credits" | "forbidden" | "off" | "failed" }

// shortcut: hand-written from apps/api/hermi/modules/ai/features/recheck.py until `npm run gen:api` is real.
/** POST /notes/{id}/recheck or /items/{id}/recheck (04 5.14). `key` is the Idempotency-Key, one per tap. */
export async function recheck(kind: "note" | "item", id: string, tripId: string, key: string): Promise<RecheckOutcome> {
  try {
    const r = await api.post<RecheckResult>(`/v1/${kind === "note" ? "notes" : "items"}/${encodeURIComponent(id)}/recheck`, undefined, { headers: { "Idempotency-Key": key } })
    const s = r.response.status
    const code = (r.error as { code?: string } | undefined)?.code
    if (s === 402) return { ok: false, reason: "credits" }
    if (s === 403) return { ok: false, reason: code === "ai_consent_required" || code === "ai_disabled_for_trip" ? "off" : "forbidden" }
    if (r.error !== undefined || !r.data) return { ok: false, reason: "failed" }
    if (r.data.result === "confirmed") await queryClient.invalidateQueries({ queryKey: noteKey(tripId) })
    return { ok: true, data: r.data }
  } catch {
    return { ok: false, reason: "failed" }
  }
}
