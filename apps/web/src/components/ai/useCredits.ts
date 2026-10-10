import { useQuery } from "@tanstack/react-query"
import { ApiError } from "../../lib/api/client"
import { queryClient } from "../../lib/queryClient"
import { api } from "../../routes/auth/api"

// shortcut: hand-written from CreditsNow in apps/api/hermi/modules/billing/schemas.py until `npm run gen:api` is real.
export type Credits = {
  available: number
  own: number
  pool: number
  payer: "own" | "trip_pass"
  blocked: boolean
  version: number
  total: number
  monthly: number
  trip_pass: number
  purchased: number
  next_monthly_grant_at: string | null
  grants?: { kind: "monthly" | "promo" | "trip_pass" | "purchase" | "adjustment"; remaining: number; expires_at: string | null; trip_id: string | null }[]
}

export const creditsKey = (tripId: string | null) => ["me", "credits", tripId]

/** GET /me/credits for one trip: own credits, the Trip Pass pool this role may spend, and which pool pays first. */
export function useCredits(tripId: string | null, enabled: boolean) {
  return useQuery(
    {
      queryKey: creditsKey(tripId),
      enabled,
      retry: 1,
      queryFn: async () => {
        const r = await api.get<Credits>("/v1/me/credits", { query: tripId ? { trip_id: tripId } : undefined })
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )
}

/** After a spend or a refund: every cached balance is stale. */
export const refreshCredits = () => queryClient.invalidateQueries({ queryKey: ["me", "credits"] })
