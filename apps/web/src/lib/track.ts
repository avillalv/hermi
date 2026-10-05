/** Product events (05 section 6 "Events"). Kept as the call-site name; the catalogue and sink live in analytics.ts. */
import { analytics } from "./analytics"

export { analytics }
export const track = analytics.capture
/** first_itinerary_item_added, once per browser. The API does not return the signup time yet, so the bucket is "unknown". */
export const firstItem = () => analytics.captureOnce("first_itinerary_item_added", "first_itinerary_item_added", { minutes_since_signup_bucket: "unknown" })
