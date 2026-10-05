# Plan, places, stays and notes (prompt 09)

Where the Phase 1 trip-content features live and the helpers to reuse.

- **Itinerary:** `apps/api/hermi/modules/itinerary/` (days, items, reorder, move, bulk with version 409s, ICS export at `GET /v1/trips/{id}/itinerary.ics`). Web: `apps/web/src/routes/itinerary/` (Days view, FullCalendar Calendar view, lazy loaded).
- **Places and map:** `modules/places/` and `modules/geo/` (Geoapify through `places_cache`, 1 week TTL, `places_search` rate limit). Web: `routes/places/` (Add activity sheet, MapLibre map with clustering, Apple and Google Maps handoff).
- **SSRF guard:** `security/ssrf.py` takes a per-caller policy; link preview (`providers/link_preview.py`) allows http and https on 80 and 443. Reuse it for any outbound fetch of a user URL.
- **Lodging:** `modules/lodging/`. Links are kept as pasted and never fetched for Airbnb, Vrbo or Booking.com. Free is capped at 8 saved stays, the 9th is a 402 `ninth_stay`. Vote tombstone is migration 0022.
- **Notes:** `modules/trips/notes.py`, web `routes/notes/` and the shared `components/SourceChip.tsx`. Private notes are visible only to their author.
- **Owner check pending:** the exported ICS imports into Apple Calendar (`HUMAN_TASKS.md` row 39).
- Judgement calls are in `app-buildout/prompts/DECISIONS.md` rows tagged `09 / WF-0xx`.
