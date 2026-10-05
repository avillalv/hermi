import { useQuery } from "@tanstack/react-query"
import { queryClient } from "../../lib/queryClient"
import { api } from "../auth/api"
import type { TripSummary } from "../onboarding/trips"

// shortcut: hand-written from the Trip read model in apps/api/hermi/modules/trips/schemas.py until `npm run gen:api` is real.
export type TripDestination = {
  id: string
  position: number
  name: string
  region: string | null
  country: string | null
  timezone: string | null
}
export type Trip = Pick<TripSummary, "id" | "name" | "status" | "start_date" | "end_date" | "my_role"> & {
  home_currency: string
  destinations: TripDestination[]
}

export class NotFound extends Error {}

/** GET /trips/{id}. A 404 (deleted, or not yours) is a `NotFound`, which the screen shows without a retry. */
export function useTrip(id: string | undefined, enabled: boolean) {
  return useQuery(
    {
      queryKey: ["trip", id],
      enabled: enabled && !!id,
      retry: (n, e) => !(e instanceof NotFound) && n < 1,
      queryFn: async () => {
        const r = await api.get<Trip>(`/v1/trips/${encodeURIComponent(id)}`)
        if (r.response.status === 404) throw new NotFound()
        if (r.error !== undefined || !r.data) throw new Error(`trip ${r.response.status}`)
        return r.data
      },
    },
    queryClient,
  )
}
