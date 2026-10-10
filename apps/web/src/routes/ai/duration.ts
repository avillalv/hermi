/** `duration_seconds_bucket` of the analytics catalogue (10 section 4). */
export const duration = (ms: number) => {
  const s = ms / 1000
  return s < 30 ? "under_30" : s < 60 ? "30_to_60" : s < 180 ? "60_to_180" : "over_180"
}
