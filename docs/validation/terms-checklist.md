# Provider terms checklist

These are things to verify, not legal conclusions. The owner reads the current official page, records the date and the answer, and sets the status. Where no URL is given, find the page by name on the provider site.

| # | Provider | What to verify | Where | Answer, date, link | Status |
|---|---|---|---|---|---|
| 1 | SerpApi | Terms allow a paid app to show Google Flights and Google Vacation Rentals results to end users, store them (for how long), and share cached results between users | serpapi.com, Terms of Service and Legal pages | | Open |
| 2 | SerpApi | Status of Google's lawsuit against SerpApi: current stage, any ruling, and whether SerpApi still offers the engines Hermi uses. Read SerpApi's own statement and a primary court or press source | SerpApi blog and legal statement; court docket | | Open |
| 3 | SerpApi | Whether any legal protection or indemnity SerpApi offers applies to our use and plan | SerpApi pricing and legal pages | | Open |
| 4 | SerpApi | Plan limits, overage and monthly cost against our credit model (1 credit is up to $0.02 of provider spend) | SerpApi pricing page | | Open |
| 5 | Geoapify | Terms allow caching and storing place and geocoding results (we keep `places_cache`), and for how long | geoapify.com, Terms and Conditions and the Places API docs | | Open |
| 6 | Geoapify | Exact required attribution wording (for example "Powered by Geoapify" and "(c) OpenStreetMap contributors") and where it must appear | Geoapify docs, attribution section; OpenStreetMap copyright page | | Open |
| 7 | Geoapify | Free tier limits versus launch volume, and the plan that permits storing results | Geoapify pricing page | | Open |
| 8 | Travelpayouts | Commission rates for flights and each program we use, and the payout threshold | Travelpayouts dashboard, Programs list | | Open |
| 9 | Travelpayouts | Whether a mobile app is eligible: program rules on app traffic, links opened from an app, and any banned traffic types | Travelpayouts program pages and terms; ask support if unclear | | Open |
| 10 | Travelpayouts | Data API terms: caching cached fares, how long they may be shown, required disclosure | Travelpayouts Data API docs and terms | | Open |
| 11 | Travelpayouts | Sub-id and postback support for matching conversions to our click ids | Travelpayouts docs, sub id and postback pages | | Open |

## Fixed rules (not open to interpretation)
- Never fetch or scrape Airbnb, Vrbo or Booking.com pages. Pasted links are stored as links only.
- Never rank results or suggestions by commission. Affiliate links are disclosed.
- Every fare shown carries its source URL, and a fare not seen on a page during the run is never shown as live.

## Fallbacks
- Rows 1 to 3 block live fares: keep `serpapi` behind its flag and ship the cached Travelpayouts baseline (09 risk 4, WF-052).
- Row 5 or 7 blocks caching: shorten the TTL to the permitted limit or move plan.
- Row 9 blocks app use: ship flight links without affiliate tracking until cleared.

Reviewed by: ________  Date: ________
