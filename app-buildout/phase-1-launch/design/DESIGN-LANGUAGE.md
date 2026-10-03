# Hermi design language

The rules behind the Hermi look, so a screen that has no mockup still looks like it belongs. Read it with [README.md](README.md). Values live in [tokens.css](tokens.css) and the classes in [hermi.css](hermi.css); every example here names the class or token and the number. Behavior, states, copy and events are in [05-ui-ux-spec.md](../05-ui-ux-spec.md).

## 1. The idea

Every trip fact is a ticket: a flight, a stay, a day, a plan, a result. Every trip is a place on a calm illustrated map. Two travelers' routes, pink first and yellow second in the order they joined, tie the map, the tickets and the timeline together. The ground is warm paper, and sky blue is a fill accent, never text.

## 2. Foundations

### Surfaces

| Role | Token | Light | Dark | What sits on it |
|---|---|---|---|---|
| Paper | `--tp-paper` (`--background`) | `#FBF5EA` | `#0B1A2A` | The page ground, tickets, tiles, list cards, inputs on a sheet |
| Sheet | `--tp-sheet` (`--card`) | `#FFFDF8` | `#12263A` | Bottom sheets, floating bars, map chips, round buttons |
| Sunken | `--tp-sunken` (`--secondary`) | `#F5ECDA` | `#1A3149` | Ticket stubs, wells, chips, the seg track |
| Rule | `--tp-rule` (`--border`) | `#E3D6BC` | `#27405A` | 1 px hairlines and card borders, decoration only |
| Edge | `--tp-edge` | `#6A86A0` | `#6C88A3` | Borders of controls (secondary button, seg pill, radio, tear dots) |

**Why tickets are paper on a sheet.** The sheet is the lighter warm white, so a ticket (paper) reads as a printed card lying on it. The stub steps down to sunken, which is the tear-off. A 1 px rule hairline follows the ticket's outline and its notches (`.h-ticket` draws it with a drop-shadow chain). In dark the order flips in lightness but not in role: the ticket body is the darker paper, the stub is the lighter sunken.

### Color roles

- **Sky** (`--tp-sky`) is a fill and never text. It is the logo tile, the hero ticket head, the paywall header and the agent run head. Text on it is `--tp-sky-ink`. In dark it becomes deep sky `#0E3F66`, but the logo tile stays `#2AA5FF`.
- **Brand** (`--tp-brand`) is for actions and links: the primary button, links, the focus ring, the active tab and the selected state. Text on a brand fill is `--tp-brand-ink`.
- **Ink** (`--tp-ink`, `--tp-ink-soft`) is text and icons. Soft ink is secondary text, 13 px and up.
- **Traveler colors** (`--tp-traveler-1` to `-8`, initials in `--tp-traveler-ink-N`) identify people, in join order: pink, yellow, teal, violet, orange, green, blue, magenta. They never mean status or price, and they always come with a name or initials.
- **Route colors** (`--tp-route-a` pink, `--tp-route-b` yellow) are traveler 1 and 2 as decoration. When pink or yellow carries text, use `--tp-route-a-ink` or `--tp-route-b-ink`.
- **Category colors** (`--cat-culture`, `-food`, `-outdoors`, `-shopping`, `-neutral`) tint plan nodes and pins. An icon and a label always come with the color.
- **Status colors**: `--tp-success` (booked, done, a price that fell), `--tp-warning` and `--tp-warning-ink` (a price that rose, a cost you cannot cover; small text uses the ink), `--tp-danger` (errors). Chart series use `--viz-live`, `--viz-cached`, `--viz-agent`, `--viz-google` by price source, never by rank.

### Type roles

Three families: Fredoka for names, codes and titles; Atkinson Hyperlegible Next for body and labels; Atkinson Hyperlegible Mono for numbers. Sizes below are what the kit uses.

| Role | Face and weight | Size and line | Where |
|---|---|---|---|
| Display | Fredoka 700, tracking -0.01em | 40 px, line 1.05 (`.h-display`) | Welcome headline, paywall headline |
| Airport codes | Fredoka 700, tracking 0.06em, uppercase by CSS | 36, 40 or 44 px (`.h-codes`, `--md`, `--lg`) | Tickets and passes; 44 px on the hero pass |
| Page title | Fredoka 600 | 30 px, line 1 (`.h-pagehead__title`) | Root screens such as Trips |
| Sheet title | Fredoka 600 | 24 px (`.h-sheet__title`) | AI sheet |
| Ticket name | Fredoka 600 | 22 px, 26 px on the hero (`.h-ticket__name`) | Destination on a ticket |
| Heading | Fredoka 600 | 20 px (`.h-heading`), 18 px (`--sm`) | Section headings |
| Label | Atkinson Next 700, tracking 0.08em, uppercase by CSS | 11 px (`.h-label`) | Eyebrows, field labels, AM and PM |
| Body | Atkinson Next 400 | 15 px; 17 px for a lead (`.h-lead`) | Text |
| Row title | Atkinson Next 600 | 15 px | List and ticket titles |
| Small | Atkinson Next 400 | 13 px (`.h-soft`, `.h-disclosure`) | Captions, ages, disclosure |
| Mono data | Atkinson Mono 600, tabular | 13 to 15 px (`.h-mono`, `.h-num`) | Prices, times, counts, dates |
| Figure | Atkinson Mono 700, tracking -0.03em | 36 px (`.h-figure`), 20 to 22 px for a stay or plan price | The fare, a price block |
| Buttons | Atkinson Next 600 | 16 px primary and secondary, 14 px compact, 13 px in a stub | Actions |

Text sizes are `rem` in `hermi.css`. Never set body text below 13 px.

### Spacing

- **Gutter:** 16 px on phones. A sheet body is `padding: 8px 16px 0`.
- **Gaps:** 6 px between items in a sheet body (`.h-sheet__body`), 8 px between tickets (`.h-stack--roomy`), 4 px between provider rows (`.h-stack--tight`), 8 px between tiles (`.h-tiles`), 22 px between ticket fields (`.h-ticket__fields`).
- **Heading margins:** a section heading is `6px 0 4px` (`.h-heading--section`), `8px` above after a stack.
- **Targets:** 44 by 44 pt. A visual may be smaller (the section strip pill is 34 px) if its hit area is 44.
- **Scale:** `--tp-space-1` to `-16` are 4 to 64 px.

### Radii

| Surface | Radius | Class or token |
|---|---|---|
| Ticket | 18 px, notch 9 px | `.h-ticket` |
| Large ticket (welcome, paywall) | 24 px, notch 10 px | `.h-ticket--lg` |
| Side-stub ticket | 14 px, notch 7 px | `.h-ticket--side` |
| Card (tile, list card, chart, action list) | 16 px | `--radius-xl` |
| Bottom sheet, top corners | 20 px | `--radius-2xl` |
| Day chip | 14 px | `.h-daychip` |
| Buttons and the strip, seg and tab pills | full: 24 px at 48 px tall, 22 px at 44 px | `.h-btn` |
| Avatars, chips, pins, plane disc | full round | |

### Elevation

Hermi is flat. Hierarchy comes from ground color, hairlines and the sky band.

1. **Level 1.** A 1 px `--tp-rule` border and no shadow: cards, tiles, list cards, charts.
2. **Level 2.** `--tp-shadow-2` (`0 4px 16px`): the floating tab bar, the round map buttons, a ticket floating over the welcome map.
3. **Level 3.** `--tp-shadow-3`: bottom sheets. In dark it is a 1 px `--tp-sunken` top edge instead of a shadow. A modal sheet adds the scrim `--tp-scrim`.

## 3. Phone screen anatomy

All phone mockups are 390 by 844 (`.h-screen`, mockups only).

- **Safe areas:** 47 px at the top, 34 px at the bottom. In the app use `env(safe-area-inset-*)`; the kit hard-codes these two numbers.
- **Map header and sheet top:** on trip screens the sheet starts at 166 px (`--h-sheet-top`) and the map band is 194 px tall, 28 px of it under the sheet's rounded corners. The logo badge (`.h-map__badge`) sits at 44 px above the sheet top. A modal or tall sheet sets its own top: 84 px (AI actions, `.h-sheet--ai`), 104 px (agent run, `.h-screen--run`), 118 px (paywall, `.h-sheet--paywall`).
- **Round nav buttons:** 44 px circles at `top: 55px` (47 + 8), 16 px from each side (`.h-navbtn--back`, `--menu`). Level 2 elevation.
- **Sheet and grabber:** `.h-sheet` has 20 px top corners and level 3 elevation. The grabber is 36 by 5 px in `--tp-edge`, 8 px from the top.
- **Section strip:** `.h-strip` under the trip header: six pill tabs, 44 px hit area, 34 px pill, 14 px 600 type, the selected one in ink. State comes from `aria-selected`.
- **Content ends above 758 px.** The tab bar's top is at 764 px, so a screen that scrolls ends its last item at 758 px at the latest in the resting position.
- **Floating tab bar:** `.h-tabbar__bar` is 58 px tall, inset 12 px from each side, with its bottom 22 px above the screen edge, over an 83 px fade. Four tabs, labels always shown. Hide it in full-screen sheets and present mode.

**Sync indicator.** On Overview it goes under the destination name in the hero pass head, as a 13 px line in `--tp-sky-ink` ("Synced 12 s ago" with a small refresh icon); the head grows by that line and the tear moves with it (`--h-head-h`). On the other trip sections it is a small map chip (`.h-map__chip`) centered between the two round buttons, at `left: 195px; top: 77px`. States and copy are in 05 section 4.21 and 6.41. It is not mocked yet.

**Which screens get a map.** Trip-scoped screens (Overview, Flights, Stays, Plan), Trips home, and pushed details that have a route (fare detail, agent run). Account, settings and forms use plain paper with a large title and no map. The paywall and the AI sheet are a sheet over a dimmed copy of the screen they came from (`.h-dim` and `.h-scrim`).

## 4. Components

Each entry gives the class, the React name from the comment above its block in `hermi.css`, and the rules. Open [components.html](components.html) to see every one in light and dark.

### Tickets

**Anatomy.** `.h-ticket` (wrapper, draws the hairline) wraps `.h-ticket__card` (an `a`, `article` or `div`, masked with notches). Inside: an optional `__head`, a `__body`, and a `__stub` that starts with `__tear` (a dotted line made of a repeating radial-gradient). Notches are positioned by custom properties: `--h-tear-a` (head tear), `--h-stub-h` (stub height), `--h-stub-w` (side stub width), `--h-r` and `--h-nr` (corner and notch radius).

**Use.** Any trip fact the person can open or decide on. One ticket is one link with one full `aria-label`.

**Variants.**

| Variant | Class | Use | Stub |
|---|---|---|---|
| Hero pass, sky head | `.h-ticket--sky` with `__head--sky` | The trip overview, the top of the trip | 42 px, status and next date |
| Trip ticket | `.h-ticket` | A trip in a list on Trips home | 40 px; `--two-line` 50 px for a second line |
| Side-stub row | `.h-ticket--side` | A timeline item (72 px stub), a booking row (`--stub-wide`, 168 px stub with a button) | Vertical tear |
| Lodging ticket | `.h-ticket--actions` | A shortlisted stay with hearts in the stub | 48 px |
| Plan ticket | `.h-ticket--side.h-ticket--plan` | A paywall offer that is a radio | 100 px stub with the price |
| Fare ticket | `.h-ticket--fare` | The fare at the top of fare detail | 60 px |
| Run outcome | `.h-ticket--sky.h-ticket--run` | A finished agent run | 52 px, lands with touchdown |
| Evidence | `.h-ticket--evidence` | One agent finding with a source | 44 px with three actions |
| Welcome pass | `.h-ticket--cta.h-ticket--lg.h-ticket--float` | Splash only | 176 px with two buttons |

**React:** `<TripTicket>`, `<ItemTicket>`, `<ProviderRow>`, `<StayTicket>`, `<PlanOption>`, `<RunTicket>`, `<EvidenceTicket>`, `<WelcomePass>`.

**Do.** Keep the body on paper and the stub on sunken. Put the status in the stub. Use `a.h-ticket__card:active` for the 1 px press. **Don't.** Add a border to the card (the hairline is the wrapper's job), nest a ticket in a ticket, or put two primary actions in one stub.

### Stub tags

`.h-stub` is a boarding-pass stub tag: 28 px tall, a notched left edge, three perforation dots, an icon and a word. React: `<StatusStub>`. Never color alone.

| Status | Class | Fill and text | Icon |
|---|---|---|---|
| Booked | `--booked` | `--tp-success`, `--tp-brand-ink` | check |
| Planning | `--planning` | `--tp-brand-soft`, `--tp-ink` | pencil |
| Done | `--done` | `--tp-ink-soft`, `--tp-paper` | circle-check |
| Both like this | `--votes` | `--tp-brand-soft`, `--tp-ink` | heart |

**Don't** invent a status color; add a status to 05 first.

### Fields

`.h-field` is a label over a value inside a `dl` (`.h-ticket__fields`): label 11 px uppercase (`__label`), value mono 600 14 px (`__value`), or body text with `--text`. React: `<Field>`. **Do** keep labels one or two words ("Nights", "Travelers"). **Don't** put a sentence in a value.

### Airport codes

`.h-codes`: two codes in Fredoka 700 joined by the small twin route (pink, yellow) and a plane. Sizes 36 px (default), 40 px (`--md`, fare), 44 px (`--lg`, hero on sky). React: `<RouteCodes>`. **Do** type the code in sentence case in the DOM (`RDU`) and uppercase it with CSS only. **Don't** set codes in the body face, and keep the plane pointing right (ink on paper, cream on sky).

### Avatars and traveler colors

`.h-avatar`: 28 px, initials 11 px 700 on `--tp-traveler-N` (`--t1` to `--t8`), with a 2 px ring in the surface color. `--sm` is 24 px and `--xs` is 22 px, with no ring. `.h-avatars` overlaps by 5 px. React: `<Avatar>`, `<AvatarStack>`. **Do** give `role="img"` and the person's name as the label. **Don't** use a traveler color for status, price or category.

### Vote toggle

`.h-vote` is a 44 px pill with the voter's 24 px avatar and a heart. State is `aria-pressed`: pressed has a `--tp-brand` border, a brand-soft fill and a heart filled with the voter's color (`--t1` to `--t8`). React: `<VoteButton>`. **Do** name the person and the stay in the label ("Ana likes Casita with volcano view"). **Don't** add a down vote; hearts are the only vote.

### Pins, chips and the plane disc

Markers are HTML children of `.h-map`, placed with `left` and `top` in map coordinates, so they port to MapLibre markers. `.h-pin--num` is a 24 px ink disc with a 3.5 px ring in the activity color (`--outdoors`, `--food`, `--culture`, `--shopping`, `--neutral`). `.h-pin--stop` is a hollow ring for a connection, `.h-pin--start` the larger dot where a route begins, `.h-pin--price` and `--price-active` a 30 px price pin (the selected stay is ink). `.h-map__chip` is a 24 px label; `--code` sets airport codes in Fredoka. `.h-plane-disc` is a 28 px sky disc (26 px `--sm`, 48 px `--lg`) with a cream plane. React: `<MapPin>`, `<PlaneMarker>`. **Do** rotate the plane glyph along the route. **Don't** put a chip over a pin.

### Routes

`.h-route` strokes are SVG paths: round caps and a `0 11` dash make dots 5 px wide at an 11 px pitch (`--lg`: 5.5 px at 12; `--sm`: 4 px at 9). `--a` is pink and `--b` is yellow. Set `pathLength` to dots times 11 and the dots fit the path exactly. A twin route is two paths offset by 4.5 px either side of the centerline. React: `<RoutePath>`.

### Timeline

`.h-timeline` is an `ol` of rows on a 44, 30 and 1fr grid: time (`__time`, mono with AM or PM), a 22 px node (`__node`) ringed in the activity color, and a side-stub ticket. Between rows, `__spine` is the pink and yellow dotted pair (two repeating radial-gradients) and `__travel` is the drive time. A row is 56 px; a travel row is 26 px. React: `<DayTimeline>`. **Do** show who added an item in the stub ("Added by Ana") with their color. **Don't** draw the spine in SVG.

### Tiles and list cards

`.h-tile` is a quiet 16 px card link with a label, one mono value and one line of context (min height 68 px). Two per row (`.h-tiles`). `.h-listcard` is a card with a label and rows of check, one sentence and a chevron (44 px rows). React: `<SummaryTile>`, `<NextSteps>`. **Do** make the whole tile one link with a full label. **Don't** put a button inside a tile.

### Buttons

`.h-btn--primary` is the one 48 px brand pill per screen or sheet. `--secondary` is the 1.5 px `--tp-edge` outline pill, equal in size to the primary when it is the free path. `--text` is a quiet inline action, `--icon` a 44 px circle, `--sm` a 44 px compact pill, `--spend` a primary that carries its credit cost. React: `<Button>`. **Do** use plain verbs ("Plan a trip", "Mark as booked"). **Don't** add a second brand-filled button; a second action is secondary.

### Segmented control, section strip and day chips

`.h-seg` is a 44 px track with a 34 px selected pill (sheet fill, edge border). `.h-strip` is the six-tab section strip (see section 3). `.h-daychips` is a scrolling row of 46 by 44 px chips, the selected day in ink. All three use `role="tablist"` and `aria-selected`. React: `<SegmentedControl>`, `<SectionTabs>`, `<DayChips>`. **Don't** use a segmented control for more than four options.

### Tab bar and sheet

`.h-tabbar` is the floating pill (section 3); the active item is `--tp-brand-soft` with a brand icon at stroke 2.2. `.h-sheet` is the level 3 bottom sheet (section 3). React: `<TabBar>`, `<Sheet>`. **Do** keep Trips active inside a trip. **Don't** show the tab bar under a modal sheet.

### Chart

`.h-chart` is a 16 px card with a label, a legend that names the source, and a 52 px plot: a 2.5 px line, a hollow dot for a past point, a solid dot for now, a callout with a paper halo. Series color follows the source: `--live`, `--cached`, `--agent`, `--google`. React: `<PriceChart>`. **Do** pair it with a text summary ("Down $42 since Tuesday"). **Don't** color a series by how good the price is.

### Partner rows and the disclosure line

A booking row is a side-stub ticket (`.h-provider__name`, `__price`, `__amount`) with a secondary `.h-btn--stub` button and an external-link icon in the 168 px stub. Directly under the list sits `.h-disclosure`: "We earn a commission if you book here." (13 px soft, never truncated). React: `<ProviderRow>`, `<Disclosure>`. **Do** show the free route ("Search on the airline's site") at the same size, and say how the list is sorted ("Sorted by price, lowest first"). **Don't** sort by commission or brand-fill a partner button.

### Credit chip and AI entry

`.h-credit` is a 28 px chip with a coin, a mono number and the word "credit" or "credits" (`--lg` 32 px; `--warn` for a cost the person cannot cover). `.h-ai-entry` is a 48 px card row with the balance; `--pill` is the outlined 44 px button form. React: `<CreditChip>`, `<AiEntry>`. **Do** show the cost before the tap. **Don't** show dollars for AI.

### Photo placeholder

`.h-photo-ph` is a 64 px sunken tile with an image icon and "Listing photo". React: `<PhotoPlaceholder>`. **Do** use it until a real photo loads, at the same size. **Don't** use an illustration of people.

### Paywall, AI sheet and agent run

- **Paywall** (`.h-sheet--paywall`): a sky head with the two routes meeting at a plane, a 40 px headline, one line of what the person gets, then a tear. Offers are `.h-ticket--plan` radios (checked: 2 px brand outline, brand-soft body); `.h-more` names the next offer; one primary purchase button with the price in mono; `.h-btnpair` holds the free route and "Not now" at equal size; `.h-disclosure--legal` states price, term and how to cancel; `.h-linkrow` holds billing, terms, privacy and restore. The screen behind is `.h-dim` under `.h-scrim`. React: `<PaywallSheet>`, `<PlanOption>`.
- **AI sheet** (`.h-sheet--ai`): a title with the balance, one `.h-actionlist` of `.h-action` rows (title, one line, cost chip; one row selected with `aria-pressed`), and a `.h-confirm` stub pinned to the bottom that says the cost, the balance after, and has the spend button beside Cancel. A confirm is required at 6 credits or more. React: `<AiSheet>`, `<ConfirmStub>`.
- **Agent run** (`.h-ticket--run`): a sky head with what ran, elapsed, credits used and left; a route of steps (`.h-run`, checks and a landed plane); a stub that lands with touchdown; then `.h-ticket--evidence` findings and one primary "Add to plan". React: `<RunTicket>`, `<EvidenceTicket>`.

**Do** keep the free path at equal weight on every paywall. **Don't** show a paywall during an agent run.

## 5. Motifs

- **Round dots only, never dashes.** Routes, tears, the timeline spine and the run steps are dots.
- **Route colors follow traveler join order:** pink first, yellow second. Never swap them.
- **The plane points along its route.** On a horizontal route it points right.
- **Maps never sit under body text.** The map is decoration and carries nothing the page does not also say in text.
- **One sky accent area per surface.** The hero head, the paywall head or the agent run head, not two. The welcome screen and the map are the exceptions.

## 6. Motion

- **Touchdown** (`.h-touchdown`): a stub settles from 1.15 to 1 and fades in over 280 ms with `--ease-touchdown`, after the plane lands. Use it for a result the person earned (a run finished, a purchase made), not for decoration.
- **Route draw-on** (`.h-run__dot`): dots appear in order, 45 ms apart, then the plane glides in (1.2 s, `--ease-out`). At most 1.8 s in all. Play it when a trip map first opens, a new trip is made and a run finishes, once per session per surface.
- **Sheet slide:** 320 ms (`--motion-slow`) with `--ease-out`. A press is `translateY(1px)` over `--motion-fast` (120 ms).
- **Reduced motion:** `hermi.css` ends every animation at once and removes delays, so touchdown and draw-on show their final state. Sheets fade instead of sliding.

## 7. Dark mode

- **How it is set.** Put the `dark` class on the root element. With no class the system setting applies (`prefers-color-scheme: dark`), and a `light` class forces light. A demo can wrap any block in `<div class="dark">`. `tokens.css` holds all dark values, and the semantic aliases resolve per scope.
- **Maps darken.** Land steps up one surface (`--h-land` becomes `--tp-sunken`, the alternate land `--tp-sheet`), the coast halo turns `--tp-sky`, and the water thins from 20% to 12% sky. The plane ring turns ink.
- **The logo tile stays sky** (`#2AA5FF`); the wordmark turns light.
- **Dark shadows.** Level 2 is `0 4px 16px rgb(0 0 0 / 40%)`. Level 3 is a 1 px `--tp-sunken` top edge. The scrim is black at 60%.
- **Check** every screen in both modes. `screens/03-trip-overview.html#dark` and `screens/07-paywall.html#dark` show the pattern.

## 8. Accessibility

- **Targets are 44 px** or larger on touch. A 34 px visual gets a 44 px hit area (strip, seg and chip components do this).
- **Contrast** is measured in [05 section 2.3](../05-ui-ux-spec.md). A new color pair is checked with the same formula and added there.
- **Tabs.** The section strip, the segmented control and the day chips use `role="tablist"` with `aria-selected`; the current day also has `aria-current="date"`.
- **Votes** use `aria-pressed` and name the person and the stay.
- **Tickets are one link** with a full label that reads the facts in order ("Costa Rica, 25 November to 6 December 2026, flight booked, 2 travelers, departs in 53 days").
- **Body text is at least 13 px**, in `rem`, so Dynamic Type and browser zoom work.
- **Uppercase comes from CSS only.** The DOM keeps sentence case so a screen reader does not spell it out.
- **Decorative art is hidden:** routes, maps, icons and the dotted tears are `aria-hidden`; the map as a whole has one `role="img"` label.
- **Modal sheets** are `role="dialog" aria-modal="true"` with a labelled heading; the screen behind is `aria-hidden` and `inert`.
- **Focus** is a 3 px `--ring` outline, offset 2 px, never covered by the tab bar.

## 9. Voice in the UI

The full rules are in [05 section 7](../05-ui-ux-spec.md). The ones the design depends on:

- **Every price shows its source and its age** ("$612, Aviasales, checked 3 h ago"). A price never says "best" or "cheapest"; a list may say "Lowest in this list".
- **The commission line** "We earn a commission if you book here." appears under every partner action. It is not used where there is no partner.
- **Ranges use "to"** ("25 Nov to 6 Dec", "2 to 3 hours").
- **No em dashes or en dashes**, in copy or in the files of this kit.
- **Sentence case** for every heading, button, label and tab; plain verbs; one idea per line.
- **Say what it costs before the tap** ("Costs 8 credits. You have 12, so 4 left.").

## 10. Do and don't

| Do | Don't |
|---|---|
| One primary button per screen or sheet (`.h-btn--primary`, 48 px). | A second brand-filled button. The second action is `.h-btn--secondary`. |
| Put the free path next to the paid one at equal size (`.h-btnpair`). | Hide "Not now" in a gray X, a small link or a swipe. |
| Draw routes with round dots (`.h-route`). | Use dashes, solid lines or gradients on a route. |
| Keep pink first and yellow second, in join order. | Swap the routes, or use route colors for status or price. |
| Give each traveler color a name or initials. | Let a color alone say who did something. |
| Set codes in Fredoka with 0.06em tracking, uppercase by CSS. | Type codes in the body face, or uppercase them in the DOM. |
| Set prices, times and counts in mono, tabular. | Use mono for words. |
| Show a price with its source and age. | Write "best price", "deal" or "cheapest". |
| Use tokens (`var(--tp-ink)`, `var(--tp-brand)`). | Write a hex value or `rgb()` in a component. |
| Keep the map decorative and away from body text. | Put a paragraph on a map. |
| Use one sky area per surface. | Stack two sky bands on one screen. |
| Make the hairline on a ticket with the wrapper's drop-shadow chain. | Add a CSS border to the masked card (the mask clips it at the notches). |

## 11. New screen checklist

Run these before calling a screen done.

1. **Open the closest mockup** (HTML and PNG) and match its anatomy: header, sheet top, strip, content, tab bar.
2. **Decide map or no map** with the rule in section 3, and use `--h-sheet-top` for the sheet top.
3. **Trip facts are tickets.** Choose the variant from section 4; do not draw a plain card for a flight, a stay or a day.
4. **One primary button.** Everything else is secondary, text or icon.
5. **Tokens only.** Search the screen's CSS for `#` and `rgb(`. There should be none outside the logo mark.
6. **Both modes.** Check `.dark` and the system setting; check `.light` inside a dark context if the screen embeds a demo.
7. **44 px targets and visible focus** on every control; tab through the screen.
8. **Text is at least 13 px**, in `rem`; uppercase is CSS only; numbers are mono.
9. **Every price has a source and an age**, and a partner action has the commission line and a free route.
10. **Copy follows 05 section 7:** sentence case, plain verbs, "to" for ranges, no dashes.
11. **At 390 by 844 nothing is clipped** and the last item ends above 758 px; then try the largest text size.
12. **Reduced motion shows final states**, and the touchdown and draw-on do not run.

## 12. Known gaps

These are decisions the owner can revisit. The kit keeps the artboard values until then.

- **Tokens 05 leaves undefined.** `--heat-ink-1` to `--heat-ink-5` (text on each date-grid step) and `--viz-band` (the typical-price band on the chart) have no values in 05 section 2.2, so `tokens.css` does not define them either. Define them in 05 first.
- **Airport code sizes (a note, not a gap).** 05 section 2.4 allows 24 to 48 px for `type-code`, with 36 to 48 px on tickets and passes. `--tp-type-code` in `tokens.css` stays 32 px as the default, and tickets use `.h-codes` at 36, 40 or 44 px.
- **The wordmark is live text in the mockups.** The welcome pass sets "Hermi" in Fredoka 600 at 42 px (`.h-lockup__name`) for convenience. Production must use the wordmark file (`hermi-wordmark.svg`), per 05 section 3 rule 4.
- **Display line height is 1.05.** The welcome and paywall headlines use 1.05; 05 section 2.4 says 1.0 for `type-display`.
- **No tablet or web layouts are mocked.** The 05 breakpoints also conflict: section 5.3 puts the full 248 px sidebar at 1200 px and up, while section 10 starts the laptop layout at 1024 px. Settle one before building the web shell.
- **Android uses the same layout.** Phase 1 ships Android as a PWA, so there is no separate Android design.
- **The map is an illustration.** `.h-map` is a placeholder for MapLibre tiles styled with these tokens (land, water, coast halo, relief). The markers are HTML and carry over; the shapes do not.
- **Fixed ticket stubs.** Stub heights are fixed (for example 40 and 50 px) so the notches line up. At large Dynamic Type sizes a build needs a taller stub or the side-stub form; 05 section 9.3 says layouts reflow rather than clip.
- **Mono weight 700.** The Google Fonts link in the mockups loads Atkinson Mono at 400 to 600, so bold mono (the fare, price blocks) is synthesized there. The app bundles the variable font and has a true 700.
- **`:has()` in plan options.** The checked state of `.h-ticket--plan` uses `:has()`, which iOS 15.4 and later support. Use a state class if the shell must support older systems.
- **Not mocked yet:** the sync indicator, Increase Contrast, the paywall without prices on web, and loading, empty and error states.
