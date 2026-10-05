import type { Category, Item } from "./api"

/** Icon and kit activity group per category, shared by the Days timeline and the Calendar blocks. */
export const ICON: Record<Category, string> = { sights: "landmark", museum: "landmark", food: "utensils", nature: "mountain", nightlife: "star", shopping: "shopping-bag", travel: "car", other: "circle" }
export const GROUP: Record<Category, string> = { sights: "culture", museum: "culture", food: "food", nature: "outdoors", nightlife: "neutral", shopping: "shopping", travel: "neutral", other: "neutral" }

/** One day's items in the order the API lists them: start time (untimed last), then sort_order, then id. */
export const inOrder = (items: Item[], day: string | null) =>
  items
    .filter((i) => i.day === day)
    .sort((a, b) => (a.start_time ?? "99").localeCompare(b.start_time ?? "99") || a.sort_order - b.sort_order || a.id.localeCompare(b.id))

/** The Ideas bucket's key in the day picker and chip strip: items with no day. */
export const IDEAS = "ideas"
const fmt = new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" })
export const dayText = (iso: string) => fmt.format(new Date(`${iso}T00:00:00Z`))
