import type { Category } from "./api"

/** Icon and kit activity group per category, shared by the Days timeline and the Calendar blocks. */
export const ICON: Record<Category, string> = { sights: "landmark", museum: "landmark", food: "utensils", nature: "mountain", nightlife: "star", shopping: "shopping-bag", travel: "car", other: "circle" }
export const GROUP: Record<Category, string> = { sights: "culture", museum: "culture", food: "food", nature: "outdoors", nightlife: "neutral", shopping: "shopping", travel: "neutral", other: "neutral" }
