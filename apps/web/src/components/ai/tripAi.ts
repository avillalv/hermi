import { patchTrip } from "../../routes/trips/api"

/** PATCH /trips/{id} `{ ai_enabled }`. Owner only; the API answers 403 to anyone else. Returns true when saved. */
export async function setTripAi(tripId: string, version: number | undefined, enabled: boolean): Promise<boolean> {
  return (await patchTrip(tripId, version, { ai_enabled: enabled })).ok
}
