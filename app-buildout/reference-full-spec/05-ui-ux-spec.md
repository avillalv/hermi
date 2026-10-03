# 05. UI and UX specification

Part of the [Hermi build specification](../README.md). The shared decisions in the README are final and override anything here. Brand files are in [brand/](../brand/BRAND.md). API names are in [04-api-spec.md](04-api-spec.md), tables in [03-database-schema.md](03-database-schema.md), pricing and entitlement logic in [07-monetization-spec.md](07-monetization-spec.md), AI behavior in [06-ai-agents-spec.md](06-ai-agents-spec.md).

Written 2026-09-30. This file is the source of truth for how Hermi looks, moves and reads. It starts from the design system that already exists in the Trip Planner repository (`frontend/src/index.css`, `frontend/src/components/ui/`, `frontend/src/components/brand/`) and keeps its token plumbing and neutral token names, but replaces the old passport palette, type and motifs with the Hermi design language: two routes, one trip. Where this file adds or renames a token (for example `--tp-sky`), it says so.

Contents: 1 Design principles, 2 Design tokens, 3 Logo usage, 4 Component library, 5 Navigation and information architecture, 6 Screens, 7 Microcopy rules, 8 Paywall design rules, 9 Accessibility, 10 Responsive breakpoints, 11 Haptics, 12 Dark mode, 13 Analytics conventions.

## 1. Design principles

1. **Two routes, one trip.** A pale sky ground, deep ink, sky blue as the brand, and the people on the trip drawn as colored dotted routes that meet at a plane. Every trip has its own seeded route pattern in its travelers' colors, so a trip feels like a journey you share.
2. **Value before asking.** No account wall, no paywall, no permission prompt before the person has built something. Ask for sign-in when there is something to save, and for a purchase only at a limit they actually hit.
3. **The free path is always visible.** Every paywall, credit prompt and partner card shows the no-cost route beside the paid one, in the same visual weight class ("Not now" is a real button, not a gray X).
4. **Show the source.** Anything an agent found shows the page it came from, the date it was seen and what it was based on. Prices say "at last check". Nothing is presented as the lowest or best price.
5. **Numbers are a calm, honest voice.** Prices, credits and fares are set in the data face (Atkinson Hyperlegible Mono, tabular figures), always with currency, date or age, and a plain statement of how a list is sorted.
6. **Plan together.** Who did what is always visible: avatars, "added by Sam", vote counts with names. Shared state is never silent; changes from others appear with a quiet highlight.
7. **Never blocks the trip.** Offline, rate limited, out of credits or downgraded: the plan stays readable and editable where possible and always exportable. Errors say what happened and how to fix it.
8. **Quiet commerce.** Partner cards are useful, labeled and few. No banners, no countdowns, no fake scarcity, nothing ranked by commission, nothing inside AI output.
9. **One screen, one job.** A phone screen has one primary action. Advanced controls live behind a sheet or a "More" row.
10. **Accessible by construction.** WCAG 2.2 AA is the floor, not a polish pass. Color never carries meaning alone, and every motion has a reduced version.

## 2. Design tokens

All tokens are CSS custom properties defined in `packages/tokens` (CSS and TS) and imported by `apps/web`, exposed to Tailwind 4 through `@theme inline`. The token plumbing and the neutral names (`--tp-paper`, `--tp-ink`, `--tp-brand` and the rest) are ported from the Trip Planner's `frontend/src/index.css`; the values are not. Every value below replaces the old passport palette, and where a token is new or renamed this file says so. Components use the semantic names (`--background`, `--card`, `--primary`) and the Hermi names (`--tp-*`). Never hard-code a hex value in a component.

### 2.1 Color: surfaces and ink

| Token | Light | Dark | Use |
|---|---|---|---|
| `--tp-paper` (`--background`) | `#F2FAFF` | `#0B1A2A` | Page ground, a pale sky |
| `--tp-sheet` (`--card`, `--popover`) | `#FFFFFF` | `#12263A` | Cards, sheets, inputs, popovers |
| `--tp-sunken` (`--secondary`, `--muted`, `--accent`) | `#E3F1FC` | `#1A3149` | Wells, chips, hover fill, skeleton base |
| `--tp-ink` (`--foreground`) | `#17324A` | `#E6F2FF` | Primary text, icons |
| `--tp-ink-soft` (`--muted-foreground`) | `#4A6580` | `#9DB5CC` | Secondary text, captions |
| `--tp-rule` (`--border`, `--input`) | `#D3E4F2` | `#27405A` | Decorative dividers and card borders only |
| `--tp-edge` (new) | `#6A86A0` | `#6C88A3` | Borders of interactive controls (inputs, checkboxes, segmented controls). Needed because `--tp-rule` is only about 1.3 to 1 against a card, which fails the 3 to 1 non-text contrast rule |
| `--tp-brand` (`--primary`, `--ring`) | `#0B6BC0` | `#6CC4FF` | Primary buttons, links, focus ring, active tab. This is the text-safe sky; the logo's own sky `#2AA5FF` is `--tp-sky` |
| `--tp-brand-ink` (`--primary-foreground`) | `#FFFFFF` | `#0B1A2A` | Text on brand fills |
| `--tp-brand-soft` | `#DCEFFF` | `#123A5C` | Selected row, your own vote, soft emphasis |
| `--tp-success` | `#1d7a52` | `#4cc38a` | Done, price fell, booked |
| `--tp-warning` | `#a86a12` | `#e0a44a` | Caution, price rose, limit near. Light value is 4.43 to 1 on a card, so use it for icons, bars and text of 18 px bold or larger; small text uses `--tp-warning-ink` |
| `--tp-warning-ink` (new) | `#8a5a10` | `#e0a44a` | Small warning text (5.91 to 1 on a card in light) |
| `--tp-danger` (`--destructive`) | `#b42318` | `#f07167` | Errors, destructive actions, price rose when the user is buying |

### 2.2 Color: sky, routes, travelers and data

| Token | Light | Dark | Use |
|---|---|---|---|
| `--tp-sky` (`--sidebar`; renamed from `--tp-cover`) | `#2AA5FF` | `#0E3F66` | The logo tile and the brand surfaces: splash, web sidebar, paywall header, trip header band. A fill, never a text color (white on it is 2.65 to 1) |
| `--tp-sky-ink` | `#17324A` | `#E6F2FF` | Text and icons on sky |
| `--tp-sky-soft` | `#17324A` | `#B9D3EA` | Secondary text on sky. In light it equals `--tp-sky-ink`, because nothing lighter passes 4.5 to 1 on sky; use size and weight for hierarchy there |
| `--tp-sky-raised` | `#E8F5FF` | `#155487` | Hover and active row on sky (the active row is a pill) |
| `--tp-sky-rule` | `#1B8EE6` | `#1A5A8C` | Dividers on sky |
| `--tp-cream` (new) | `#FFF8EC` | `#FFF8EC` | The plane, small highlights on sky |
| `--tp-route-a` (new, replaces `--tp-teal` and `--tp-line-a`) | `#FF5E7E` | `#FF7A93` | Route pink: traveler 1 and the left route of the logo. A decorative fill |
| `--tp-route-a-ink` (new) | `#C4264D` | `#FF8FA5` | Pink when it is text or the only carrier of meaning |
| `--tp-route-b` (new, replaces `--tp-violet` and `--tp-line-b`) | `#FFCB2E` | `#FFD45C` | Route yellow: traveler 2 and the right route of the logo. A decorative fill |
| `--tp-route-b-ink` (new) | `#8A5A00` | `#FFD45C` | Yellow when it is text or the only carrier of meaning |
| `--tp-traveler-1` to `--tp-traveler-8` (new) | `#FF5E7E`, `#FFCB2E`, `#2BBFAD`, `#6A45F2`, `#FF8A3D`, `#3DBE6B`, `#0B6BC0`, `#B92E86` | same | One color per person on a trip, in the order they joined: avatar fill, their route on the map and the timeline, their "added by" highlight. Initials on each use `--tp-traveler-ink-1` to `-8`: `#10283D`, `#17324A`, `#17324A`, `#FFFFFF`, `#17324A`, `#17324A`, `#FFFFFF`, `#FFFFFF` (all at least 5.1 to 1) |
| `--viz-live` | `#00909a` | `#0f9aa2` | Chart series: live fare (Google Flights) |
| `--viz-cached` | `#a86a12` | `#c2851f` | Chart series: cached fare (Aviasales) |
| `--viz-agent` | `#5b47b0` | `#8a76e4` | Chart series: agent-found fare |
| `--viz-google` | `#c24472` | `#d9598a` | Chart series: Google price history |
| `--heat-1` to `--heat-5` | `#ceeff1`, `#93d9dc`, `#4fbec4`, `#009da3`, `#007980` | `#083a3d`, `#00565a`, `#007378`, `#00a0a6`, `#5ac8cd` | Date-grid price steps, one hue; the most prominent step is the cheapest. Text on each step uses `--heat-ink-1` to `--heat-ink-5` |
| `--cat-culture` | `#5b47b0` | `#a07fe0` | Plan blocks and pins: sights, museums |
| `--cat-food` | `#e0621e` | `#d95926` | Food, nightlife |
| `--cat-outdoors` | `#0f9f76` | `#1a9f71` | Parks, hikes, beaches |
| `--cat-shopping` | `#2f86d8` | `#2869cc` | Shopping |
| `--cat-neutral` | `#55607a` | `#9ba7be` | Getting around, other |

Rules: chart series follow the price source, never its rank, so a partner's color can never signal "best". Activity groups are validated for color-blind separation; an icon and a text label always accompany the color. Traveler colors identify people, never status or price: a person's color always comes with their name or initials, and the old `--tp-rose` is gone.

The `--cat-*` tokens are color groups over the eight `itinerary_items.category` values of 03 (`item_category`): `--cat-culture` is `sights` and `museum`, `--cat-food` is `food` and `nightlife`, `--cat-outdoors` is `nature`, `--cat-shopping` is `shopping`, and `--cat-neutral` is `travel` (getting around) and `other`. Every item has exactly one category; the UI labels are Sights, Museums, Food, Outdoors, Nightlife, Shopping, Getting around and Other.

### 2.3 Measured contrast (WCAG 2.x ratios)

| Pair | Light | Dark |
|---|---|---|
| Ink on paper | 12.50 | 15.48 |
| Ink on card | 13.19 | 13.57 |
| Soft ink on paper | 5.74 | 8.29 |
| Soft ink on card | 6.06 | 7.27 |
| Brand on card (links, text buttons) | 5.41 | 8.05 |
| Brand ink on brand (primary button label) | 5.41 | 9.18 |
| Success on card | 5.31 | 6.95 |
| Warning on card | 4.43 (large text only) | 7.02 |
| Warning ink on card | 5.91 | 7.02 |
| Danger on card | 6.57 | 5.32 |
| Sky ink on sky | 4.98 | 9.63 |
| Sky soft on sky | 4.98 | 7.06 |
| Sky ink on sky raised (active row) | 11.90 | 6.99 |
| Route A ink on card | 5.63 | 7.13 |
| Route B ink on card | 5.93 | 10.87 |
| Traveler initials on traveler fills (lowest of the eight) | 5.14 | 5.14 |
| `--tp-edge` on card (control borders) | 3.80 | 4.17 |
| `--tp-edge` on paper | 3.60 | 4.76 |

Every new color pair added later must be checked with the same formula and recorded here. Body text needs 4.5 to 1, large text and control boundaries 3 to 1. The logo's sky `#2AA5FF`, `--tp-route-a` and `--tp-route-b` are decorative fills and never carry text in a color of their own.

### 2.4 Typography

Three bundled families (`@fontsource-variable`, subset to Latin): **Fredoka** (display: rounded and friendly, used only for names, codes and page titles), **Atkinson Hyperlegible Next** (body and labels), **Atkinson Hyperlegible Mono** (numbers and data). Everything that is not a name, a code or a title is Atkinson Hyperlegible Next.

| Role (Tailwind utility) | Family and axes | Size and line height | Use |
|---|---|---|---|
| `type-display` | Fredoka, weight 700, tracking -0.01em | 40 to 56 px, line 1.0 | Splash, empty hero, paywall headline |
| `type-title` | Fredoka, weight 600, tracking -0.005em | 30 px, line 1.1 | Screen title |
| `type-heading` | Fredoka, weight 600 | 20 px, line 1.2 | Section and card heading |
| `type-code` | Fredoka, weight 700, tracking 0.06em, uppercase | 24 to 32 px | Airport codes like a bag tag (LIS, JFK) |
| `type-label` | Atkinson Hyperlegible Next, weight 700, tracking 0.08em, uppercase | 11 px | Eyebrows, chip labels, table heads |
| Body large | Atkinson Hyperlegible Next 400 | 17 px, line 1.5 | Lead paragraphs, onboarding |
| Body (default) | Atkinson Hyperlegible Next 400 | 15 px (`0.9375rem`), line 1.55 | Default text |
| Body strong | Atkinson Hyperlegible Next 600 | 15 px | Row titles |
| Small | Atkinson Hyperlegible Next 400 | 13 px, line 1.45 | Captions, disclosure lines, timestamps |
| `type-data` | Atkinson Hyperlegible Mono, tabular figures | 13 to 15 px | Prices, credits, times, counts |
| Figure (hero) | Mono 700, tracking -0.03em | 32 to 48 px | Fare on a fare detail, credit balance |

Rules: sentence case everywhere except `type-label` and `type-code`, which are uppercase by style (the text in the DOM stays sentence case so screen readers do not spell it out). Never set body text below 13 px. Inputs are 16 px on iOS to stop zoom. All sizes are in `rem` so Dynamic Type and browser zoom work (section 9.3). Deck (present mode) uses the `deck-*` container-query utilities already in `index.css`.

### 2.5 Spacing

4 px base. Scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 (Tailwind `1, 2, 3, 4, 5, 6, 8, 10, 12, 16`). Screen gutter 16 px on phones, 24 px from 768 px, content max width 1120 px on web (720 px for reading screens such as notes and settings). Card padding 16 px (12 px when dense). Vertical rhythm between cards 12 px, between sections 24 px. Touch targets are at least 44 by 44 pt with at least 8 px between targets; a visually small control (a 32 px button) gets an invisible hit area to reach 44.

### 2.6 Radii

`--radius` is `0.75rem` (12 px). Derived: `sm` 8 px, `md` 10 px, `lg` 12 px, `xl` 16 px, `2xl` 20 px, `3xl` 24 px, `4xl` 28 px. Buttons are pills (full round). Inputs `lg` (12 px). Cards `xl` (16 px). Bottom sheets `2xl` on the top corners (20 px). Chips and avatars full round. The app icon keeps its own 22% corner.

### 2.7 Elevation

Hermi is flat: hierarchy comes from ground color, hairline rules and the sky band, not shadow.

| Level | Use | Light | Dark |
|---|---|---|---|
| 0 | Page ground | none | none |
| 1 | Cards, inputs | 1 px `--tp-rule` border, no shadow | same |
| 2 | Popovers, menus, toasts | border plus `0 4px 16px rgb(23 50 74 / 12%)` | border plus `0 4px 16px rgb(0 0 0 / 40%)` |
| 3 | Bottom sheets, dialogs | `0 -8px 32px rgb(23 50 74 / 18%)`, scrim `rgb(23 50 74 / 45%)` | lighter surface (`--tp-sunken` top edge 1 px), scrim `rgb(0 0 0 / 60%)` |

### 2.8 Motion

| Token | Value | Use |
|---|---|---|
| `--motion-fast` | 120 ms | Press, hover, pin scale, toggle |
| `--motion-base` | 200 ms | Fades, chip state, tab underline |
| `--motion-slow` | 320 ms | Sheets, page transitions |
| `--ease-out` | `cubic-bezier(0.22, 0.61, 0.36, 1)` | Default (same curve as the route draw-on) |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Reorder, layout shifts |
| `--ease-touchdown` (renamed from `--ease-stamp`) | `cubic-bezier(0.2, 0.9, 0.3, 1.2)` | Touchdown only (`touchdown`, 280 ms) |

Signature motions: **touchdown** (a run's outcome ticket stub settles from 1.15 to 1 and fades in, like a plane landing), **route draw-on** (a route's dots appear in order with a 45 ms stagger and the plane glides to the end, at most 1.8 s, on the splash, a new trip and a finished run) and the **nav progress bar** (a 1.1 s sweep that starts after 150 ms so quick loads never flash it). Touchdown and route draw-on are new; they replace the old repo's stamp press and guilloche draw-on with the same timings. Everything else is a short fade or a slide. Reduced motion: touchdown and draw-on render at their final state, sheets fade instead of sliding, the progress bar becomes a static 60% bar, no parallax, no auto-advancing carousels.

### 2.9 Route pattern usage rules

The route pattern (`components/brand/route-pattern.tsx`, new, replacing `guilloche.tsx`; deterministic from a seed) is the signature: two or three dotted routes that start at their own origin dots, curve across the space and meet at a plane, echoing the logo. It is used sparingly and never under text that needs to be read.

1. **Seed** is the trip's UUID, so a trip keeps its pattern on every device. Non-trip uses seed from a fixed string ("hermi-splash", "hermi-paywall"). On a trip, the routes take the colors of its first travelers.
2. **Where it appears:** splash and onboarding hero (full pattern, animated once), trip card band (behind the destination), trip overview header (band), paywall header (static), present-mode title and closing slides, empty states (two routes only, static, 12% opacity), export PDF cover, share-link page.
3. **Where it never appears:** behind body text, inside inputs, on lists of more than three rows, on partner cards, on error states, in the tab bar.
4. **Color:** `--tp-route-a` and `--tp-route-b` (later travelers in their traveler colors); the plane in `--tp-cream` on sky and in `--tp-ink` on paper. On sky surfaces use the `.on-sky` class, which draws at full color; on paper and sheet the pattern sits at 35 to 50% opacity.
5. **Dots:** round, never dashes; 6 to 10 px across at display size with a gap of 1.2 times the dot; at most 80 dots per pattern; each route's start dot is 1.5 times larger, as in the logo.
6. **Decorative:** `aria-hidden="true"`, `focusable="false"`, no title. Never the only carrier of meaning.
7. **Animation:** route draw-on plays once per session per surface and never on scroll. Skipped under reduced motion.
8. **Performance:** dot positions are memoized per seed; at most two animated patterns on screen; static SVG on devices that report low power mode.

## 3. Logo usage

Files live in `../brand/` (see [../brand/BRAND.md](../brand/BRAND.md)): `hermi-logo.svg` (mark plus wordmark on light), `hermi-logo-dark.svg`, `hermi-mark.svg` (the app-icon tile), `hermi-wordmark.svg`, `hermi-app-icon.svg` and `hermi-app-icon-1024.png`.

The mark is an H on a sky rounded tile (`#2AA5FF`). Its two posts are dotted routes, pink (`#FF5E7E`) on the left and yellow (`#FFCB2E`) on the right, each with a larger start dot at its foot, and its crossbar is a cream (`#FFF8EC`) plane flying right: two travelers, one trip. The wordmark is "Hermi" in Fredoka SemiBold, ink `#17324A` on light and `#E6F2FF` on dark.

| Context | Use |
|---|---|
| Splash, sign-in, paywall header | Full lockup (mark plus wordmark), centered, mark 72 px |
| Web sidebar (sky) | Mark 32 px and wordmark 17 px in `--tp-sky-ink`; the tile merges into the sky, and the dots and plane carry the mark |
| Web top bar on light | Light lockup, mark 28 px |
| Navigation bar on iOS | No logo; the screen title is used. Trips home may show the 28 px mark (no wordmark) left of the large title |
| Favicon, app icon | `hermi-mark.svg` (also the 16 and 32 px favicon) and the 1024 px PNG, no transparency, no extra rounding (iOS masks it) |
| Email, PDF cover, share page | Full lockup above a sky band with the route pattern |
| Loading | Mark with its route dots appearing from the start dots up and the plane sliding in (route draw-on rule; static under reduced motion) |

Rules:
1. Clear space on every side equals the diameter of a start dot (about 14% of the mark width, minimum 8 px).
2. Minimum sizes: mark 24 px in the UI (the 16 and 32 px favicons use the same file, where the dots merge into a pink and a yellow post), lockup 96 px wide. Below 24 px use the mark only.
3. Never recolor or swap the routes (pink left, yellow right), rotate (the plane points right), stretch, outline, add shadows, or place the mark on busy photography without its tile. On dark grounds use the dark lockup; the tile stays sky.
4. Never use the logo as a button or a bullet. The wordmark is not set in the UI font; always use the file.
5. The app has one name in the UI, "Hermi", in sentence-case copy. No "Hermi AI" or "Hermi Pro" as a product name except "Hermi Plus" and the plan names in the price table.
6. The existing in-repo rosette `BrandMark` and "Trip Planner" text in `logo.tsx` are replaced by the Hermi mark and wordmark, and `guilloche.tsx` is replaced by `route-pattern.tsx` (section 2.9).

## 4. Component library

Base: shadcn/ui on Radix, already in the Trip Planner's `frontend/src/components/ui/` and carried to `apps/web/src/components/ui/` (button, badge, card, dialog, alert-dialog, dropdown-menu, input, textarea, label, separator, sheet, skeleton, sonner, switch, tabs, tooltip). Additions are named in each entry. Conventions: every component supports light and dark through tokens, has a visible focus ring (`--ring`, 3 px at 50% plus a 1 px solid edge), has a minimum 44 pt hit area on touch, and never relies on hover for information.

State vocabulary used below: default, hover (web), pressed, focus, disabled (50% opacity, not removed from focus order when it explains itself through a tooltip or helper), loading, error, selected.

### 4.1 Button

| Variant | Look | Use |
|---|---|---|
| Primary (`default`) | `--primary` fill, `--primary-foreground` text | One per screen or sheet |
| Secondary | `--secondary` fill | Supporting action beside a primary |
| Outline | Border `--tp-edge`, transparent fill | Neutral action, "Not now" on paywalls |
| Ghost | No fill, `--muted` on hover and press | Toolbar and inline |
| Destructive | `--destructive` at 10% fill, danger text | Delete, remove, leave |
| Link | Brand text, underline on hover and always underlined in body copy | Inline navigation |
| Partner | Outline with an external-link icon and the partner name, never brand-filled | Affiliate "Book on <partner>" (see 4.13) |

Sizes: `sm` 28 px, default 32 px on web, `lg` 44 px on touch (all primary actions on phones are 48 px tall, full width in sheets). Icon buttons are square with an `aria-label`. States: pressed translates 1 px down (existing `active:translate-y-px`) and on iOS scales to 0.98; loading replaces the label with a 16 px spinner and keeps the width, sets `aria-busy`, and blocks repeat taps; disabled explains itself ("Add a destination first") in helper text, not only a dimmed button. Labels are plain verbs: Save, Add, Invite, Book, Restore purchases.

### 4.2 Inputs

Text input, textarea, select (Radix), combobox (existing `components/common/combobox.tsx`, used for airports and destinations), date and date-range field, stepper (travelers, nights), switch, checkbox, radio group, segmented control, search field, money field.

| Part | Rule |
|---|---|
| Label | Always visible above the field, `type-label` is not used for form labels (sentence case, 13 px, weight 600) |
| Field | 44 px tall on touch, 16 px text, `--tp-sheet` fill, 1 px `--tp-edge` border, radius `lg` |
| Helper | 13 px soft ink below, for format and limits ("Add the code from your email") |
| Error | Border `--tp-danger`, danger icon plus text below ("That code is not right. Check the email we sent and try again."), `aria-invalid` and `aria-describedby`, focus moves to the first error on submit |
| Disabled | 50% opacity with helper saying why |
| Money field | Mono figures, currency code as a fixed suffix, decimal keyboard, stores minor units |
| Airport combobox | Type to search by city or code; results show the code in `type-code`, the city, and distance from the home airport; "Nearby airports" chip row; results are sorted by distance, never by anything commercial |
| Date range | Sheet calendar on phones, popover on web; "Flexible dates" toggle opens a window picker (earliest departure, latest return, trip length) |
| Switch | 51 by 31 pt on iOS; label on the left, switch on the right, whole row is the hit area |

### 4.3 Cards

`Card` is `--tp-sheet` fill, 1 px `--tp-rule` border, radius `xl`, padding 16 px. Variants: default, interactive (whole card is a link, pressed fills `--tp-sunken`, chevron on the right), selected (2 px `--primary` border plus `--tp-brand-soft` wash), quiet (no border, `--tp-sunken` fill; used for hints and disclosure blocks), and locked (content blurred 6 px with a lock icon and an unlock button, used only where a paywall in 6.27 allows a preview). A card never has more than one primary action.

### 4.4 Trip card

Shown on Trips home. A card with a route pattern band (seeded by trip id) across the top 72 px at 14% opacity, the destination name in `type-heading`, dates in `type-data` ("12 to 19 Mar"), travelers as stacked avatars, a status chip (Planning, Booked, Happening now, Past), and a footer row of quiet facts: cheapest fare with age ("from $412, 3 h ago"), next item ("Day 1: Alfama walk"), and open votes count. Variants: upcoming, in progress (brand-soft wash, "Day 3 of 7"), past (muted, "Archived on 4 Apr"), shared with me (owner avatar and role chip), locked by limit (read-only chip "Limited", never hidden). States: loading skeleton (band, two lines, three chips), offline (shows a "Saved offline" cloud-check icon), pressed, focus. Swipe left reveals Archive; long press opens the context menu (Open, Share, Archive, Delete).

### 4.5 Fare chip

A compact pill that states one fare: price in mono, route code pair in `type-code` at 13 px, and a source tag. Anatomy: `[LIS  $412  Google, 3 h ago]`. Source tags (existing `source-tag.tsx`): Live (teal dot), Cached (amber dot), Agent (violet dot), Google history (rose dot); the dot color always pairs with the word. Trend glyph: arrow down with "Down $42" in success, arrow up with "Up $30" in warning-ink, flat dash glyph replaced by the word "No change". States: default, selected (brand-soft), stale (age over 24 h adds a clock icon and "Check again"), unavailable ("No fare found"). Tapping opens the fare detail. The chip never says "best", "cheapest" or "deal" unless the value is the computed minimum of the shown set, and then it says "Lowest in this list".

### 4.6 Price chart

Recharts line and band chart in a 16:9 card (180 px tall on phones). Series: live, cached, agent and Google history, in the `--viz-*` colors with distinct marker shapes and a legend that doubles as a toggle. The typical-price band uses `--viz-band`. Y axis has currency and no more than five ticks; x axis has dates. Interactions: tap or drag to place a scrubber with a readout ("Tue 14 Oct, $412, cached, seen 6 h ago"); long press pins a point; a "Fare fell $42 since Tuesday" callout sits above. Phones show a sparkline in the list and the full chart on the fare detail. Accessibility: the chart has a text summary ("Lowest $398 on 3 Oct, now $412, up $14 this week"), a visually hidden data table, and arrow keys step the scrubber. States: loading (skeleton with axis), empty ("No fares yet. Checks run daily."), one point ("We need two checks to draw a line"), error ("We could not load this chart. Pull down to try again."), offline ("Showing the last saved data from 3 Oct").

### 4.7 Calendar

Two modes on the Plan section. **Month and range** (`react-day-picker` style grid, used in create trip and flexible dates): 44 pt cells, today ringed, selected range filled `--tp-brand-soft` with `--tp-brand` end caps. **Day timeline** (FullCalendar `timeGridDay` and `listWeek`, themed through the `--fc-classic-*` tokens already in `index.css`): events show as tinted blocks of their activity group color with icon and label, times in mono. On phones drag-resize is off; long press opens "Move to..." (sheet with day and time). Web allows drag and drop between days, with a 409 conflict toast "Sam changed this just now. Your change was not saved. View their version." States: loading skeleton rows, empty day ("Nothing planned. Add a place or ask for a draft."), offline read-only banner, dragging (lifted with elevation 2).

### 4.8 Day card

One per day in the Plan list. Header: "Day 3", date in mono, a one-line theme the person wrote or accepted ("Sintra by train"), total walking or transit time if known. Body: ordered items with time, icon in the group color, title, optional place photo, and an "added by" avatar when someone else added it. Footer: "Add" and "Draft this day (1 credit)". Variants: collapsed (first two items plus "3 more"), expanded, drop-target (dashed `--tp-edge` border while dragging), today (brand-soft header), empty. Items are ordered by start time, then by `sort_order` (a number on each item, `itinerary_items.sort_order`; untimed items keep the order the person sets). Reorder by drag handle on web, "Move up" and "Move down" actions plus drag on touch (for VoiceOver, custom actions); each reorder or move writes `sort_order` through `POST /trips/{id}/days/{day}/reorder` or `POST /items/{id}/move`. Booked items show a small check ticket stub; unbooked bookable items show the "Tickets" partner link only on explicit expand (see 4.13).

### 4.9 Place card

Used in search, saved places, ideas and Discover. Photo 16:10 (or category icon tile when no photo), name, category chip, distance from the trip center, opening-hours status ("Open until 18:00"), rating when a licensed source provides it, a save heart, and an "Add to day" button. Attribution stays visible (Geoapify, Wikipedia). Variants: result row (72 px, thumbnail left), full card, compact pin popup (map). Sorted by relevance and distance only, and a sort label is always shown ("Sorted by distance"). No partner content in the list; "Tickets" or "Book a table" appears on the detail view only, through 4.13. States: loading skeleton, no photo, closed now, saved, added to Day 2.

### 4.10 Lodging card with votes

Photo strip (swipe, up to 6 photos, page dots), name, area, price per night and total for the trip in mono with currency, per-person price for the party, bedrooms, source chip ("Pasted link", "From Stay22 search", "Added by hand"), status chip (Shortlisted, Booked, Rejected), and the vote row. **Votes are hearts, nothing else:** one row of avatar chips, one per traveler who hearted the stay (there is no down vote and no "no" mark); the viewer's own state is a 44 pt heart toggle ("You love this" with `aria-pressed`) that sends `{ voted: true }` or `{ voted: false }` to `PUT /lodging/{id}/votes/me`. Counts read "3 of 4 like this" (hearts over travelers), names on tap. Variants: shortlist card, compare column (2 to 4 columns, horizontal scroll with a sticky label column), booked (touchdown on the status), rejected (collapsed). Buttons: "Open" always opens the user's saved URL exactly as pasted; "Book via partner" is a separate labeled button only when a program is approved for that host and never for Airbnb (see 4.13). States: no price yet ("Add a price to compare"), price older than 7 days ("Price from 12 Sep, check the site"), locked "later" list on Free after 8 saved (read and export still work), conflict ("Sam also edited this").

### 4.11 Credit cost chip

A pill shown on every button that spends credits. Anatomy: coin glyph, number in mono, the word "credit" or "credits" (for screen readers: "costs 8 credits"). Variants: cost (neutral, `--tp-sunken`), free from cache ("1 credit, from shared cache", success dot), insufficient (warning-ink with "You have 3"), and zero ("Free"). Placement: right side inside the action button, or directly under a button on a sheet. A confirm sheet is required at 6 credits or more (research, agent run), shows the balance before and after, and never auto-confirms. A balance pill ("27 credits") sits in the AI sheet header and Account; tapping it opens Subscription and credits. Wording rules are in 7.3.

### 4.12 Badge and chip set

Badge (status), chip (filter), role chip (Owner, Editor, Viewer), source tag, tier chip (Free, Plus, Family, Pass), fare trend chip, "New" (only for changes by others since last visit, never for marketing). Height 24 px, label in 12 px weight 600, never ALL CAPS except `type-label` badges. Chips that filter are 44 pt tall targets with a 32 px visual.

### 4.13 Affiliate offer card with disclosure line

The only surface for partner links besides the labeled buttons on the lodging and fare screens. Anatomy, top to bottom: an eyebrow `type-label` naming the category and why it is here ("Stays near your Day 2 plan"), the title, a one-line reason grounded in the user's data ("You land in Lisbon at 21:40"), the basis of the price ("From $58 a night, checked 12 Sep, via Stay22"), a row of two equal-weight actions, and the disclosure line.

```
+--------------------------------------------------+
| TRANSFER                                         |
| Airport to your stay                             |
| You land in Lisbon at 21:40 on Fri 12 Mar.       |
| From $24 for 2 people, checked today, via        |
| Welcome Pickups.                                 |
|                                                  |
| [ Book on Welcome Pickups ]  [ I will arrange ]  |
| We earn a commission if you book here.           |
+--------------------------------------------------+
```

Rules, applied to every instance:
1. **Disclosure line** is 13 px `--tp-ink-soft`, always visible directly under the button row, never truncated, never in a tooltip, never below a fold inside the card. Text is exactly: "We earn a commission if you book here." On UK and EU storefronts an "Ad" tag sits in the eyebrow row. Where a partner requires its own line (Booking.com), it is added after ours.
2. **Both routes.** A non-affiliate route is always present: "Search on the airline's site", "Open your saved link", "I will arrange this myself", "Not needed".
3. **Quiet.** Outline buttons, no brand fill, no partner logos larger than 16 px, no badges like "Hot" or "Popular", no timers, no stock counts.
4. **One per screen view**, except lists the user asked for (Stays shortlist, Before you go checklist). Never inside AI output, never beside a paywall, never during present playback, never offline.
5. **Sort statement** on any list of offers ("Sorted by price, lowest first"). Never sorted by commission.
6. **Opens** through `/go/{click_id}` in the in-app Safari view (`SFSafariViewController`, visible address bar, Done button), so the person always sees where they are.
7. **Hide switch.** Settings, How we earn money, "Hide booking links" collapses every card into one plain "Open on partner site" text link. Disclosure still shown.
8. **Flag.** Each partner has a kill switch; a disabled partner renders the non-affiliate route only.

### 4.14 Paywall sheet

A bottom sheet on phones (full height is not used) and a centered 480 px dialog on web. Structure and rules are in section 8. Parts: a header with the static route pattern and the benefit headline for the trigger, a two to three line list of what this gives on this trip, the offer list (up to three options, annual pre-selected where it is a subscription), the primary purchase button, the "Not now" button (equal size), a legal row (price, renewal, cancellation, Terms, Privacy), and "Restore purchases". States: loading prices (skeleton rows, buttons disabled, "Not now" enabled), store unavailable ("We cannot reach the App Store. Check your connection and try again. You can keep planning for free."), purchase pending ("Waiting for approval from your family organizer"), success (touchdown "Plus is on", sheet closes, the blocked action resumes), cancelled (no error, sheet stays), error.

### 4.15 Toast

`sonner`, bottom center on web, above the tab bar on iOS (8 px gap), elevation 2, 4 second default, 8 seconds with an action, persistent for errors that need a choice. Variants: success (check icon), info, warning, error (with a "Try again" action), undo ("Day 2 deleted. Undo"), credit ("Used 1 credit. 11 left"). Announced politely to screen readers (`role="status"`), errors with `role="alert"`. Max two visible, newest on top. Never used for paywalls or for anything the person must read before continuing.

### 4.16 Empty state

A centered block: a static route pattern (two routes at 12%) behind a 48 px line icon, a `type-heading` line saying what lives here, one sentence saying what to do, and one primary button. Optional quiet secondary link. Never a blank screen, never an illustration of people. Copy pattern: "No stays yet" / "Paste a link or search to start a shortlist." / [Add a stay]. Variants per screen are in section 6.

### 4.17 Error state

Inline block (in a card region) or full screen. Anatomy: danger icon, a plain statement of what happened, how to fix it, a primary retry, and a secondary path ("Keep planning offline", "Contact support"). Variants: network ("You are offline. Your trip is saved on this phone. Changes will sync when you reconnect."), server ("Something went wrong on our side. We are looking into it. Try again in a minute."), not found ("This trip is not available. It may have been deleted or you may not have access."), permission ("You can view this trip but not edit it. Ask Sam to make you an editor."), limit ("You have used this month's 12 credits. They renew on 1 Nov."), conflict (409, "Sam changed this while you were editing. Review their version."). Error text includes a request id in small mono ("Reference 7F3A") for support. Full-screen errors never trap the user: Back and Home always work.

### 4.18 Skeletons

`Skeleton` (existing): `--tp-sunken` base with a slow 1.4 s shimmer at 40% contrast (static under reduced motion). Shapes match the final layout exactly (trip card band plus two lines; fare chip row; chart frame with axes; day card with three rows; lodging card with photo block) so the layout does not jump. Show after 150 ms delay (same rule as the nav progress bar). Never show a spinner on a content area; spinners are for buttons and pull-to-refresh only. After 8 seconds of loading, replace with the error state.

### 4.19 Bottom sheet

`vaul` on phones (Radix `Sheet` and `Dialog` on web). Detents: medium (50% height), large (92% height, leaves the status bar visible). Grabber 36 by 5 px, scrim `rgb(23 50 74 / 45%)`, swipe down or tap scrim to dismiss (disabled while a purchase or a spend confirmation is in progress). Content scrolls inside; the primary button is sticky at the bottom above the safe area. Focus moves to the sheet title on open and back to the trigger on close; `aria-modal`; the page behind is inert. Keyboard: the sheet lifts with the keyboard and the focused field stays visible. Web converts to a 480 px dialog, or a right-hand 420 px panel for add and edit forms.

### 4.20 Tab bar

iOS bottom tab bar, 49 pt plus the safe area, `--tp-sheet` at 94% with 20 px background blur and a 1 px top `--tp-rule`. Four tabs: Trips, Discover, Activity, Account. Icons are 24 px lucide line icons (`Luggage`, `Compass`, `Bell`, `CircleUser`), label 11 px weight 600 beneath (labels always shown). Active tab: brand-colored icon and label, plus a 2 px brand bar above the icon; inactive `--tp-ink-soft`. Badge: a 16 px brand dot with a number up to 9, then "9+"; the badge has an accessible name ("Activity, 3 new"). Tapping the active tab scrolls to top, then pops to root. The bar hides while a full-screen sheet or present mode is open and never hides on scroll. Web at 768 px and wider shows the sidebar instead (section 5.3).

### 4.21 Other shared components

| Component | Notes |
|---|---|
| Avatar and avatar stack | 28 px default, initials on one of the traveler colors `--tp-traveler-1` to `-8` (section 2.2), each of which passes 4.5 to 1 with its initials; stack overlaps 8 px and shows "+3" |
| Segmented control | 32 px visual, 44 pt target, iOS style on phones; used for view toggles (List, Map) |
| Progress and run timeline | Steps with a dot, label, elapsed time in mono; current step pulses (static under reduced motion) |
| Ticket stub | Outcome mark (Done, Stopped, Failed, Booked) shaped like a boarding-pass stub, with a notched left edge and a dashed perforation, that uses `touchdown`; text plus icon, never color only |
| Evidence row | Favicon, page title, domain in mono, "seen 12 Sep", one-line quote, "Open source" link |
| Map | MapLibre with the themed pins from `index.css` (`tp-map-pin`, numbered, group colored); attribution stays visible; "Open in Apple Maps" and "Open in Google Maps" actions |
| Banner | Full-width strip under the header for state: offline, limited trip, pending deletion. One at a time, most urgent wins |
| Stepper list | Checklist rows with a check, title, reason, three actions (see 6.20) |
| Context menu and action sheet | iOS action sheet on phones, dropdown on web; destructive last, red text plus icon |
| Pull to refresh | A custom route-and-plane spinner is not used; use the native-style spinner with "Updated just now" text |

## 5. Navigation and information architecture

### 5.1 Sitemap

```
Hermi
+-- Trips (tab 1, web: sidebar "Trips")
|   +-- Trips home (upcoming, in progress, past, shared with me)
|   +-- Create trip
|   +-- Trip workspace  /trips/:tripId
|       +-- Overview   (summary, next steps, Before you go, cost so far)
|       +-- Flights    (routes, alerts, fare detail, Book this fare)
|       +-- Stays      (shortlist, compare, vote, import)
|       +-- Plan       (day list, calendar, map, add item, ideas)
|       +-- Group      (travelers, polls, expenses, settle up, invite)
|       +-- Present    (full screen deck, share)
|       +-- Notes and evidence (reached from Overview; notes also attach to days, items and stays)
|       +-- Agent runs (from Flights, Plan and the AI sheet; run detail)
|       +-- Trip settings (members, AI on or off, Trip Pass status, export, archive)
+-- Discover (tab 2)  destination ideas, cheap fares from your airport, guides
+-- Activity (tab 3)  alerts, changes by others, agent results, invites
+-- Account (tab 4)  profile, subscription and credits, settings, how we earn money,
                     notifications, export and delete, help
```

Notes and evidence have no tab of their own. Notes live in Overview (trip notes) and on each day, item and stay; the Evidence list lives on every agent result and in the Notes screen reachable from Overview. Agent runs have no top-level destination at launch (they are an action, not a place); the list of runs for a trip is Overview, "AI activity".

### 5.2 iOS and phone navigation

- Four bottom tabs (4.20): **Trips, Discover, Activity, Account**. The tab bar shows on every screen except present mode, full-screen sheets and the paywall.
- Inside a trip the tab bar stays (Trips is active) and a **section strip** sits under the trip header: six scrollable text tabs with an underline, in this order: **Overview, Flights, Stays, Plan, Group, Present**. The strip is sticky, scrolls horizontally if the text size is large, and keeps the last visited section per trip. "Present" does not open a section page; it opens the full-screen deck.
- Navigation bar: large title on root screens (Trips, Discover, Activity, Account), inline title inside a trip (destination name) with a back button labeled "Trips", and a trailing "..." menu (Share, Trip settings, Export).
- Swipe from the left edge goes back (native). Modals are bottom sheets; full-screen modals only for create trip, present mode and onboarding.
- Deep links: `https://hermi.world/i/<token>` (invite), `/trips/<uuid>`, `/trips/<uuid>/fares/<route>`, `/s/<shareId>` (read-only). Cold start from a link lands on the target with Back going to Trips.
- State restoration: last tab, last trip and section are restored on launch; a scroll position is restored per section.

### 5.3 Web layout

| Width | Layout |
|---|---|
| 1200 px and up | Sky sidebar 248 px (`--tp-sky`; deep sky in dark mode): logo, trip switcher, **Trips, Discover, Activity, Account**, and under the current trip the six sections. Main content max 1120 px. Optional right rail 320 px (AI sheet, evidence, agent run) |
| 768 to 1199 px | Sidebar collapses to a 72 px icon rail with tooltips; right rail opens as an overlay panel |
| Under 768 px | Sidebar is hidden; bottom tab bar and section strip as on iOS. Dialogs become bottom sheets |

The sidebar trip switcher lists the five most recent trips and "All trips". Keyboard shortcuts on web: `g t` Trips, `g p` Plan, `n` new item, `/` search, `?` shortcut list; all are optional and never the only way to act.

### 5.4 Route map

| Route | Screen |
|---|---|
| `/welcome` | Splash and onboarding |
| `/sign-in` | Sign in |
| `/` | Trips home |
| `/trips/new` | Create trip |
| `/trips/:tripId` | Overview |
| `/trips/:tripId/flights`, `/flights/:routeId/fare/:fareId` | Flights, fare detail |
| `/trips/:tripId/stays`, `/stays/compare`, `/stays/add` | Stays |
| `/trips/:tripId/plan`, `/plan/:day`, `/plan/map` | Plan |
| `/trips/:tripId/group`, `/group/polls/:pollId`, `/group/expenses`, `/group/settle` | Group |
| `/trips/:tripId/notes` | Notes and evidence |
| `/trips/:tripId/runs/:runId` | Agent run |
| `/trips/:tripId/checklist` | Before you go |
| `/trips/:tripId/present` | Present mode (outside the app shell) |
| `/trips/:tripId/concierge` | Concierge request |
| `/discover`, `/activity` | Discover, Activity |
| `/account`, `/account/subscription`, `/account/settings/*` | Account and children |
| `/i/:token` | Invite landing |
| `/s/:shareId` | Read-only shared page |

The current repository routes (`/trips/:tripId/itinerary`, `/lodging`, `/agents`) are renamed to Plan and Stays and folded into the trip workspace.

## 6. Screens

Every screen follows one template: **Purpose**, **Layout**, **Content**, **Interactions**, **States** (loading, empty, error, offline, no permission, limit reached where they apply), **Copy**, **Events** (analytics names, snake_case, properties in braces; `screen_viewed {screen}` fires on every screen and is not repeated; names and property values are the catalog in 10 section 4), **Accessibility**. Copy follows section 7. Credit prices and limits come from the README.

### 6.1 Splash and onboarding

**Purpose.** Show value in one screen and get the person planning in under a minute, with no account.
**Layout.** Full screen, `--tp-paper` ground. Animated route pattern (route draw-on, once) behind the lockup in the upper half. Below: the positioning line in `type-display`, one supporting sentence, and two buttons.

```
+------------------------------+
|        (route pattern)       |
|         [H mark] Hermi       |
|                              |
|  Plan together.              |
|  Know the fare.              |
|                              |
|  Build a trip with the people|
|  you are going with, and see |
|  what flights really cost.   |
|                              |
|  [      Plan a trip       ]  |
|  [        Sign in         ]  |
|                              |
|  By continuing you agree to  |
|  the Terms and Privacy policy|
+------------------------------+
```

**Content.** Three quiet swipeable cards appear only if the person waits or swipes (no auto-advance): "Plan days together", "Watch fares, know what changed", "Every fact links to its source". Dots are optional and labeled.
**Interactions.** "Plan a trip" enters guest mode and opens Create trip (6.6). "Sign in" opens 6.3. Invite links skip this screen. A returning signed-out user sees "Sign in" as primary. Age gate: a one-line confirmation in the sign-in step for storefronts that need it (13 and over, 16 and over for EU and UK locales).
**States.** Loading: the lockup shows instantly, buttons are always active (nothing to load). Offline: same screen, guest planning works offline. Error: not applicable. No permission prompts on this screen, no ATT prompt anywhere.
**Copy.** Title "Plan together. Know the fare." Button "Plan a trip". Legal "By continuing you agree to the Terms and the Privacy policy."
**Events.** `onboarding_started`, `onboarding_choice_made {choice: plan|sign_in|invite}`.
**Accessibility.** The route pattern is hidden from assistive tech; heading order is lockup, headline, body; buttons reachable in order; draw-on skipped under reduced motion.

### 6.2 Guest mode and save your trip

**Purpose.** Let a guest build one trip on the device, then ask for an account only when there is something to keep, share or sync.
**Layout.** A guest sees the normal app with a slim banner under the header: "Guest trip, saved on this phone" and a "Save" button. Tabs: Trips, Discover, Account are live; Activity shows a sign-in prompt.
**Content.** Guest limits: one trip, destinations, plan items, maps, cached fares view, presentation. Anything that needs the server asks for sign-in: invite, sync to a second device, AI beyond the guest allowance, export, alerts, purchase.
**Save sheet (bottom sheet, triggered by any of the above).** Title "Save your trip". Body "Create a free account so your trip is safe and you can share it. Nothing you built will be lost." Buttons in this order: Continue with Apple (black, per Apple HIG), Continue with Google, Continue with email, then "Not now" as a text button. After success the guest trip is claimed into the account (merge screen if the identity already has trips: "You already have 2 trips. Add this one too?" with counts).
**Interactions.** The banner "Save" opens the sheet. Dismissing the sheet mutes the prompt for that trigger for 7 days, but the banner remains (it is not a paywall).
**States.** Offline: sign-in buttons disabled with "Connect to the internet to create your account. Your trip stays on this phone." Error on claim: "We could not move your trip into your account. It is still on this phone. Try again." with Retry. Limit: a second guest trip shows "Guests can plan one trip. Create a free account to add more."
**Events.** `guest_trip_created`, `save_prompt_shown {trigger}`, `save_prompt_dismissed {trigger}`, `guest_claimed {trip_count_bucket}`.
**Accessibility.** Sheet focus rules from 4.19; the Apple button meets Apple's contrast and size rules.

### 6.3 Sign in

**Purpose.** Create or restore an account with Sign in with Apple, Google or an email code.
**Layout.** Sheet or full screen: lockup, title "Sign in to Hermi", three buttons stacked (Apple, Google, email), a legal line. Email path: one screen with an email field ("Email") and "Send code"; next screen six digit code field (one field, `autocomplete="one-time-code"`, numeric keyboard), "Resend code in 30 s", and a "Use a different email" link.
**Interactions.** Apple returns the identity token; "Hide My Email" relay is accepted and shown as the email. The code field auto-submits at six digits. Three wrong codes show a gentle warning; five invalidate the code. Passwords do not exist.
**States.** Loading: button spinners. Error (wrong code): "That code is not right. Check the email we sent and try again." Expired: "That code expired. Send a new one." Rate limited: "Too many tries. Wait 10 minutes, then send a new code." Offline: "You are offline. Connect to sign in." Account pending deletion: "Your account is scheduled for deletion on 14 Nov. Restore it to keep your trips." with "Restore account".
**Copy.** Email helper "We will send a six digit code. No password needed."
**Events.** `signup_started {method}`, `signup_completed {method, from_invite, was_guest}` (new account) or `sign_in_completed {method}` (existing account), `sign_in_failed {method, reason}`.
**Accessibility.** The code field announces "Six digit code"; paste works; error text is linked with `aria-describedby`; the Apple button has a VoiceOver label "Continue with Apple".

### 6.4 Profile setup (skippable)

**Purpose.** Collect the minimum that improves fares: a display name and a home airport.
**Layout.** One sheet: Name, Home airport (combobox with "Use my location" that asks for permission only on tap), Currency (prefilled from locale). "Skip for now" is a full button.
**Interactions.** Saving creates the "Me" traveler. Skipping still creates "Me" with no airport.
**States.** Location denied: "Location is off. Type a city or an airport code instead." Offline: fields work, saved locally.
**Events.** `onboarding_step_completed {step: profile|home_airport}`, `onboarding_step_skipped {step}`.
**Accessibility.** The location button states what it does and why ("Use my location to suggest nearby airports").

### 6.5 Trips home

**Purpose.** See every trip and start a new one.
**Layout.** Large title "Trips", trailing "+" button (also a primary "New trip" button when empty). Sections: **In progress**, **Upcoming**, **Shared with me**, **Past**. Trip cards (4.4) stacked on phones, a two-column grid from 768 px. A "Trip limit" line under the title on Free: "2 of 2 active trips".
**Content.** Sorted by start date (upcoming ascending, past descending); the sort is fixed and not commission related. A banner appears for pending invites ("Sam invited you to Lisbon in March. View").
**Interactions.** Tap opens the trip at the last section. Swipe left: Archive. Long press: Open, Share, Archive, Delete. Pull to refresh. "+" opens Create trip. Archived trips are under a "Past" section toggle, always readable and exportable.
**States.** Loading: three trip card skeletons. Empty: static route pattern, "No trips yet", "Start with a place and a few dates. You can change everything later.", [New trip]. Error: "We could not load your trips. Pull down to try again." Offline: cached trips with "Saved offline" icons and a banner "You are offline. Showing your saved trips." No permission: not applicable. Limit reached: "+" opens the third trip paywall (6.27, trigger `third_trip`) with the free path "Archive a trip" first.
**Copy.** Limit line "You have 2 active trips. Archive one to make room, or upgrade."
**Events.** `trips_home_viewed {trip_count_bucket, active_count}`, `trip_opened {source}`, `trip_archived`.
**Accessibility.** Each card is one link with a combined label ("Lisbon, 12 to 19 March, 2 travelers, planning"); swipe actions have a custom-actions alternative; sections are headings.

### 6.6 Create trip

**Purpose.** Get a trip with a destination, dates and travelers in three taps.
**Layout.** Full-screen modal, three short steps with a progress label ("Step 1 of 3"), one field group per step.

```
+------------------------------+
| x    New trip       Step 1/3 |
|                              |
| Where are you going?         |
| [ Search a city or country ] |
|  Lisbon, Portugal            |
|  Porto, Portugal             |
|                              |
| + Add another destination    |
|                              |
| [          Next           ]  |
+------------------------------+
```

**Content.** Step 1 destination (Geoapify autocomplete, multi-destination allowed), Step 2 dates (range picker, or "I do not have dates yet", or "Flexible" with a window and trip length), Step 3 travelers (you, plus names and home airports for each; "Just me" allowed) and a trip name (prefilled "Lisbon, March"). Template chips on step 1: "Long weekend", "Week abroad", "Road trip", "Blank".
**Interactions.** Create makes the trip, plays the route draw-on once and opens Overview. Dates optional. Back keeps entries. A traveler can be typed or chosen from saved travelers.
**States.** Loading: suggestions skeleton. Empty search: "Try a city, region or country." Error (lookup): "We could not search places right now. Type the name and continue, we will look it up later." Offline: free-text destination accepted, resolved later. Limit reached: Free with 2 active trips shows the third trip paywall on "Create". Guests: one trip limit (6.2).
**Copy.** "Dates are optional. You can add them later."
**Events.** `trip_create_started`, `trip_created {source, destination_count, has_dates}`.
**Accessibility.** Step label is announced; destination results are a listbox with arrow navigation; date picker has a text entry alternative ("12 Mar 2027").

### 6.7 Trip overview

**Purpose.** The trip at a glance and the next sensible step.

```
+------------------------------+
| < Trips     Lisbon       ... |
| Overview Flights Stays Plan  |
|--(underline)-----------------|
| [route pattern band]         |
|  LISBON     12 to 19 Mar     |
|  (SM)(AK)(+1)  Planning      |
|                              |
| Next steps                   |
| [ ] Pick flights       >     |
| [ ] Shortlist 3 stays  >     |
| [ ] Plan day 1         >     |
|                              |
| Fares        from $412       |
|  LIS  [sparkline]  Down $42  |
| Stays        2 of 3 voted    |
| Plan         4 days planned  |
| Before you go   3 to do   >  |
| Cost so far  $1,840 est.     |
| Notes and evidence       >   |
| AI activity              >   |
+------------------------------+
```

**Layout.** Header band with the trip's route pattern, destination in `type-title`, dates, travelers, status. Below: a "Next steps" card (up to three suggestions, derived from missing data: dates, flight, stay, first day), then summary cards for each section, then Before you go, cost so far (from chosen flight, booked stays and expenses), Notes and evidence, AI activity (runs and credits used on this trip).
**Content.** A quiet "Places to stay in Lisbon" partner card appears only when dates exist, collapses after the first view, and follows 4.13 (one per screen view). Destination facts (local time, currency, a Wikipedia summary with attribution) are in a collapsed card.
**Interactions.** Every summary card opens its section. "Invite" avatar button opens the invite flow (6.8). The "..." menu: Share, Trip settings, Export, Archive, Delete. Changes by others show a brand dot on the section and a "Sam updated Stays" line.
**States.** Loading: skeleton header and five cards. Empty (no data yet): only "Next steps". Error: block-level retry per card. Offline: "Saved offline, updated 2 h ago" chip. No permission (viewer): Next steps hidden, summary cards read-only. Limit reached: a limited trip (Plus lapsed, pass expired) shows a banner "This trip is limited. Extra travelers are now viewers. Renew to restore editing." with the free actions visible (read, export).
**Copy.** Empty next step "Pick your dates". Banner as above.
**Events.** `trip_overview_viewed`, `next_step_tapped {step}`, `section_opened {section}`.
**Accessibility.** The header reads as one heading plus a description; cards are links with the state in their name ("Stays, 2 of 3 voted"); the section strip is a `tablist`.

### 6.8 Invite flow

**Purpose.** Bring the other travelers into the trip; they join free.
**Sender layout.** Group section, "Invite" button, or the Overview avatar plus. A sheet with: role (Editor or Viewer, default Editor), "Share link" (native share sheet, link `hermi.world/i/...`), "Send by email" (email field, up to 20 pending), and the current members list with role chips and "Remove". A line under the role: "They join free. You share your trip's features with them on this trip."
**Free owner.** The Invite button is the `invite` paywall trigger (6.27): "Plan together. They join free." with Trip Pass first. The free path: "Share a read-only link" stays available (viewer link) per the tier rules. Family and Plus owners see no paywall.
**Recipient flow.** The link opens the app (or the App Store with an "Enter code" fallback, or a web landing page on desktop). Landing: "Sam invited you to Lisbon, 12 to 19 March" with the route pattern band, member avatars, and "Join trip" (primary). No sign-in wall before seeing the trip title and dates. After sign-in a banner "You were added by Sam" and a one-time sheet "Which traveler are you?" listing travelers with a "None of these" option that adds a new one.
**Interactions.** Owner can change role, resend, revoke a pending invite, and remove a member (access ends immediately). Links expire in 7 days (owner can regenerate).
**States.** Loading: member list skeleton. Error: "We could not create the link. Try again." Invite expired: "This invite expired. Ask Sam to send a new one." Invite used or revoked: "This invite is no longer valid." Already a member: opens the trip. Offline: "Connect to send an invite." No permission: editors can invite viewers only if the owner allows it; else the button is hidden and a line reads "Only Sam can invite people." Limit: 20 pending invites, "You have 20 pending invites. Cancel one to send another."
**Events.** `invite_sheet_opened`, `invite_sent {channel, role}`, `invite_opened {platform_before_install}`, `invite_accepted {role, minutes_to_accept_bucket}`, `traveler_linked`.
**Accessibility.** Role control is a radio group; the share button announces "Share invite link"; the landing page is fully usable without the app.

### 6.9 Flights and alerts

**Purpose.** Find and follow fares for the trip's routes, and set price alerts.
**Layout.** Section header with a "Add route" button. One **route card** per route: codes in `type-code` (NYC to LIS), date window, travelers count, the fare chip row for the cheapest options, price chart (4.6), date grid toggle (Chart, Grid, Options), and an alert switch. "Options" is a list sorted by price by default with a visible sort control (Price, Duration, Stops); every row is a fare chip plus airline, times and stops.

```
+------------------------------+
| Flights               + Route|
| NYC > LIS   12 to 19 Mar     |
| Lowest in this list   $412   |
| [Live $412 3h] [Cached $398] |
| [ price chart 16:9         ] |
| Chart | Grid | Options       |
| Alert me when it drops  [on] |
| Fares at last check. Prices  |
| can change on the booking    |
| site.                        |
| [ Live check  1 credit ]     |
+------------------------------+
```

**Content.** Free: 1 route with cached fares; other routes are visible as "Preview" (locked preview of cached fares, see the `second_route` trigger). Plus: 3 live routes checked daily within 120 days of departure, Family 5, Pro 6, Trip Pass 2. Source tags, age ("checked 3 h ago"), and a clear line that cached fares come from Aviasales and live from Google Flights. "Live check" (1 credit) refreshes now; a result under 6 hours old is free and says so.
**Interactions.** Add route sheet: origins (up to 2 airports on Free, 4 on paid, per side), destinations, date window or exact dates, trip length, travelers. Tap a fare chip to open fare detail (6.10). Alert switch opens the alert sheet: "Notify me when the lowest fare drops by" (amount or percent) or "below $" with a push permission reason screen the first time ("We will only send alerts for routes you follow"). Edit or delete route in the "..." menu.
**States.** Loading: route card skeleton with chart frame. Empty: "No routes yet", "Add where you fly from and to, and we will track fares for you.", [Add a route]. Error: "We could not load fares. Pull down to try again." Provider down: "Live fares are paused. Cached fares are still here." Offline: last saved fares with their age. No permission: viewers see fares without alert or live check controls. Limit reached: second route on Free opens `second_route`; live check with no credits opens `out_of_credits` with cached fares still shown.
**Copy.** Alert confirmation "Alert on. We will tell you if the lowest fare drops by $30 or more." Stale "Fares may have changed. Check again (1 credit)."
**Events.** `flight_route_added {route_type, days_to_departure_bucket}`, `fare_chip_tapped {source}`, `fare_alert_created {kind}`, `ai_action_started {action: live_search, credits, from_cache}` for a live check (`from_cache: true` when a result under 6 hours old is served free).
**Accessibility.** The chart has the text summary and data table (4.6); the date grid is a real table with row and column headers and heat values also printed as numbers; alert switch has a state label.

### 6.10 Fare detail and Book this fare

**Purpose.** Understand one fare and book it on a partner or the airline, honestly.
**Layout.** Large figure (mono 40 px) for the price, "per adult, economy, at last check 3 h ago", trend chip, route and times summary, then the price chart focused on this route, "Why this price" (Explain, 1 credit), then the **Book this fare** compare list.

```
+------------------------------+
| < Flights    NYC > LIS       |
| $412                         |
| per adult, checked 3 h ago   |
| Down $42 since Tuesday       |
| [ chart ]                    |
| [ Explain this fare  1 cr ]  |
|                              |
| Book this fare               |
| Sorted by price, lowest first|
| +--------------------------+ |
| | Aviasales      $412  3h  | |
| | [ Book on Aviasales   ]  | |
| +--------------------------+ |
| | Kiwi.com       $431  3h  | |
| | [ Book on Kiwi.com    ]  | |
| +--------------------------+ |
| Airline site   price varies  |
| [ Search on the airline's  ] |
| [ site                     ] |
| We earn a commission if you  |
| book here. The price can     |
| change on the booking site.  |
| [ Mark as booked ]           |
+------------------------------+
```

**Content.** The compare list shows two or three providers when a live or cached price exists for each, each row with provider name, price, the date and age of the price, and a button. The airline's own site row is always present and equal weight. Sort statement always shown; ties broken alphabetically, never by commission. If the booking page price differs, the copy says so after return ("The price on the partner site can be different. Check it before you pay.").
**Interactions.** Book opens the partner link in the in-app Safari view through `/go/{click_id}`. After return: a sheet "Did you book it?" with "Yes, mark as booked", "Not yet", "I booked somewhere else". "Mark as booked" sets the chosen flight (which can set trip dates after confirmation), puts a Booked ticket stub on the card and offers the soft next step "Plan your days" (no paywall, no partner card). "Explain this fare" (1 credit) gives a short Haiku answer with sources.
**States.** Loading: figure and chart skeletons. Empty providers: only the airline route: "We do not have a partner price for this fare. You can search on the airline's site." Error: "We could not load this fare. Try again." Offline: shows the saved fare; Book buttons are disabled with "Connect to the internet to book." Stale (over 24 h): a warning-ink line "This price is 2 days old. Check again (1 credit)." Limit: Explain with no credits opens `out_of_credits`.
**Copy.** Disclosure as in 4.13. No "best", "deal", "hurry" words.
**Events.** `fare_detail_viewed {age_hours_bucket}`, `partner_link_tapped {program, placement: flight}` (the click id is added server side), `fare_marked_booked`, `ai_action_started {action: explain}`.
**Accessibility.** Price change is announced as text, not color; each provider row is a labeled group ("Aviasales, 412 dollars, checked 3 hours ago, Book on Aviasales, opens in a browser").

### 6.11 Stays: shortlist, compare and vote

**Purpose.** Collect places to stay, compare them fairly and decide as a group.
**Layout.** Section header with "Add a stay" and a List or Compare segmented control. The list is sorted by a visible control (Hearts, Price, Added, Rating; the API `sort` values `votes`, `price`, `created`, `rating`), default Hearts. Lodging cards (4.10). A sticky bottom bar appears when 2 to 4 are selected: "Compare (3)".
**Add a stay sheet.** Four ways: Paste a link (Airbnb, Vrbo, Booking.com or any URL; the text below says "We never change your links and never load these pages."), Search (partner search results with the sort statement, "Save to shortlist" first and "View" second), Add by hand (name, link, price per night, notes), and "Paste a booking" for a stay you already booked (1 credit, see 6.13). On web, the bookmarklet card imports from a page the user has open.
**Compare.** 2 to 4 columns (Free compares 2): price per night, total, per person, bedrooms, area, cancellation note, votes, notes. Differences are highlighted with a pattern and text, not color alone. Sticky first column on phones with horizontal scroll.
**Voting.** A heart toggle per person (a `lodging_votes` row exists while the heart is on; 03 section 5.8). There is no down vote. Tap the count to see names. Owner and editors can mark a stay "Booked" (ticket stub) or "Rejected". A poll can be started from a stay pair ("Start a poll", see 6.21).
**Partner surfaces.** A separate "Compare on other sites" link (labeled partner search) and, only for hosts with an approved program, a "Book via partner" button, all using 4.13 wording. Airbnb has plain links only. "Cheaper on <partner>" appears only with real dated price data.
**States.** Loading: three card skeletons. Empty: "No stays yet", "Paste a link or search to start a shortlist.", [Add a stay]. Error: "We could not save this stay. Check the link and try again." Offline: list readable, adding allowed as a queued edit with a "Waiting to sync" chip. No permission: viewers can vote but not add or mark. Limit reached: saving the 9th stay on Free puts it in a locked "Later" list with `ninth_stay` paywall, free path "Keep in Later" and nothing is lost.
**Copy.** Import helper "We never change your links." Vote summary "3 of 4 like this".
**Events.** `lodging_option_added {source}`, `lodging_voted {voted}`, `lodging_compare_opened {count}`, `lodging_booked`, `partner_link_tapped {program, placement: stay}`.
**Accessibility.** Vote buttons use `aria-pressed` and name the person; the compare table is a real table with `th` scope; difference highlights are also announced ("Cheaper than the others by $40").

### 6.12 Plan: calendar and day view

**Purpose.** Plan each day together.
**Layout.** Section header with a segmented control (Days, Calendar, Map) and an "Ideas" button. **Days** is the default list of day cards (4.8) with a day chip strip pinned at the top (D1 to D7, today highlighted). Day detail is a push screen with the timeline (4.7) above the ideas tray.
**Content.** Each day: items in order with times, travel time between items when known, and a summary. Ideas tray holds saved places not yet scheduled. "Draft this day" (1 credit) and "Draft the trip" (4 credits) live in the AI sheet (6.15). On the arrival day, a transfer card can appear (4.13, one per view), on a drive day a car card.
**Interactions.** Tap an item to edit. Add with "+" (6.13). Reorder: drag handle (web, and long press on touch) or "Move to..." sheet; the new position is stored in `sort_order`. Swipe left on an item: Delete (undo toast); swipe right: Mark done. Pinch on map. Pull to refresh; polling every 15 to 30 s on shared trips, with a "Sam added Bairro Alto to Day 2" highlight for 6 s and an entry in Activity.
**States.** Loading: day card skeletons. Empty trip: "Nothing planned yet", "Add a place, or ask for a draft to start from.", [Add a place] [Draft the trip, 4 credits]. Empty day: "Free day". Error: "We could not load your plan. Pull down to try again." Offline: readable, edits to notes and checkmarks queue, itinerary structure edits show the read-only banner "Offline. You can read your plan and check things off. Reconnect to rearrange." Conflict: 409 sheet with both versions and "Keep mine" or "Use theirs". No permission: viewers cannot edit, can comment. Limit reached: none on the plan itself (the calendar is never gated).
**Copy.** Conflict "Sam changed this while you were editing."
**Events.** `plan_viewed {mode}`, `itinerary_item_moved {method}`, `itinerary_item_deleted`, `edit_conflict_shown {resolution}`.
**Accessibility.** Drag has full keyboard and VoiceOver alternatives (Move up, Move down, Move to day); timeline blocks have text labels with time and duration; the day chip strip is a `tablist`.

### 6.13 Add item

**Purpose.** Add a place, activity, transport leg, reservation or note to a day or to Ideas.
**Layout.** Bottom sheet, large detent. Top: search field "Search places" with category chips (Sights, Museums, Food, Outdoors, Nightlife, Shopping, Getting around), which are the `item_category` values `sights`, `museum`, `food`, `nature`, `nightlife`, `shopping` and `travel`; an item that fits none is `other`. Results (place cards) sorted by relevance then distance with the sort label. A "Custom item" row at the bottom.
**Content.** A place result opens a detail view (photo, hours, website, Wikipedia summary with attribution, "Explain" 1 credit) with "Add to Day 2" (day picker), "Save to ideas", and optional time. The place detail may carry a "Tickets" or "Book a table" partner chip on the detail view only (4.13). "Paste a booking" (1 credit) takes a confirmation email or text, shows a draft flight, stay or activity for confirmation (names and booking references are replaced with placeholders before anything is sent to the AI provider, and nothing is fetched from any link in the text), and "Add to plan" creates the item or stay. Custom item: title, time, duration, cost, link, note, category (one of the eight above; it chooses the color group and icon) and status (Idea, Planned or Booked, `item_status`).
**Interactions.** Add closes the sheet with a toast "Added to Day 2. Undo" and scrolls to the item. Adding while offline queues the edit.
**States.** Loading: result row skeletons. Empty: "No results. Try a different name, or add it yourself." Error: "Place search is not working right now. Add it by hand and we will match it later." Limit: places search is capped per day on Free (30); at the cap: "You have reached today's 30 place searches. Saved places still work. Searches reset at midnight." with "Add by hand".
**Events.** `itinerary_item_added {category, source}`, `place_searched {result_count_bucket}`.
**Accessibility.** Result list is a listbox; the day picker is a native select on iOS; "Add" buttons include the place name in their label.

### 6.14 Plan map

**Purpose.** See the days spatially and plan walking time.
**Layout.** Full-bleed MapLibre map under the section header, numbered pins in group colors (`tp-map-pin`), a day filter strip (All, D1 to D7), and a half-height list sheet that drags up. A button group: "Open in Apple Maps", "Open in Google Maps".
**Interactions.** Tap a pin to select and highlight the list row; tap a list row to fly to the pin. A route line connects a day's items in order with a walking time label. Location dot only if the person has granted location (asked on tap of "Show me on the map").
**States.** Loading: map tiles with a skeleton frame. Empty: "No places on the map yet. Add a place to a day." Error: "The map did not load. Try again." with a list view fallback. Offline: cached tiles at low zoom for the trip area when downloaded, else "Maps need a connection. Your list is below." No permission: location denied message as in 6.4.
**Events.** `map_opened`, `map_pin_selected`, `maps_handoff {app}`.
**Accessibility.** Every pin has a list equivalent; the map is not required to complete any task; attribution stays visible; pin numbers are also in the list rows.

### 6.15 AI actions: explain, draft, research

**Purpose.** One sheet for every AI action, with the price up front.
**Layout.** An "Ask" button (sparkle glyph replaced by a plain "Ask" label) in the trip header opens a bottom sheet. Header: title, balance pill ("27 credits"), trip AI toggle state. Body: action rows, each with a one-line description and a credit cost chip:

| Action | Credits | Where else it appears |
|---|---|---|
| Explain (short answer about a fare, place or plan) | 1 | Fare detail, place detail |
| Suggest a packing list (from the weather and your plans) | 1 | Before you go, Packing |
| Paste a booking (turn a confirmation email into a draft) | 1 | Flights, Stays, Add item |
| Live check (flight or rental) | 1 | Flights, Stays |
| Draft this day | 1 | Day card |
| Draft the trip (up to 14 days) | 4 | Plan empty state |
| Research a question (5 searches, 8 fetches) | 8, or 1 from shared cache | Notes, Plan |
| Deep agent run (fare hunt or research) | 40, or 8 from shared cache | Flights, Overview |

**Content and flow.** Choosing an action asks for the minimum input (a question, or which day). A confirm step appears at 6 credits or more: "Research this question? Costs 8 credits. You have 27, so 19 left." with [Start research] and [Cancel]. A shared cache hit is stated before spend: "Someone already researched Lisbon in March this week. Use that for 1 credit?" with [Use it, 1 credit] and [Research fresh, 8 credits].
**Drafts.** Output (including a packing list or a parsed booking) appears as a preview the person edits before anything is added; "Add to plan" is explicit. Drafts carry "Drafted by AI from your dates and places. Check hours and prices." and sources when a web search was used. AI output never contains partner links or partner names.
**First use.** The AI consent screen (once per account): "Hermi sends your destination, dates and what you type to Anthropic to answer. We do not send your name, email or other travelers' names, and it is not used to train models." [Allow] [Not now]. Revoking is in Account, Privacy.
**Interactions.** Cancel works during a wait; a failed or empty action refunds automatically and says so ("No charge. That did not finish."). An agent run is stoppable and billed by turns used (minimum 8 credits) and the sheet says it before stopping.
**States.** Loading: streaming text with a stop button. Empty: n/a. Error: "That did not work, and you were not charged. Try again." Rate limited (10 AI actions a minute): "Slow down a little. Try again in a few seconds." Offline: actions disabled, "AI needs a connection." No permission: viewers cannot run AI; the owner may turn AI off for the trip ("AI is off for this trip. Ask Sam to turn it on."). Limit: out of credits opens `out_of_credits_draft` or `out_of_credits_research` (6.27), monthly provider ceiling reached shows "AI is paused until 1 Nov. Saved data and cached fares still work."
**Events.** `ai_sheet_opened`, `ai_action_started {action, feature, credits, from_cache}` (fired when the person confirms), `ai_action_completed {action, feature, outcome, duration_seconds_bucket}` (a refund is `outcome: refunded`), `ai_consent_shown`, `ai_consent_granted`, `ai_consent_declined`.
**Accessibility.** Cost chips are read as part of the button name; streaming text is in a polite live region updated per sentence, not per token; Stop is always the first focusable control while running.

### 6.16 Agent run: live progress and evidence

**Purpose.** Watch a deep run, trust what it found, and keep the good parts.
**Layout.** Run screen pushed from the AI sheet. Header: goal ("Find the cheapest way to fly NYC to Lisbon, 10 to 20 March"), a ticket stub status (Running, Done, Stopped, Failed), elapsed time in mono, credits reserved ("40 credits, billed by use"), and a **Stop** button. Body: a **timeline** of steps (Searching, Reading a page, Checking a fare, Saving a finding) with time, and below it **Findings** grouped as Fares and Notes. Each finding is an **evidence row** (4.21): what was found, the source page title and domain, the date seen, a quote, "Open source".

```
+------------------------------+
| < Lisbon      Agent run      |
| Find the cheapest NYC to LIS |
| RUNNING  02:14   Stop        |
| 40 credits, billed by use    |
|                              |
| o Searching flights    00:12 |
| o Reading kayak page   00:41 |
| * Checking a fare...   now   |
|                              |
| Findings (2)                 |
| Fare  $398 TAP, 12 Mar       |
|  theflightsite.com  seen     |
|  today 10:42 [Open source]   |
|  [Save to trip] [Dismiss]    |
| Note  Tram 28 is crowded ... |
|  lisbon-guide.org  [Open]    |
+------------------------------+
```

**Content.** Only findings with a source page and a capture date are shown as findings; rejected items go to a collapsed "Not saved (2)" list with the reason ("No page link", "Page did not show that fare"). Fares are labeled "Seen on a page during this run. Prices can change." The final ticket stub lands with `touchdown` and a summary: "Done. 2 fares and 3 notes saved. 31 credits used."
**Interactions.** The run continues if the app is backgrounded; a push and an Activity item announce completion. "Save to trip" on a finding adds it to fares or notes with its evidence attached; "Dismiss" removes it from view. Stop asks "Stop this run? You will be billed 14 credits for the work done." with [Stop run] and [Keep running].
**States.** Loading (queued): "In the queue. About 1 minute." with Cancel and no charge. Empty result: "Nothing saved. You were not charged." Error: "The run stopped because the price check service is down. You were not charged." Offline: progress is on the server and resumes when online, banner "You are offline. The run keeps going." No permission: only the starter can stop; others can read findings. Limit reached: one run at a time, "A run is already in progress for your account. Wait for it to finish or stop it."
**Events.** `ai_action_started {action: agent_run, feature, credits, from_cache}`, `agent_finding_saved {kind}`, `ai_action_completed {action: agent_run, outcome}` (a run the person stops is `outcome: partial`).
**Accessibility.** Timeline is an ordered list with the current step marked "current"; status changes are polite announcements ("Checking a fare"); the ticket stub carries text, not only color; evidence links say "Open source, theflightsite.com, opens in a browser".

### 6.17 Taster run

**Purpose.** Let a Free person try one deep agent run, once, so they see the best feature before paying.
**Layout.** An entry card on Flights or Overview for accounts whose taster is unused: "Try a deep run, free once", a two-line explainer, and a **Start free run** button with a chip "Free, one time". The confirm step reads the normal confirm copy with "Free taster" in place of the cost.
**Content.** Same run screen as 6.16 with a "Taster" ticket stub. Runs with the same caps (20 turns, 10 searches, 10 fetches, $0.80 hard stop). At the end, a soft card "That was your free run. Runs cost 40 credits (8 when someone already researched it). Plus includes 60 credits a month." with "See plans" and "Done" (equal weight). It is a result-moment offer, not a paywall sheet, and it follows the one-per-session and 7-day mute rules.
**States.** Used: the entry card is replaced by the normal "Deep run, 40 credits" action. Offline: disabled. Error or empty result: the taster is not consumed ("That did not finish, so your free run is still available.").
**Events.** `taster_offered`, `ai_action_started {action: agent_run, taster: true}`, `ai_action_completed {action: agent_run, taster: true, outcome}`, `taster_upsell_shown`.
**Accessibility.** The one-time nature is stated in text, not only a badge.

### 6.18 Notes and evidence

**Purpose.** Keep the trip's knowledge in one place, with where each fact came from.
**Layout.** Reached from Overview. Two tabs in a segmented control: **Notes** (written by people) and **Found by AI** (saved findings). Notes are a reverse-chronological list with author avatar and "private" lock; each note can attach to the trip, a day, an item or a stay. Found by AI lists evidence rows grouped by topic, each with the captured date.
**Interactions.** Add a note (plain text, links auto-detected). Mark private (excluded from AI context and from other members). Pin a note to Overview. "Research this" (8 credits) starts research from a selected note. Tap an evidence row to see the quote and open the source. "Stale" appears on findings older than 30 days ("Seen 12 Aug. Check it is still true.").
**States.** Loading: row skeletons. Empty: "No notes yet", "Write down what you learn. Anything an AI finds is saved here with its source.", [Add a note]. Error: "We could not load notes. Pull down to try again." Offline: notes can be added and ticked (queued); evidence is readable. No permission: viewers can read and comment. Limit: none.
**Events.** `note_added {scope, private}`, `evidence_opened`, `finding_saved_to_notes`.
**Accessibility.** Private state is text plus icon; evidence links name the domain; long notes are not truncated for screen readers.

### 6.19 Present mode

**Purpose.** Walk the group through the plan on a phone, a TV or AirPlay, and print or share it.
**Layout.** Outside the app shell, full screen, `deck-*` type utilities so text scales by container size. Slides: Title (destination, dates, travelers, route pattern), one per Destination, Flights per route, Stays shortlist, one per Day (map plus items), and Closing "Trip at a glance" (existing slide kinds). An optional last slide "Book the plan" lists partner links with the disclosure line, off by default for the owner to turn on. Chrome (hidden after 3 s of no input): close, slide counter, overview grid, share, print.
**Interactions.** Phones in portrait: swipe up and down between slides in a story layout, tall slides scroll. Landscape and iPad: swipe or arrow keys, tap right or left third. Overview grid shows thumbnails. Screen stays awake (wake lock). Share creates a read-only link with redaction switches (hide addresses, prices, notes and traveler names, which show as "Traveler 1"; all hidden by default; the link expires after 90 days unless the owner picks another length up to a year). Print or PDF one slide per 16:9 page, links live, checklist without partner buttons. Free shares carry a small "Made with Hermi" footer and the PDF a footer mark; paid tiers do not.
**No partner content during playback.** No cards, no logos, no interstitials on any normal slide.
**States.** Loading: title slide appears first, others stream in. Empty trip: "There is nothing to present yet. Add a day to your plan." Error: "We could not build the presentation. Try again." Offline: works from the offline copy, map slides use the static route plot. No permission: viewers can present. Limit: none (the footer is the only difference).
**Copy.** Footer "Made with Hermi".
**Events.** `present_mode_started {slide_count_bucket}`, `share_link_created {redaction_level}` (sharing from present mode), `present_mode_printed`.
**Accessibility.** Each slide has a heading and is navigable with arrow keys and VoiceOver swipe; auto-advance is never used; slide counter is announced ("Slide 3 of 9"); text stays at least 16 px.

### 6.20 Before you go checklist

**Purpose.** Help the group finish the practical things before leaving. Free on every tier.
**Layout.** Card on Overview (top three open items) and a full screen grouped by **Bookings, Getting around, Connectivity, Safety, Documents, Luggage, Money, Home, Packing**. It appears once there is a chosen flight or a saved stay, or 45 days before departure.
**Packing.** The Packing group starts as one row. "Suggest a packing list" (1 credit, `ai/packing-list`, from the weather numbers and the activity categories of the plan) opens a preview grouped as clothing, toiletries, documents, electronics, health and other; "Add to checklist" saves the lines the person keeps as tick-off rows (`kind` packing, source AI) and "Discard" saves nothing. No product links appear in it.
**Content.** Each row: a check, the title, the reason from the trip's data ("You land in Lisbon at 21:40"), a cost range if known, and three actions: **Get it** (affiliate, where one exists), **I have this**, **Not needed**. At least half the rows have no partner (documents, money, home, packing). Visa and entry rows link to the official government site first. Insurance rows appear only once a flight is booked, use insurer approved wording only, and never include AI advice. eSIM is not shown for domestic trips.
**Interactions.** Done and dismissed persist per trip and sync across members. One optional push seven days before departure. Partner rows follow 4.13 with the disclosure line on each button row. A "Hide booking links" setting collapses them.
**States.** Loading: row skeletons. Empty (nothing applies): "You are all set. Nothing to do before you go." Error: "We could not load your checklist. Try again." Offline: fully usable, partner buttons hidden with "Connect to see booking links." No permission: viewers can tick their own rows only. Limit: none.
**Copy.** Row "eSIM for Portugal. You will be abroad for 7 days. Plans start around $5." [Get it] [I have this] [Not needed]. Disclosure: "We earn a commission if you book here."
**Events.** `checklist_item_shown {kind}`, `partner_link_tapped {program, placement: checklist}` (through `/go`), `checklist_item_updated {kind, status}` (done, skipped, not needed).
**Accessibility.** Checkboxes are real inputs with the title as the label; the three actions are a labeled group per row; progress "4 of 9 done" is text.

### 6.21 Group tools: polls, expenses, settle up

**Purpose.** Decide together and split real costs fairly. Polls and manual cost splitting are in Plus, Family, Pro, Trip Pass and Group Trip Pass, and Free users have them on any trip that has them; the Group Trip Pass adds up to 12 travelers and the room-block request; Stripe collection is for Group Trip Pass and Pro and arrives in Phase 4 (exact entitlements are in [01-product-spec.md](01-product-spec.md), section 5); viewing is always allowed.
**Layout.** The Group section has a segmented control: **People, Polls, Expenses, Settle up**.
**People.** Traveler list with avatars, roles, home airports (visible to members only), "Invite" (6.8), "Which traveler are you?" link if unclaimed. Travelers without accounts are first names with a color.
**Polls.** A poll card: question, options (stays, dates, restaurants, free text), votes as avatar chips, a deadline, and a result line ("Alfama loft leads, 3 of 5 voted"). Create from a stay or from "New poll". Vote is a single or multiple choice; change allowed until it closes; owner closes. A poll never implies a purchase.
**Expenses.** List of expenses with payer, amount in mono (currency and converted trip currency), who shares it, and category; "Add expense": title, amount, paid by, split (equally, by share, by amount, or exclude people), date, receipt photo. Totals: "Trip total $3,480, $870 each." Offline add is queued.
**Settle up.** A plain list of "who pays whom" reduced to the fewest transfers ("Ana pays Sam $120"), each row with "Mark as paid" (manual, available wherever cost splitting is). A payment carries the `settlements.status` as a text chip: Waiting for confirmation (`pending`, until the person paid confirms), Paid (`recorded`, or `succeeded` for a Stripe payment), Failed (`failed`), Refunded (`refunded`) and In dispute (`disputed`, Phase 4); only Paid rows reduce the balances. From Phase 4, "Collect payments" (Stripe, shown only on Group Trip Pass and Pro trips when the `group_payments` flag is on; real-world costs only, never for app features) starts a payment request with a clear fee line and opens a web checkout view; it is labeled "Payments are handled by Stripe. Hermi does not hold your money." In app purchases are never used here.
**States.** Loading: skeleton rows. Empty polls: "No polls yet", "Ask the group to choose between two stays or a date.", [New poll]. Empty expenses: "No expenses yet", "Add what you pay for and we will work out who owes whom.", [Add expense]. Error: "We could not save this expense. Check the amount and try again." Offline: queued edits with "Waiting to sync". No permission: viewers can vote in polls and see expenses, not add. Limit: on a trip whose owner is on Free with no pass, Polls and Expenses show a locked preview and the `group_tools` paywall (Trip Pass or Plus; free path: view what others add, and a free read-only balance); the room-block request and more than 8 travelers show the `group_pass` paywall (Group Trip Pass); "Collect payments" on a trip without Group Trip Pass or Pro shows the `collect_payments` paywall (Phase 4); expense viewing stays free.
**Copy.** "Split equally among 4 people, $27.50 each." "Mark as paid" confirmation "Marked as paid. Sam will see it." and, for the payee, "Ana says she paid you $120. Confirm?" (confirming moves the status from `pending` to `recorded`).
**Events.** `poll_created {option_count, subject}`, `poll_voted {selection}`, `expense_added {split_type, member_count_bucket}`, `settle_up_viewed`, `settlement_started {method}` (a Stripe payment request from Phase 4 is `method: stripe`).
**Accessibility.** Money is read with currency ("one hundred twenty US dollars"); split controls are a labeled radio group; "who owes whom" is a list, not only a chart.

### 6.22 Concierge request

**Purpose.** Let a person ask a human advisor to book something, always optional and disclosed.
**Layout.** Entry card on Stays and Overview: "Have a human book this", a two-line explainer and [Request help]. Request form as a sheet: what to book (Stays, Cruise, Complex trip, Other), dates, travelers, budget range, preferences, preferred contact. Confirmation screen with expected reply time.
**Content.** A disclosure block in plain words: "A travel advisor at our partner agency will book this for you and is paid a commission by the suppliers. You pay the same price. You can say no at any time." Perks, if any, are listed as facts, never as urgency. The advisor relationship is clearly separate from AI ("A person replies, not AI.").
**Interactions.** Submit creates a request (`concierge_requests`). Status: Received, In progress, Options ready, Closed. Replies arrive in Activity and by email. Cancel any time.
**States.** Loading: form skeleton. Empty (no requests): entry card only. Error: "We could not send your request. Your answers are saved. Try again." Offline: the form saves as a draft. No permission: owner and editors can request; viewers see the card without the button. Limit: none. Not available in the region: "Concierge is not available where you are yet. Join the waitlist."
**Events.** `concierge_card_shown {surface}`, `concierge_requested {kind, region}`, `concierge_status_changed {kind, status}` (a cancel by the requester is `status: cancelled`).
**Accessibility.** The disclosure is body text above the submit button and is read before it; the form uses standard labels and errors.

### 6.23 Discover

**Purpose.** Ideas and useful numbers for where to go, with no paid placements.
**Layout.** Large title "Discover", a search field, and sections: **Cheap fares from your airport** (cached fares by destination, sorted by price, with source and age), **Destinations** (Wikipedia summary, photo, best months, local currency), **Saved places**. A chip row filters (Beach, City, Mountains, Food).
**Content.** Every list states its sort. Fares are cached (Aviasales) and labeled. No partner cards. A destination page has "Start a trip here" and, when dates exist, the one quiet "Places to stay" card per 4.13.
**States.** Loading: card skeletons. Empty: "Add your home airport to see fares from there.", [Add home airport]. Error: "We could not load ideas. Pull down to try again." Offline: saved destinations only. Limit: none.
**Events.** `discover_viewed`, `destination_opened {country_code}`, `trip_started_from_discover`.
**Accessibility.** Cards are links with price and age in the name; sort control is a labeled menu.

### 6.24 Activity

**Purpose.** One inbox for what changed and what needs an answer.
**Layout.** Large title "Activity", a filter row (All, Alerts, Group, AI), a reverse-chronological list grouped by day. Items: fare alerts ("Fare fell $42 since Tuesday. View fare"), changes by others ("Sam added Bairro Alto to Day 2"), votes and polls, agent run results, invites, concierge replies, expense requests. Unread items have a brand dot.
**Interactions.** Tap opens the exact place (fare detail, day, poll). Swipe to mark read. "Mark all as read". Owner can revert an edit within 7 days from the item ("Undo this change").
**States.** Loading: row skeletons. Empty: "Nothing new", "Price alerts, changes from your group and finished AI runs show up here." Error: retry. Offline: cached list. Limit: none. Signed-out guest: "Sign in to get alerts and see changes from your group."
**Events.** `activity_viewed {unread_bucket}`, `activity_item_opened {kind}`.
**Accessibility.** Unread is text ("Unread") plus dot; each row is one link; the tab badge has an accessible count.

### 6.25 Account and settings

**Purpose.** Manage profile, plan, privacy and devices.
**Layout.** Large title "Account". Top: profile card (name, email, tier chip, credit balance). Groups: **Subscription and credits**, **Profile** (name, home airport, currency, traveler "Me"), **Notifications**, **Appearance** (Light, Dark, System), **Text size** (follows system Dynamic Type, with an in-app override), **Privacy** (AI consent, AI history, analytics choice), **How we earn money**, **Devices** (sign out everywhere), **Export my data**, **Delete account**, **Help and support**, **Terms and Privacy**, version.
**How we earn money.** A static page: "Hermi is paid for by subscriptions, trip passes, AI credits and commissions from partners when you book. We never show ads, sell your data, or rank anything by commission." Lists current partners, the disclosure sentence, the ranking rule, and the **Hide booking links** switch.
**States.** Loading: skeleton rows. Error: retry. Offline: profile readable, purchases disabled ("Connect to buy or restore"). Guest: sign-in row replaces the profile card. Limit: n/a.
**Events.** `account_viewed`, `setting_changed {key}`, `booking_links_hidden {value}`.
**Accessibility.** Standard iOS list semantics; switch rows are single hit areas; destructive rows come last and are labeled.

### 6.26 Subscription and credits

**Purpose.** Show what the person has, what it includes and how to change it, with no tricks.
**Layout.**

```
+------------------------------+
| < Account  Plan and credits  |
| Plus (annual)                |
| Renews 14 Mar 2027, $39.99   |
| [ Manage subscription ]      |
|                              |
| Credits           27 left    |
| 12 monthly, renew 1 Nov      |
| 15 bought, last until Jun    |
| [ Get more credits ]         |
|                              |
| Trip Pass                    |
| Lisbon, ends 4 Dec           |
|                              |
| Compare plans                |
| Restore purchases            |
| How credits work             |
+------------------------------+
```

**Content.** Current plan, renewal date and price in the store currency, pause or cancel through "Manage subscription" (opens the system subscriptions page). Credit balance split into monthly (do not roll over) and purchased (12 months, spent last) with expiry dates and a ledger link ("History": date, action, credits, refund marks). Trip Pass list with status and binding ("Not applied yet. Choose a trip"). **Compare plans** shows the tier table below in plain numbers. Packs: 50, 150, 400 credits at $2.99, $6.99, $14.99 with the per-credit price as a fact and the expiry sentence "Bought credits last 12 months."

| | Free | Plus | Family | Trip Pass | Group Trip Pass |
|---|---|---|---|---|---|
| Price | $0 | $5.99 a month or $39.99 a year (about $3.33 a month) | $8.99 a month or $59.99 a year (about $5.00 a month) | $9.99 once, 90 days | $19.99 once, 90 days |
| Active trips | 2 | Unlimited (fair use 25) | Unlimited, 6 household members | 1 trip | 1 trip, up to 12 travelers |
| Live fare routes | 0 (1 cached route per trip) | 3, checked daily within 120 days of departure | 5 | 2 (max 60 checks) | as Trip Pass |
| Credits | 12 a month | 60 a month | 150 a month, shared | 40 | 80 |
| Invite people | No, joins free | Yes | Yes | Up to 6 | Up to 12 |
| Polls and cost splitting | On trips that have them | Yes | Yes | Yes | Yes |
| Room-block request | No | No | No | No | Yes |

Pro appears in this table only after it launches ($11.99 a month or $99 a year, 240 credits, 6 live routes, scheduled routines, priority queue). The table says "Plans include generous limits, listed above. Live tracking and AI use real services, so they have fair limits."
**Interactions.** Purchases use the native sheet (RevenueCat over StoreKit 2). "Restore purchases" is on this screen and every paywall. Downgrade or lapse never deletes or hides data: a line says so ("Your trips stay yours. If a plan ends, you can still read and export everything.").
**States.** Loading: skeletons. Offline: "Connect to see your plan." Error: "We could not load your plan. Your access has not changed. Try again." Pending purchase: "Your purchase is waiting for approval." Refunded credits: ledger row "Refund, 8 credits returned". Family: pooled balance with "Spent by Ana: 12" attribution.
**Events.** `screen_viewed {screen: subscription}`, `restore_tapped {result}`, `purchase_started {product}` for a credit pack tap, `manage_subscription_tapped`.
**Accessibility.** The comparison table is a real table; the balance is text with the unit; price lines include period and the true monthly equivalent as plain text.

### 6.27 Paywalls for each trigger

All paywalls use the sheet in 4.14 and the rules in section 8. The trigger id is sent in `paywall_viewed {placement}`.

| Trigger id | When it fires | Headline | What it gives on this trip | Free path (equal weight) | Leading offer |
|---|---|---|---|---|---|
| `third_trip` | Create a third active trip on Free | "Two trips are active" | More active trips, invite people | "Archive a trip" (opens picker) | Plus annual |
| `second_route` | Add a second route on Free | "Watch a second route" | More routes with live checks | "Keep one route" (shows the preview of the second route's cached fares) | Trip Pass |
| `track_live` | Tap Track live or Refresh now without live access | "Live prices for this route" | Daily live checks for this trip, or one check for 1 credit | "Use cached fares" or "Check once, 1 credit" | Trip Pass |
| `alert_limit` | Second alert on Free | "Alerts on live fares" | More alert routes, live fares | "Keep my one alert" | Trip Pass |
| `invite` | Free owner taps Invite | "Plan together. They join free." | Invite up to 6 people | "Share a read-only link" | Trip Pass (Group Trip Pass when the trip has 5 or more travelers) |
| `out_of_credits_draft` | Draft with no credits | "Draft this day" | More credits | "Write it myself", plus a blurred preview of day one | Credit pack or Plus |
| `out_of_credits_research` | Research, Ask or Explain with no credits | "Get 8 credits for one question" | One research question | "Not now" | Small pack (50 credits, $2.99) |
| `routine` | Start a scheduled agent routine without the Pro tier (hidden until Pro launches) | "Run this on a schedule" | A sample result from the shared cache, one manual run for 40 credits | "Run once, 40 credits" | Credits, then Pro when launched |
| `ninth_stay` | Save a ninth stay on Free | "Keep all your stays" | More saved stays per trip | "Keep it in Later" | Trip Pass |
| `group_tools` | Free owner opens polls or expenses on a trip with no pass | "Decide together, split costs" | Polls and manual cost splitting on this trip | "View what others add" | Trip Pass (or Plus when the person has two or more active trips) |
| `group_pass` | Open the room-block request, or add a ninth traveler, without a Group Trip Pass | "Plan for a bigger group" | Up to 12 travelers, the room-block request, 80 credits | "Keep to 8 travelers" or "Skip the room block" | Group Trip Pass |
| `collect_payments` | Phase 4: tap "Collect payments" on a trip without Group Trip Pass or Pro (hidden until `group_payments` is on) | "Collect what everyone owes" | Payment requests through Stripe for real-world costs | "Mark as paid" | Group Trip Pass |
| `export_footer` | Share or export a Free presentation | "Share without the footer" | No footer or watermark | "Share with the footer" | Trip Pass |
| `out_of_credits_agent` | Deep agent run or fare hunt with fewer than 40 credits (taster already used) | "Run a deep search" | One deep agent run for 40 credits | "Not now" or use the cached result if one exists | Credit pack (150 credits) or Plus |
| `lifecycle_14d` | 14 days before departure on a Free trip with dates (push or email, at most once per trip) | "Your fares moved this week" | Live checks and alerts for the last two weeks | Dismiss | Trip Pass |
| `household` | Invite a second household member, or signals of a shared household | "Plan as a household" | Plus for up to 6 people, 150 pooled credits | Invite them to this trip for free | Family |
| `lifecycle_14d` | Message, not a sheet, 14 days before departure on a Free trip | "Your fares moved this week" | Live checks until you fly | Open the route | Trip Pass |

There is **no paywall** after an affiliate booking (only the soft "Plan your days" prompt), at first launch, inside present playback, during an agent run, on the taster result (it is a card, not a sheet), or on Account unless the person opens it. Default offer order when the trigger does not decide: Trip Pass first when the trip has dates within 120 days, annual Plus first when the person has two or more active trips.

### 6.28 Export and delete account

**Export.** Account, Export my data. Explains "We will email you a link to a zip with your trips as JSON, plus a readable PDF per trip. The link works for 7 days." Re-authentication (Apple, Google or code), a single [Export my data] button, then a progress row ("Preparing, usually under a day") and a notification when ready. Per-trip export (JSON, ICS, PDF) is also in Trip settings and is free on every tier. Limit: one export a day ("You asked for an export today. The link was sent to a***@gmail.com."). Error: "We could not start your export. Try again." Events: `export_requested`, `export_ready`.
**Delete account.** Account, Delete account (in app, no email or web only path). A full screen with a plain list of effects:

```
+------------------------------+
| < Account   Delete account   |
| This will:                   |
| - Sign you out everywhere    |
| - Delete your profile, AI    |
|   history and saved          |
|   travelers after 30 days    |
| - Delete trips only you are  |
|   in                         |
| - Remove you from shared     |
|   trips. Your edits stay as  |
|   "Deleted user"             |
|                              |
| Trips others are in (1)      |
|  Lisbon: [Transfer] [Delete] |
|                              |
| Your subscription is not     |
| cancelled by this.           |
| [Open subscriptions]         |
|                              |
| [ Export my data first ]     |
| [ Delete my account ]        |
+------------------------------+
```

Flow: list effects, choose what to do with trips others share (transfer to a member, or delete; if unchosen, deleted after 30 days unless a member accepts), re-authenticate, type "delete" or confirm with a destructive button, then a confirmation: "Your account is scheduled for deletion on 14 Nov. Sign in before then to restore it." The Apple Sign in token is revoked. Subscriptions are not cancelled by deletion and the screen links to the system subscriptions page without blocking. States: offline ("Connect to delete your account."), error ("We could not schedule deletion. Nothing was changed. Try again."). Events: `screen_viewed {screen: delete_account}`, `account_deletion_requested {had_subscription}`, `account_deletion_cancelled`. Accessibility: the destructive button is last in order, labeled with the consequence, and never the default focus.

### 6.29 Notifications

**Purpose.** Tell people what matters, never to sell.
**Permission.** Asked only after the first invite or the first price alert, through a reason screen: "Allow notifications so we can tell you when a fare drops or someone joins your trip." [Allow] [Not now]. Declining never blocks the feature; an in-app fallback shows in Activity.
**Types.** Price drop on a followed route (user requested), someone joined, someone changed the plan (digest, at most one an hour per trip), agent run finished, trip starts tomorrow, leave for the airport (local notification, works offline), a single optional "7 days before departure" checklist reminder, concierge reply. **Never:** promotions, partner offers, credit sales, re-engagement nags, or any push whose only purpose is a click.
**Settings.** Account, Notifications: a switch per type, a quiet hours control (default 22:00 to 08:00 local), and per-trip mute. Email has its own list with one-click unsubscribe; marketing email is a separate opt-in.
**Copy.** Push titles are facts: "Lisbon: fare fell $42", "Ana joined Lisbon", "Research finished: 3 notes saved". No exclamation marks, no emoji.
**States.** Permission denied: row shows "Notifications are off in Settings" with "Open Settings". Offline: local notifications still fire.
**Events.** `push_prompt_shown {context}`, `push_permission_result {result}`, `notification_opened {type}`.
**Accessibility.** Notification text stands alone without the icon; in-app switches describe the event, not the mechanism.

## 7. Microcopy rules

### 7.1 Voice and form

1. **Sentence case** for every heading, button, label, tab and toast ("Add a stay", not "Add A Stay"). Proper nouns keep capitals. `type-label` and `type-code` are styled uppercase through CSS only.
2. **Plain verbs.** Save, Add, Invite, Book, Open, Undo, Remove. Not "Utilize", "Leverage", "Initiate", "Submit". Buttons say what happens ("Start research", not "Continue").
3. **No em dashes or en dashes, anywhere.** Use a comma, a period or "to" for ranges ("12 to 19 Mar", "4 to 6 guests"). Hyphens only inside compound words and in technical strings. A lint rule in CI greps UI strings and docs for U+2013 and U+2014 and fails the build.
4. **Short.** Buttons one to three words. Toasts one sentence. Helper text one sentence. Explain the reason, not the feature.
5. **Second person, present tense, calm.** "You are offline", not "Connection lost!". No exclamation marks except in a success ticket stub the person earned (and even then sparingly), no emoji in product copy, no jokes in errors.
6. **Names over pronouns for people:** "Sam added a stay". Dates as "12 Mar" in lists, "Friday 12 March" in headings, times in the person's 12 or 24 hour setting.
7. **Numbers.** Always digits in UI ("3 stays"). Currency with the code when ambiguous ("$412" for the home currency, "EUR 380" for another). Counts agree with the noun ("1 credit", "8 credits").

### 7.2 Errors

An error message has three parts, in order: what happened, why if known, and how to fix it. It never blames the person, never shows a raw code, and always offers a next step. Examples:

| Situation | Copy |
|---|---|
| Network down | "You are offline. Your trip is saved on this phone. Changes will sync when you reconnect." |
| Server error | "Something went wrong on our side. Your work is saved. Try again in a minute." |
| Validation | "Enter an end date after 12 Mar." |
| Not found or no access | "This trip is not available. It may have been deleted, or you may not have access. Ask the person who shared it." |
| Conflict | "Sam changed this while you were editing. Review their version, then save yours if you still want to." |
| Rate limit | "Too many tries. Wait 10 minutes and try again." |
| Out of credits | "You have 3 credits and this costs 8. Get more credits, or ask something smaller." |
| Purchase failed | "The purchase did not go through and you were not charged. Try again, or check your payment method in Settings." |
| Partner link down | "We could not open that booking site. You can search on the airline's site instead." |

### 7.3 Prices, credits and money

1. Prices show currency symbol or code, the period and what they cover ("$39.99 a year, about $3.33 a month"). Subscriptions state the renewal date and how to cancel.
2. Fares always carry age and source ("$412, cached, checked 3 h ago") and "Prices can change on the booking site." No "from" prices in headlines without the date.
3. Credits are always "credits", shown with their cost before the action ("Costs 8 credits. You have 27."). Never dollars for AI. A cached result says "1 credit, from shared cache". Refunds say "No charge" or "Returned 8 credits".
4. Totals and per-person amounts both appear where a group is involved ("$870 each, $3,480 total").
5. Words never used: "free" for anything with a catch (say "Free, one time" or "Included"), "unlimited" (use "fair use 25 trips" or real numbers), "best price", "lowest price guaranteed", "deal", "hurry", "last chance", "only 2 left", "save up to". Comparisons say "Lowest in this list".
6. Trials state the price after the trial and the date it starts ("7 days free, then $39.99 a year from 7 Oct").

### 7.4 Commission disclosure wording

- The sentence, exact and fixed: **"We earn a commission if you book here."** It appears beside every partner button (4.13), in the Before you go rows, in present mode's optional last slide, in printed PDFs, and in email where a partner link appears.
- UK and EU storefronts add an "Ad" tag before the eyebrow. Partner-mandated text (for example Booking.com) is added after our sentence.
- Sort statements: "Sorted by price, lowest first", "Sorted by distance", "Sorted by hearts". Never "recommended" or "top picks" for anything that can carry a commission.
- Neutral links: "We never change your links." on import, and "Open" on a saved item opens the pasted URL unchanged.
- How we earn money (Account) explains the model in four sentences and lists partners.
- AI output never includes partner names, links or disclosure (it has none).

### 7.5 Reusable strings

| Key | Copy |
|---|---|
| `offline_banner` | "You are offline. You can read your trip and check things off." |
| `saved_offline` | "Saved offline, updated 2 h ago" |
| `waiting_to_sync` | "Waiting to sync" |
| `limited_trip` | "This trip is limited. Extra travelers are now viewers. Renew to restore editing. Your data is safe and you can export it any time." |
| `ai_disclaimer` | "Drafted by AI from your dates and places. Check hours and prices." |
| `fare_age` | "Checked 3 h ago" |
| `no_charge` | "No charge. That did not finish." |
| `restore_done` | "Purchases restored." |
| `restore_none` | "We did not find any purchases to restore for this Apple ID." |

## 8. Paywall design rules

1. **The free path is always visible.** "Not now" (or the specific free action) is a full-size button of equal weight, in the same row or directly under the primary button. It is never a small gray X, a hidden link or a swipe-only dismiss. The scrim tap and swipe down also dismiss.
2. **No paywall before value.** None at first launch, on the splash, in guest mode before a limit, or before the person has built something.
3. **One per session.** At most one paywall sheet is shown per app session. Further triggers in the same session show an inline locked state with the free path, not a sheet.
4. **7-day mute.** Dismissing a paywall mutes that trigger for 7 days (server side, per account and trigger, so it follows across devices). The action the person wanted is either blocked with the free alternative or simply not offered; it does not reappear as a nag. Buying ends the mute.
5. **Say what it gives on this trip.** The first line after the headline names the concrete result for this trip ("Live prices for Lisbon until 4 Dec"), with real numbers from the README.
6. **Up to three options**, in this order of prominence, chosen by the rules in 6.27: Trip Pass (lead when the trip has dates in the next 120 days), Plus annual (pre-selected where it is the lead subscription), Plus monthly under "More options". Credit packs appear only at credit triggers. Family is under "More options" only for people with a household signal. Pro is hidden until it launches.
7. **Annual is pre-selected with the true monthly equivalent**: "Plus annual, $39.99 a year, about $3.33 a month" next to "Plus monthly, $5.99 a month". The saving is stated as a number ("Save $31.89 a year"), never a percent alone or a crossed-out fake price.
8. **Trials and renewals are plain.** The trial line reads "7 days free, then $39.99 a year from 7 Oct. Cancel any time in Settings." A reminder is sent before conversion. No trial for Trip Pass or credit packs.
9. **Restore purchases** is a visible text button on every paywall and on the Plan and credits screen. It shows a result either way (`restore_done`, `restore_none`).
10. **No countdowns, no invented scarcity, no "limited offer", no pre-checked upsell add-ons, no confirmshaming** ("No thanks, I like paying more"). The free button says "Not now" or names the free action.
11. **Legal row** under the buttons: price and period, renewal, cancellation, Terms, Privacy. 12 px minimum, never hidden.
12. **Never next to affiliate content** and never on the same screen as a partner card. After an affiliate booking there is no paywall.
13. **Confirm credit spends, do not paywall them.** Spending credits is a confirm sheet (6.15), not a paywall; it appears for 6 credits or more and always shows the balance after.
14. **Resume the task.** After a purchase the sheet closes with a touchdown, the blocked action resumes (the route is added, the invite sheet opens) and the plan or pass is bound to the trip when it applies ("Apply to Lisbon?" picker for a Trip Pass).
15. **Downgrades never take data.** Copy and behavior follow `limited_trip`. Archived trips stay readable and exportable forever on Free.
16. **Measure without manipulating:** events `paywall_viewed {placement, offer_shown}` (the trigger id from 6.27 is the `placement`), `paywall_dismissed {placement}`, `purchase_started {product, period}` (choosing an option and tapping the purchase button are one event), `purchase_completed {product, period, is_trial}`, `purchase_failed {product, reason}` (a cancelled sheet is `reason: cancelled`), `restore_tapped {result}`.

```
+------------------------------+
|            ------            |
|     (static route pattern)   |
| Plan together. They join     |
| free.                        |
| Invite up to 6 people to     |
| Lisbon, with live fares until|
| 4 Dec.                       |
|                              |
| (o) Trip Pass   $9.99 once   |
|     90 days, this trip       |
| ( ) Plus annual  $39.99 a yr |
|     about $3.33 a month      |
| More options                 |
|                              |
| [ Get Trip Pass  $9.99 ]     |
| [      Not now          ]    |
| Terms  Privacy  Restore      |
| purchases                    |
+------------------------------+
```

## 9. Accessibility

Target: **WCAG 2.2 level AA** on web and iOS, plus Apple's Human Interface accessibility guidance. Accessibility is part of the definition of done for every screen in this file.

### 9.1 Contrast and color

Body text 4.5 to 1, large text and UI boundaries 3 to 1 (measured table in 2.3). Color never carries meaning alone: fare trend uses an arrow and words, votes use an icon and a count, group colors use an icon and a label, traveler colors come with a name or initials, status uses text. Focus indicators are at least 2 px, 3 to 1 against neighbors, and never covered by sticky bars (scroll padding under the tab bar and sticky header). Heat grid cells print their price.

### 9.2 Structure, keyboard and focus

One `h1` per screen. Landmarks: header, nav, main. Section strips are `tablist`. Every interactive element is reachable by keyboard on web in a logical order, with visible focus. Sheets trap focus, restore it on close, close on Escape. No keyboard traps, no timing limits except session expiry (with a warning). Drag and drop has non-drag alternatives (WCAG 2.5.7). Targets are at least 24 by 24 CSS px on web (2.5.8) and 44 by 44 pt on touch. Consistent help: a Help link in the same place on every screen's overflow menu (3.2.6). Redundant entry is avoided: trip dates and travelers are prefilled from the trip (3.3.7). Authentication has no cognitive test and supports paste in the code field (3.3.8).

### 9.3 VoiceOver and Dynamic Type

- Every icon button has an `aria-label` that names the action and object ("Remove Bairro Alto from Day 2"). Decorative route patterns and icons are hidden.
- Custom controls expose roles and states (`aria-pressed` for votes, `aria-expanded` for day cards, `aria-selected` for tabs, `aria-current="step"` in the run timeline).
- Dynamic content uses live regions: toasts (`status` or `alert`), run progress (polite), credit balance changes (polite). Loading states expose `aria-busy`.
- Rotor and headings: each day card is a heading; each list has an accessible count ("Stays, 4 items").
- Reading order matches visual order. Price, age and source are read in one phrase ("412 dollars, cached, checked 3 hours ago").
- **Dynamic Type:** all text is `rem`. The native shell reads the system size through `@capacitor/text-zoom` and applies it to the root font size, supporting up to Accessibility XXXL (about 310%). Layouts reflow rather than clip: the section strip scrolls, the tab bar labels stay (icons stay 24 px, labels wrap to two lines then truncate only at the largest sizes with the accessible name intact), cards stack their metadata, tables scroll horizontally with a sticky label column, buttons grow in height. Test each screen at default, Large and the largest accessibility size.
- Web supports 200% browser zoom and 400% reflow at 320 px width with no two-dimensional scrolling (except the chart and compare table, which scroll in their own region).

### 9.4 Reduced motion, bold text and other system settings

`prefers-reduced-motion` and iOS Reduce Motion: no route draw-on, no touchdown scale, no parallax, no sliding sheets (fade instead), no shimmer, no pulsing. Information previously carried by motion (a new item highlight) is also carried by a static label ("New"). Bold Text raises body weight to 600. Increase Contrast swaps `--tp-rule` and `--tp-edge` to the ink color. Smart Invert and Differentiate Without Color are honored by the rules above. Voice Control: every control has a visible text label or a matching accessible name (WCAG 2.5.3). Captions and transcripts are required for any future video.

### 9.5 Testing

Automated: `@axe-core/playwright` in the e2e suite on every screen in light and dark; lint for missing `aria-label` on icon buttons; contrast unit test over the token pairs in 2.3. Manual before each release: VoiceOver walkthrough of onboarding, create trip, fare detail, stays vote, run and paywall; Dynamic Type at the largest size; Reduce Motion on; keyboard only on web. An accessibility statement is published and the App Store Accessibility Nutrition Labels are declared when true.

## 10. Responsive breakpoints

| Name | Width | Layout |
|---|---|---|
| Phone | 0 to 479 px | One column, bottom tabs, sheets, 16 px gutter, full-width primary buttons |
| Large phone | 480 to 767 px | Same, cards up to 560 px centered, two-up chips |
| Tablet | 768 to 1023 px | Icon rail (72 px), two-column grids (trips, stays), right panel as overlay, dialogs centered |
| Laptop | 1024 to 1439 px | Full sidebar (248 px), content 720 to 1120 px, persistent right rail for AI and evidence |
| Desktop | 1440 px and up | Same as laptop, content capped at 1120 px, presentation and map can go full width |

Rules: design mobile first; navigation switches at 768 px; safe areas through `env(safe-area-inset-*)`; `viewport-fit=cover`; inputs 16 px; landscape phone hides the tab bar labels and keeps icons; iPad runs the tablet layout (iPhone only in version 1, iPad later). Container queries drive the deck and dense cards so a component adapts to its container, not the window. Tables become stacked cards under 480 px except compare and settle up, which scroll horizontally.

## 11. Haptics

Through `@capacitor/haptics`, used sparingly and never the only feedback.

| Event | Haptic |
|---|---|
| Tab change, segmented control change | Selection (light tick) |
| Toggle a vote, switch, checkbox | Impact light |
| Drag pick up and drop on a day | Impact medium on drop |
| Pull to refresh reaches threshold | Impact light |
| Add item, save stay, mark done | Notification success |
| Purchase success, run finished, trip marked booked | Notification success (paired with the touchdown) |
| Error, blocked action, conflict | Notification error |
| Limit reached, low credits warning | Notification warning |
| Destructive confirm (delete) | Impact heavy, once |

Rules: off when the system or Low Power Mode disables them, and a Settings switch "Haptics" turns them off; no haptics on scroll, timers or agent progress steps; at most one haptic per action.

## 12. Dark mode

Dark mode follows the system by default with an Appearance setting (Light, Dark, System), applied through the `.dark` class on the root (as today in `theme.tsx`) and `color-scheme` so native controls match. Dark values are the tokens in 2.1 and 2.2 and are validated to the same contrast rules (table in 2.3).

Rules: the ground is deep night `#0B1A2A`, cards `#12263A`, not black; shadows give way to lighter surfaces and 1 px rules; brand shifts to the light sky `#6CC4FF` with dark ink text (`#0B1A2A`) on it; sky surfaces (web sidebar, splash, paywall header, trip bands) become deep sky `#0E3F66`; route and traveler fills brighten (`--tp-route-a` `#FF7A93`, `--tp-route-b` `#FFD45C`) and the route pattern sits at 50 to 70% on paper and sheet; chart and heat ramps use the dark sets and invert direction so the most prominent step is still the cheapest; images get a 4% dark overlay only when they sit under text; the logo uses the dark lockup and its tile stays sky `#2AA5FF`; the present deck follows the mode but print always forces light; the app icon is the same in both modes. Test every screen and every paywall in both modes, and with Increase Contrast.

## 13. Analytics conventions

Product analytics uses PostHog with no ad or attribution SDKs and no ATT prompt. Event names are `object_action` in snake_case, past tense (`paywall_viewed`, `lodging_voted`). Properties are coarse and never contain free text, names, emails, addresses, exact dates of trips or note content. Every event carries `platform`, `app_version`, `tier`, `is_guest`, `locale`, `env` and a random session id; user id is the account UUID. Outbound partner clicks are logged server side through `/go/{click_id}`, with a random per-click sub-id that is never the user id. Each screen in section 6 lists its events by the names in the catalog; the full catalog, the property values and retention are in [10-quality-security-launch.md](10-quality-security-launch.md), section 4. A screen that needs an event the catalog lacks gets it added there first.
