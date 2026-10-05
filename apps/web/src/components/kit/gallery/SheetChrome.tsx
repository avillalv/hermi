/* The hero and link lists above the blocks on design/components.html. */
export function SheetChrome() {
  return (
    <>
      <header className="doc-hero">
        <div className="doc-hero__in">
          <div className="doc-hero__brand">
            <svg className="h-mark" width="56" height="56" aria-hidden="true" focusable="false">
              <use href="#hermi-mark" />
            </svg>
            <h1 className="doc-hero__title">Hermi design kit</h1>
          </div>
          <p className="doc-hero__lead">
            {"Tokens, component classes and nine reference screens for the app: React 19, Tailwind 4 and shadcn in a Capacitor iOS shell. Open "}
            <code>tokens.css</code>
            {" and "}
            <code>hermi.css</code>
            {" first, then copy the markup you see here."}
          </p>
        </div>
      </header>
      <ul className="doc-links" aria-label="Sections">
        <li>
          <a href="#tokens">Colors</a>
        </li>
        <li>
          <a href="#type">Type</a>
        </li>
        <li>
          <a href="#spacing">Spacing</a>
        </li>
        <li>
          <a href="#radii">Radii</a>
        </li>
        <li>
          <a href="#elevation">Elevation and motion</a>
        </li>
        <li>
          <a href="#screen">Screen</a>
        </li>
        <li>
          <a href="#map">Map</a>
        </li>
        <li>
          <a href="#markers">Markers</a>
        </li>
        <li>
          <a href="#routes">Routes</a>
        </li>
        <li>
          <a href="#sheet">Sheet</a>
        </li>
        <li>
          <a href="#navbtn">Nav buttons</a>
        </li>
        <li>
          <a href="#tabbar">Tab bar</a>
        </li>
        <li>
          <a href="#strip">Section strip</a>
        </li>
        <li>
          <a href="#seg">Segmented</a>
        </li>
        <li>
          <a href="#daychip">Day chips</a>
        </li>
        <li>
          <a href="#ticket">Ticket</a>
        </li>
        <li>
          <a href="#ticket-side">Side ticket</a>
        </li>
        <li>
          <a href="#stub">Status tag</a>
        </li>
        <li>
          <a href="#field">Field</a>
        </li>
        <li>
          <a href="#codes">Codes</a>
        </li>
        <li>
          <a href="#avatar">Avatar</a>
        </li>
        <li>
          <a href="#vote">Heart toggle</a>
        </li>
        <li>
          <a href="#tile">Tile</a>
        </li>
        <li>
          <a href="#listcard">List card</a>
        </li>
        <li>
          <a href="#ai">AI entry</a>
        </li>
        <li>
          <a href="#btn">Buttons</a>
        </li>
        <li>
          <a href="#chart">Chart</a>
        </li>
        <li>
          <a href="#timeline">Timeline</a>
        </li>
        <li>
          <a href="#small">Small blocks</a>
        </li>
        <li>
          <a href="#extras">Page head</a>
        </li>
        <li>
          <a href="#stay">Lodging ticket</a>
        </li>
        <li>
          <a href="#scrim">Scrim</a>
        </li>
        <li>
          <a href="#paywall">Paywall</a>
        </li>
        <li>
          <a href="#paywall-actions">Paywall actions</a>
        </li>
        <li>
          <a href="#ai-sheet">AI actions</a>
        </li>
        <li>
          <a href="#confirm">Confirm</a>
        </li>
        <li>
          <a href="#run">Run ticket</a>
        </li>
        <li>
          <a href="#evidence">Evidence</a>
        </li>
      </ul>
      <ul className="doc-links" aria-label="Reference screens">
        <li>
          <a href="screens/01-welcome.html">01 Welcome</a>
        </li>
        <li>
          <a href="screens/02-trips-home.html">02 Trips home</a>
        </li>
        <li>
          <a href="screens/03-trip-overview.html">03 Trip overview</a>
        </li>
        <li>
          <a href="screens/03-trip-overview.html#dark">03 Trip overview, dark</a>
        </li>
        <li>
          <a href="screens/04-plan-day.html">04 Plan day</a>
        </li>
        <li>
          <a href="screens/05-fare-detail.html">05 Fare detail</a>
        </li>
        <li>
          <a href="screens/06-stays-vote.html">06 Stays and vote</a>
        </li>
        <li>
          <a href="screens/07-paywall.html">07 Paywall</a>
        </li>
        <li>
          <a href="screens/07-paywall.html#dark">07 Paywall, dark</a>
        </li>
        <li>
          <a href="screens/08-ai-actions.html">08 AI actions</a>
        </li>
        <li>
          <a href="screens/09-agent-run.html">09 Agent run</a>
        </li>
      </ul>
    </>
  )
}
