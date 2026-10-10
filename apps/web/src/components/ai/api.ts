import { useQuery } from "@tanstack/react-query"
import { ApiError } from "../../lib/api/client"
import { queryClient } from "../../lib/queryClient"
import { api } from "../../routes/auth/api"

/** The version of the consent text on `AiConsentGate`. Change it with the copy, so a new text asks again. */
export const AI_CONSENT_VERSION = "1"

// shortcut: hand-written from apps/api/hermi/modules/auth/schemas.py until `npm run gen:api` is real.
export type Consent = { kind: string; version: string; granted: boolean; accepted_at: string }
export const CONSENTS_KEY = ["me", "consents"]

/** GET /me/consents. `granted` is undefined until the answer is in, so a screen never blocks on a guess. */
export function useAiConsent(enabled: boolean) {
  const q = useQuery(
    {
      queryKey: CONSENTS_KEY,
      enabled,
      retry: 1,
      queryFn: async () => {
        const r = await api.get<Consent[]>("/v1/me/consents")
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )
  const granted = q.data ? q.data.some((c) => c.kind === "ai_processing" && c.granted) : undefined
  return { granted, isPending: q.isPending, isError: q.isError }
}

/** PUT /me/consents/ai_processing. Returns true when saved. Withdrawing disables AI only (01 F-ACC-6). */
export async function setAiConsent(granted: boolean): Promise<boolean> {
  try {
    const r = await api.put<Consent>("/v1/me/consents/ai_processing", { version: AI_CONSENT_VERSION, granted })
    if (r.error !== undefined || !r.data) return false
    await Promise.all([queryClient.invalidateQueries({ queryKey: CONSENTS_KEY }), queryClient.invalidateQueries({ queryKey: ["agents"] })])
    return true
  } catch {
    return false
  }
}

export type ReportReason = "spam" | "harmful" | "wrong_info" | "copyright" | "privacy"
export type ReportTarget = { runId: string } | { noteId: string }
export type ReportResult = "ok" | "rate" | "gone" | "failed"

/** POST /reports. A repeat on the same target is a 200 with the first id, so a second tap is harmless. */
export async function sendReport(target: ReportTarget, reason: ReportReason): Promise<ReportResult> {
  try {
    const body = "runId" in target ? { run_id: target.runId, reason } : { note_id: target.noteId, reason }
    const r = await api.post<{ id: string }>("/v1/reports", body)
    const s = r.response.status
    if (s === 429) return "rate"
    if (s === 404) return "gone"
    return r.error === undefined && r.data ? "ok" : "failed"
  } catch {
    return "failed"
  }
}
