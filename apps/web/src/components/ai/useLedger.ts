import { useInfiniteQuery } from "@tanstack/react-query"
import { ApiError } from "../../lib/api/client"
import { queryClient } from "../../lib/queryClient"
import { api } from "../../routes/auth/api"

// shortcut: hand-written from LedgerEntry in apps/api/hermi/modules/billing/schemas.py until `npm run gen:api` is real.
export type LedgerEntry = {
  reservation_id: string | null
  at: string
  kind: "grant" | "reserve" | "settle" | "refund" | "expire" | "clawback" | "adjust"
  delta: number
  charged: number | null
  action: string | null
  trip_id: string | null
  run_id: string | null
  note: string | null
}
type Page = { items: LedgerEntry[]; next_cursor: string | null; has_more: boolean }

/** GET /me/credits/ledger, newest first, a page at a time. Cached under `["me", "credits", ...]` so a spend refreshes it. */
export function useLedger(enabled: boolean) {
  return useInfiniteQuery(
    {
      queryKey: ["me", "credits", "ledger"],
      enabled,
      retry: 1,
      retryDelay: 400,
      initialPageParam: "",
      getNextPageParam: (last: Page) => last.next_cursor ?? undefined,
      queryFn: async ({ pageParam }) => {
        const r = await api.get<Page>("/v1/me/credits/ledger", { query: { limit: 25, ...(pageParam ? { cursor: pageParam } : {}) } })
        if (r.error !== undefined || !r.data) throw new ApiError(r)
        return r.data
      },
    },
    queryClient,
  )
}
