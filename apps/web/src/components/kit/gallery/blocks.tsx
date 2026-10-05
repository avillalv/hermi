/* eslint-disable jsx-a11y/anchor-is-valid -- demo links copy the kit markup (href="#") */
/* The 05 section 4 component blocks of design/components.html, rendered with the React kit components.
 * Same ids, wrappers and h- classes as the kit file, so the kit tests (e2e/kit) compare it with the kit page.
 * Generated once from components.html; edit it by hand from here. Dev and test only: not in the production build. */
import { Avatar, Avatars, Btn, DayChip, DayChips, Field, Icon, LinkBtn, SectionTabs, SegmentedControl, SegItem, Sheet, SheetBody, SheetGrabber, StatusStub, TabBar, TextField, TicketStub, TripTicket } from '..'

function Block_screen_Demo() {
  return (
    <>
      <div className="h-screen doc-frame doc-frame--tall">
      <div className="h-map" role="img" aria-label="Map of your trips. Dotted routes run from Raleigh-Durham, RDU, to San José, SJO, for Costa Rica, and to Lisbon, LIS.">
        <svg className="h-map__svg" viewBox="0 0 390 194" aria-hidden="true" focusable="false">
          <rect className="h-map__water" width="390" height="194" />
          <path className="h-map__halo" d="M-103.4 6C-64.1 -6 119.1 1.7 158.4 6C197.7 10.3 159.9 29 158.4 35C156.9 41 152.3 43.8 148.2 46C144.1 48.2 135.8 49.1 131.2 50C126.6 50.9 119.7 51 117.6 52C115.5 53 119.3 55.3 117.3 56.5C115.2 57.7 107 58 104 59.8C101 61.5 98.3 66 97.5 68C96.8 70 99.7 71.8 98.9 73C98.1 74.2 94.1 75.2 92.1 76C90.1 76.8 87.1 77.7 85.3 78.5C83.5 79.3 81.2 80.4 80.2 81.5C79.2 82.6 78.6 84.7 78.8 86C79 87.3 80.9 88.5 81.6 90C82.2 91.5 83.2 94.8 83.3 96C83.4 97.2 82.7 97.7 82.2 98C81.7 98.3 80.6 98.4 79.9 98C79.1 97.6 78.3 96.5 77.5 95.5C76.7 94.5 74.9 92.7 74.4 91.5C73.9 90.3 74.9 88.1 74.1 87.2C73.3 86.4 70.4 86.1 69 86C67.6 85.9 66.5 86.9 64.9 86.8C63.3 86.6 60.1 85.4 58.1 85.2C56.1 85.1 52.5 85.3 51.6 85.8C50.8 86.2 52.9 88.1 52.3 88.5C51.8 88.9 49.3 88.5 47.9 88.2C46.5 88 44.6 87.2 42.8 87C41 86.8 37.8 86.7 36 87C34.2 87.3 32.5 88.1 30.9 89C29.3 89.9 26.2 91.4 25.1 93C24 94.6 23.7 97.8 23.4 99.8C23.2 101.7 22.8 104.1 23.4 106C24.1 107.9 26.5 110.9 27.8 112.2C29.2 113.6 31.1 114.3 32.6 114.8C34.1 115.2 35.9 115 37.7 115C39.5 115 43 115.2 44.5 114.5C46 113.8 47.1 111.4 47.9 110.5C48.7 109.6 48.5 109 49.6 108.5C50.7 108 53.7 107.4 55.4 107.2C57 107.1 60 106.8 60.5 107.5C60.9 108.2 59.1 111 58.4 112.2C57.8 113.5 57 114.9 56.4 116C55.8 117.1 54.2 118.7 54.7 119.5C55.2 120.3 58 121.2 59.8 121.5C61.6 121.8 64.8 121 66.6 121.2C68.4 121.5 71.3 122 72 123.2C72.8 124.5 71.5 128.2 71.4 129.8C71.2 131.3 70.7 132.5 71 133.5C71.3 134.5 72.3 135.5 73.4 136.2C74.5 137 76.7 138.1 78.5 138.2C80.3 138.4 83.4 137.2 85.3 137.2C87.2 137.2 89.7 137.8 91.1 138.2C92.5 138.7 93.4 140.6 94.5 140.2C95.6 139.9 97 137 98.2 136C99.4 135 100.7 134.2 102.3 133.5C103.9 132.8 107.4 132 109.1 131.5C110.8 131 112.2 129.9 113.5 130C114.8 130.1 116.2 131.6 117.6 132.2C119 132.9 120.7 133.9 122.7 134.2C124.7 134.6 128.9 134.5 131.2 134.5C133.5 134.5 136 134.5 138 134.5C140 134.5 143.3 133.8 144.8 134.5C146.3 135.2 146.4 138.1 148.2 139.5C150 140.9 153.6 143 156.7 144C159.8 145 165.3 145.6 168.6 146.2C171.9 146.9 176.2 147 178.8 148.5C181.4 150 189.7 151.1 185.6 156C181.5 160.9 167.9 177.2 151.6 181C135.3 184.8 87.3 184 76.8 181C66.3 178 80.1 164.8 81.9 161C83.7 157.2 87.1 157.5 88.7 156C90.3 154.5 91.8 152.7 92.4 151C93.1 149.3 93.3 146.5 92.8 145C92.3 143.5 90.4 141.1 89 140.8C87.7 140.4 85 142.3 83.6 142.5C82.2 142.7 80.8 142.1 79.5 141.8C78.2 141.4 76.2 140.8 75.1 140.5C74 140.2 73.5 140.6 72 140C70.6 139.4 66.8 137.7 65.6 136.8C64.4 135.8 65 134.9 63.9 133.8C62.8 132.6 60.3 129.9 58.4 129C56.6 128.1 53.6 128.1 51.3 127.5C49 126.9 45.3 125.8 42.8 124.8C40.2 123.7 36.9 121 34.3 120.5C31.8 120 28.6 121.8 25.8 121.5C23 121.2 21.2 120.8 15.6 118.5C10 116.2 6.3 110.9 -11.6 106C-29.4 101.1 -89.6 101 -103.4 86C-117.2 71 -142.7 18 -103.4 6Z" />
          <path className="h-map__land" d="M-103.4 6C-64.1 -6 119.1 1.7 158.4 6C197.7 10.3 159.9 29 158.4 35C156.9 41 152.3 43.8 148.2 46C144.1 48.2 135.8 49.1 131.2 50C126.6 50.9 119.7 51 117.6 52C115.5 53 119.3 55.3 117.3 56.5C115.2 57.7 107 58 104 59.8C101 61.5 98.3 66 97.5 68C96.8 70 99.7 71.8 98.9 73C98.1 74.2 94.1 75.2 92.1 76C90.1 76.8 87.1 77.7 85.3 78.5C83.5 79.3 81.2 80.4 80.2 81.5C79.2 82.6 78.6 84.7 78.8 86C79 87.3 80.9 88.5 81.6 90C82.2 91.5 83.2 94.8 83.3 96C83.4 97.2 82.7 97.7 82.2 98C81.7 98.3 80.6 98.4 79.9 98C79.1 97.6 78.3 96.5 77.5 95.5C76.7 94.5 74.9 92.7 74.4 91.5C73.9 90.3 74.9 88.1 74.1 87.2C73.3 86.4 70.4 86.1 69 86C67.6 85.9 66.5 86.9 64.9 86.8C63.3 86.6 60.1 85.4 58.1 85.2C56.1 85.1 52.5 85.3 51.6 85.8C50.8 86.2 52.9 88.1 52.3 88.5C51.8 88.9 49.3 88.5 47.9 88.2C46.5 88 44.6 87.2 42.8 87C41 86.8 37.8 86.7 36 87C34.2 87.3 32.5 88.1 30.9 89C29.3 89.9 26.2 91.4 25.1 93C24 94.6 23.7 97.8 23.4 99.8C23.2 101.7 22.8 104.1 23.4 106C24.1 107.9 26.5 110.9 27.8 112.2C29.2 113.6 31.1 114.3 32.6 114.8C34.1 115.2 35.9 115 37.7 115C39.5 115 43 115.2 44.5 114.5C46 113.8 47.1 111.4 47.9 110.5C48.7 109.6 48.5 109 49.6 108.5C50.7 108 53.7 107.4 55.4 107.2C57 107.1 60 106.8 60.5 107.5C60.9 108.2 59.1 111 58.4 112.2C57.8 113.5 57 114.9 56.4 116C55.8 117.1 54.2 118.7 54.7 119.5C55.2 120.3 58 121.2 59.8 121.5C61.6 121.8 64.8 121 66.6 121.2C68.4 121.5 71.3 122 72 123.2C72.8 124.5 71.5 128.2 71.4 129.8C71.2 131.3 70.7 132.5 71 133.5C71.3 134.5 72.3 135.5 73.4 136.2C74.5 137 76.7 138.1 78.5 138.2C80.3 138.4 83.4 137.2 85.3 137.2C87.2 137.2 89.7 137.8 91.1 138.2C92.5 138.7 93.4 140.6 94.5 140.2C95.6 139.9 97 137 98.2 136C99.4 135 100.7 134.2 102.3 133.5C103.9 132.8 107.4 132 109.1 131.5C110.8 131 112.2 129.9 113.5 130C114.8 130.1 116.2 131.6 117.6 132.2C119 132.9 120.7 133.9 122.7 134.2C124.7 134.6 128.9 134.5 131.2 134.5C133.5 134.5 136 134.5 138 134.5C140 134.5 143.3 133.8 144.8 134.5C146.3 135.2 146.4 138.1 148.2 139.5C150 140.9 153.6 143 156.7 144C159.8 145 165.3 145.6 168.6 146.2C171.9 146.9 176.2 147 178.8 148.5C181.4 150 189.7 151.1 185.6 156C181.5 160.9 167.9 177.2 151.6 181C135.3 184.8 87.3 184 76.8 181C66.3 178 80.1 164.8 81.9 161C83.7 157.2 87.1 157.5 88.7 156C90.3 154.5 91.8 152.7 92.4 151C93.1 149.3 93.3 146.5 92.8 145C92.3 143.5 90.4 141.1 89 140.8C87.7 140.4 85 142.3 83.6 142.5C82.2 142.7 80.8 142.1 79.5 141.8C78.2 141.4 76.2 140.8 75.1 140.5C74 140.2 73.5 140.6 72 140C70.6 139.4 66.8 137.7 65.6 136.8C64.4 135.8 65 134.9 63.9 133.8C62.8 132.6 60.3 129.9 58.4 129C56.6 128.1 53.6 128.1 51.3 127.5C49 126.9 45.3 125.8 42.8 124.8C40.2 123.7 36.9 121 34.3 120.5C31.8 120 28.6 121.8 25.8 121.5C23 121.2 21.2 120.8 15.6 118.5C10 116.2 6.3 110.9 -11.6 106C-29.4 101.1 -89.6 101 -103.4 86C-117.2 71 -142.7 18 -103.4 6Z" />
          <path className="h-map__halo" d="M335.2 6C348.5 2.6 410.3 -15.8 423.6 6C436.9 27.8 440.4 129.2 423.6 151C406.8 172.8 329.8 154 311.4 151C293 148 303.4 135 301.2 131C299 127 296.7 125.8 296.4 124.2C296.2 122.8 298.9 122.6 299.5 121C300.1 119.4 300.8 115.4 300.5 113.5C300.3 111.6 297.7 110.4 297.8 108.5C297.9 106.6 299.9 103.1 301.2 101C302.5 98.9 304.5 96.2 306.3 94.8C308.1 93.2 311.1 91.9 313.1 91C315.1 90.1 318.2 89.4 319.6 88.5C320.9 87.6 321.7 86.2 322.3 85.2C322.9 84.3 323 83.4 323.6 82.2C324.3 81.1 325.4 78.7 326.7 77.8C328 76.8 330.9 76.7 332.1 75.8C333.4 74.8 334.5 72.5 335.2 71.8C335.9 71 337.1 71.4 336.9 71C336.7 70.6 335.2 69.7 334.2 69.2C333.2 68.8 331.5 68.1 330.1 68C328.7 67.9 325.8 68.6 325.2 68.5C324.5 68.4 325.7 67.8 325.7 67.2C325.7 66.7 325.4 65.2 325 64.8C324.6 64.3 323.5 64.4 323.3 64.1C323.1 63.9 323.2 63.7 323.6 63C324 62.3 325.8 60.7 326 59.8C326.3 58.8 325.6 57.4 325.3 56.5C325 55.6 323.5 54.2 324 53.5C324.4 52.8 325.4 51.9 328.4 51.8C331.4 51.6 340.4 52.1 343.7 52.2C347 52.4 349.3 53.2 350.5 52.5C351.7 51.8 352 48.7 351.5 47.2C351 45.8 348.9 43.8 347.1 42.8C345.3 41.7 340.3 40.8 339.3 40C338.3 39.2 340.9 39 340.3 37.2C339.7 35.5 336 33.2 335.2 28.5C334.4 23.8 321.9 9.4 335.2 6Z" />
          <path className="h-map__land" d="M335.2 6C348.5 2.6 410.3 -15.8 423.6 6C436.9 27.8 440.4 129.2 423.6 151C406.8 172.8 329.8 154 311.4 151C293 148 303.4 135 301.2 131C299 127 296.7 125.8 296.4 124.2C296.2 122.8 298.9 122.6 299.5 121C300.1 119.4 300.8 115.4 300.5 113.5C300.3 111.6 297.7 110.4 297.8 108.5C297.9 106.6 299.9 103.1 301.2 101C302.5 98.9 304.5 96.2 306.3 94.8C308.1 93.2 311.1 91.9 313.1 91C315.1 90.1 318.2 89.4 319.6 88.5C320.9 87.6 321.7 86.2 322.3 85.2C322.9 84.3 323 83.4 323.6 82.2C324.3 81.1 325.4 78.7 326.7 77.8C328 76.8 330.9 76.7 332.1 75.8C333.4 74.8 334.5 72.5 335.2 71.8C335.9 71 337.1 71.4 336.9 71C336.7 70.6 335.2 69.7 334.2 69.2C333.2 68.8 331.5 68.1 330.1 68C328.7 67.9 325.8 68.6 325.2 68.5C324.5 68.4 325.7 67.8 325.7 67.2C325.7 66.7 325.4 65.2 325 64.8C324.6 64.3 323.5 64.4 323.3 64.1C323.1 63.9 323.2 63.7 323.6 63C324 62.3 325.8 60.7 326 59.8C326.3 58.8 325.6 57.4 325.3 56.5C325 55.6 323.5 54.2 324 53.5C324.4 52.8 325.4 51.9 328.4 51.8C331.4 51.6 340.4 52.1 343.7 52.2C347 52.4 349.3 53.2 350.5 52.5C351.7 51.8 352 48.7 351.5 47.2C351 45.8 348.9 43.8 347.1 42.8C345.3 41.7 340.3 40.8 339.3 40C338.3 39.2 340.9 39 340.3 37.2C339.7 35.5 336 33.2 335.2 28.5C334.4 23.8 321.9 9.4 335.2 6Z" />
          <path className="h-map__land h-map__land--islet" d="M66.9 106.2C66.9 105.9 74.1 103.2 76.8 103C79.5 102.8 84.7 103.9 87 104.8C89.3 105.6 91.6 108.5 93.8 109.2C96 110 103.5 110.2 103.3 110.5C103.1 110.8 94.5 111.7 92.1 111.2C89.7 110.8 87.3 107.8 85.3 107C83.3 106.2 79.2 105.6 76.8 105.5C74.4 105.4 66.9 106.6 66.9 106.2Z" />
          <path className="h-map__land h-map__land--islet" d="M102.6 115C102.9 114.4 107.1 111.7 109.1 111.2C111.1 110.8 115.7 111 117.6 111.5C119.5 112 123.5 114.1 123 114.8C122.6 115.4 116.3 116.4 114.2 116.5C112.1 116.6 108.9 115.7 107.4 115.5C105.9 115.3 102.4 115.6 102.6 115Z" />
          <path className="h-map__land h-map__land--islet" d="M89.4 115C90.2 114.9 95.6 115.3 96.2 115.5C96.8 115.7 94.6 116.4 93.8 116.5C93 116.6 91 116.2 90.4 116C89.8 115.8 88.6 115.1 89.4 115Z" />
          <path className="h-map__land h-map__land--islet" d="M259.7 64.5C260.2 64.6 263.7 64.2 263.8 64C263.9 63.8 260.9 63.2 260.4 63.2C259.9 63.3 259.3 64.4 259.7 64.5Z" />
          <path className="h-map__land h-map__land--islet" d="M297.1 79.2C297.2 79.2 298.7 79 298.8 79C299 79 298.4 79.5 298.1 79.5C297.9 79.5 297 79.3 297.1 79.2Z" />
          <path className="h-route h-route--a" d="M95.9 69.7C97.3 71.7 101.8 77.8 104.1 81.5C106.4 85.3 108.9 88.3 109.8 92.5C110.7 96.7 110.5 102.7 109.4 106.7C108.4 110.8 106.2 113.7 103.4 116.8C100.6 120 96.5 122.9 92.5 125.6C88.6 128.3 83.2 130.9 79.5 133C75.8 135 71.8 137 70.3 137.9" pathLength="88" />
          <path className="h-route h-route--b" d="M88.1 74.3C89.5 76.3 94.3 82.7 96.6 86.5C98.8 90.2 101.3 92.8 101.5 96.6C101.8 100.4 100.4 105.5 98.1 109.1C95.8 112.7 91.6 115.3 87.8 118C84 120.6 79 123 75.3 125C71.6 127 67.3 129.3 65.7 130.1" pathLength="77" />
          <path className="h-route h-route--a" d="M91.2 67.6C95.8 66.6 110 63.6 118.6 62C127.3 60.5 134.5 59.3 143.1 58.2C151.6 57.2 161.2 56.5 170 55.8C178.8 55.1 187 54.6 195.7 54.3C204.4 53.9 213.4 53.5 222.2 53.4C231 53.4 239.5 53.4 248.3 53.8C257 54.2 265.5 54.9 274.5 55.8C283.6 56.6 294 57.9 302.7 58.8C311.3 59.8 322.5 61.1 326.4 61.5" pathLength="242" />
          <path className="h-route h-route--b" d="M92.8 76.4C97.4 75.5 111.7 72.4 120.3 70.9C128.9 69.3 135.7 68.2 144.1 67.2C152.5 66.1 162 65.4 170.7 64.8C179.3 64.1 187.5 63.6 196.1 63.2C204.7 62.8 213.2 62.5 222.3 62.4C231.4 62.4 241.5 62.5 250.6 62.9C259.6 63.4 268.1 64.2 276.6 65C285.1 65.8 293.5 66.8 301.6 67.8C309.8 68.7 321.6 70 325.6 70.5" pathLength="231" />
        </svg>
        <span className="h-plane-disc h-plane-disc--sm" style={{ left: "101.9px", top: "111.5px" }}>
          <svg viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
            <use href="#h-plane-path" transform="rotate(-148.9) translate(-50 -50)" />
          </svg>
        </span>
        <span className="h-pin h-pin--stop" style={{ left: "92px", top: "72px" }} />
        <span className="h-map__chip h-map__chip--code h-map__chip--end" style={{ left: "76px", top: "72px" }}>RDU</span>
        <span className="h-pin h-pin--num" style={{ left: "68px", top: "134px" }}>1</span>
        <span className="h-map__chip h-map__chip--code h-map__chip--start" style={{ left: "90px", top: "136px" }}>SJO</span>
        <span className="h-pin h-pin--num" style={{ left: "326px", top: "66px" }}>2</span>
        <span className="h-map__chip h-map__chip--code" style={{ left: "326px", top: "100px" }}>LIS</span>
      </div>
      <a className="h-navbtn h-navbtn--back" href="#" aria-label="Back">
        <Icon name="chevron-left" />
      </a>
      <button className="h-navbtn h-navbtn--menu" type="button" aria-haspopup="menu" aria-label="Menu">
        <Icon name="ellipsis" />
      </button>
      <Sheet>
        <SheetGrabber />
        <SheetBody>
          <p className="h-lead">Sheet content starts here.</p>
        </SheetBody>
      </Sheet>
    </div>
    </>
  )
}

export function Block_screen() {
  return (
    <section className="doc-block" id="screen">
      <h3 className="doc-h3">Screen frame</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-screen</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>Mockups only. The app never renders it.</dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Use it to compose a 390 by 844 artboard. The demo is cropped; the real frame is 844 pt tall.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_screen_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_screen_Demo />
        </div>
      </div>
    </section>
  )
}

export function Block_map() {
  return (
    <section className="doc-block" id="map">
      <h3 className="doc-h3">Map surface</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-map</code>
            {' '}
            <code>__svg</code>
            {' '}
            <code>__water</code>
            {' '}
            <code>__halo</code>
            {' '}
            <code>__land</code>
            {' '}
            <code>__land--alt</code>
            {' '}
            <code>__land--islet</code>
            {' '}
            <code>__land--bare</code>
            {' '}
            <code>__ground</code>
            {' '}
            <code>__coast</code>
            {' '}
            <code>__relief</code>
            {' '}
            <code>__relief--fill</code>
            {' '}
            <code>__hill</code>
            {' '}
            <code>__lake</code>
            {' '}
            <code>__river</code>
            {' '}
            <code>__peak</code>
            {' '}
            <code>__chip</code>
            {' '}
            <code>__badge</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.21 Map, becomes "}
            <code>{"<TripMap>"}</code>
            {" (MapLibre in the app)."}
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Illustrated stand-in for the trip map. Land steps one surface up in dark and the coast halo turns sky, as in e-07. Markers are HTML children placed with left and top in map coordinates.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <div className="h-screen doc-frame doc-frame--map">
            <div className="h-map" role="img" aria-label="Map of the Costa Rica route. Dotted routes join the flight stop in Panama City, then San José, La Fortuna and Manuel Antonio.">
              <svg className="h-map__svg" viewBox="0 0 390 194" aria-hidden="true" focusable="false">
                <defs>
                  <clipPath id="cr-band-l">
                    <path d="M-20 48C-10 34.7 20 46.3 40 46C60 45.7 81.7 45.3 100 46C118.3 46.7 133.3 48.3 150 50C166.7 51.7 183.3 53.7 200 56C216.7 58.3 233.3 60.3 250 64C266.7 67.7 283.3 73 300 78C316.7 83 331.7 89.3 350 94C368.3 98.7 400 92.3 410 106C420 119.7 421.7 165.3 410 176C398.3 186.7 360 170 340 170C320 170 306.7 174.3 290 176C273.3 177.7 256.7 180.3 240 180C223.3 179.7 206.7 176.7 190 174C173.3 171.3 155 167.7 140 164C125 160.3 113.3 156.3 100 152C86.7 147.7 73.3 142 60 138C46.7 134 33.3 130 20 128C6.7 126 -13.3 139.3 -20 126C-26.7 112.7 -30 61.3 -20 48Z" />
                  </clipPath>
                </defs>
                <rect className="h-map__water" width="390" height="194" />
                <path className="h-map__halo" d="M-20 48C-10 34.7 20 46.3 40 46C60 45.7 81.7 45.3 100 46C118.3 46.7 133.3 48.3 150 50C166.7 51.7 183.3 53.7 200 56C216.7 58.3 233.3 60.3 250 64C266.7 67.7 283.3 73 300 78C316.7 83 331.7 89.3 350 94C368.3 98.7 400 92.3 410 106C420 119.7 421.7 165.3 410 176C398.3 186.7 360 170 340 170C320 170 306.7 174.3 290 176C273.3 177.7 256.7 180.3 240 180C223.3 179.7 206.7 176.7 190 174C173.3 171.3 155 167.7 140 164C125 160.3 113.3 156.3 100 152C86.7 147.7 73.3 142 60 138C46.7 134 33.3 130 20 128C6.7 126 -13.3 139.3 -20 126C-26.7 112.7 -30 61.3 -20 48Z" />
                <path className="h-map__land h-map__land--bare" d="M-20 48C-10 34.7 20 46.3 40 46C60 45.7 81.7 45.3 100 46C118.3 46.7 133.3 48.3 150 50C166.7 51.7 183.3 53.7 200 56C216.7 58.3 233.3 60.3 250 64C266.7 67.7 283.3 73 300 78C316.7 83 331.7 89.3 350 94C368.3 98.7 400 92.3 410 106C420 119.7 421.7 165.3 410 176C398.3 186.7 360 170 340 170C320 170 306.7 174.3 290 176C273.3 177.7 256.7 180.3 240 180C223.3 179.7 206.7 176.7 190 174C173.3 171.3 155 167.7 140 164C125 160.3 113.3 156.3 100 152C86.7 147.7 73.3 142 60 138C46.7 134 33.3 130 20 128C6.7 126 -13.3 139.3 -20 126C-26.7 112.7 -30 61.3 -20 48Z" />
                <g clipPath="url(#cr-band-l)">
                  <path className="h-map__land h-map__land--alt" d="M-40 0L58 0L56 96L64 190L-40 190Z" />
                  <path className="h-map__land h-map__land--alt" d="M334 96L430 96L430 300L342 300Z" />
                  <path className="h-map__hill" d="M150 112C159.3 107 179.3 103.7 196 104C212.7 104.3 239 108 250 114C261 120 266.7 132.3 262 140C257.3 147.7 237.3 158 222 160C206.7 162 183.7 156.3 170 152C156.3 147.7 143.3 140.7 140 134C136.7 127.3 140.7 117 150 112Z" />
                </g>
                <path className="h-map__coast" d="M-20 48C-10 34.7 20 46.3 40 46C60 45.7 81.7 45.3 100 46C118.3 46.7 133.3 48.3 150 50C166.7 51.7 183.3 53.7 200 56C216.7 58.3 233.3 60.3 250 64C266.7 67.7 283.3 73 300 78C316.7 83 331.7 89.3 350 94C368.3 98.7 400 92.3 410 106C420 119.7 421.7 165.3 410 176C398.3 186.7 360 170 340 170C320 170 306.7 174.3 290 176C273.3 177.7 256.7 180.3 240 180C223.3 179.7 206.7 176.7 190 174C173.3 171.3 155 167.7 140 164C125 160.3 113.3 156.3 100 152C86.7 147.7 73.3 142 60 138C46.7 134 33.3 130 20 128C6.7 126 -13.3 139.3 -20 126C-26.7 112.7 -30 61.3 -20 48Z" />
                <path className="h-route h-route--a" d="M403.6 142.5C398.9 142.1 384.3 141.3 375.4 140.4C366.5 139.6 358.5 138.6 350.1 137.4C341.7 136.1 333 134.4 324.9 132.9C316.8 131.4 305.2 129.2 301.2 128.4" pathLength="99" />
                <path className="h-route h-route--b" d="M404.4 133.5C399.7 133.2 385 132.3 376.2 131.4C367.4 130.6 359.8 129.7 351.5 128.5C343.2 127.2 334.7 125.6 326.6 124.1C318.4 122.6 306.8 120.3 302.8 119.6" pathLength="99" />
                <path className="h-route h-route--a" d="M302.3 128.5C297.2 128.9 282 132.4 272 130.8C262.1 129.2 252.1 122.1 242.6 119C233.1 115.9 219.6 113.5 215 112.4" pathLength="88" />
                <path className="h-route h-route--b" d="M301.7 119.5C296.6 119.9 280.5 123.2 270.7 121.6C261 119.9 252.4 112.7 243.4 109.7C234.5 106.7 221.4 104.6 217 103.6" pathLength="88" />
                <path className="h-route h-route--a" d="M214.8 112.3C212.4 111.6 204.5 109.4 200.2 108.2C196 107 193.2 106.2 189.2 105.1C185.2 104 180.5 102.9 176.3 101.7C172.1 100.5 168.3 99 164 97.9C159.7 96.7 155 95.1 150.3 94.8C145.7 94.4 140.4 95.1 136.2 95.8C132.1 96.4 129.4 97.5 125.5 98.6C121.6 99.7 115.1 101.8 113 102.4" pathLength="110" />
                <path className="h-route h-route--b" d="M217.2 103.7C214.8 103 207.4 100.9 202.7 99.6C198 98.2 193.2 96.9 188.8 95.7C184.4 94.5 180.4 93.5 176.3 92.3C172.2 91.1 168.7 89.7 164.1 88.6C159.5 87.4 153.2 85.9 148.7 85.6C144.2 85.2 141.6 85.6 137.3 86.4C133 87.1 127.3 88.8 122.9 90C118.5 91.2 113 93 111 93.6" pathLength="110" />
                <path className="h-route h-route--a" d="M116.5 98.4C116 100.8 112.6 108.3 113.5 112.7C114.4 117.2 118.5 121.8 121.9 125.2C125.3 128.5 129.8 131 134 132.9C138.2 134.8 142.7 135.6 147.2 136.7C151.8 137.9 158.8 139.2 161.2 139.7" pathLength="77" />
                <path className="h-route h-route--b" d="M107.5 97.6C107 100.1 104.1 107.8 104.5 112.6C104.9 117.4 107.5 122.4 110.2 126.3C112.9 130.1 116.8 132.9 120.6 135.5C124.5 138.2 129.2 140.6 133.3 142.3C137.4 143.9 141 144.5 145.3 145.5C149.5 146.5 156.6 147.9 158.8 148.3" pathLength="88" />
              </svg>
              <span className="h-plane-disc" style={{ left: "258.2px", top: "121.8px" }}>
                <svg viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
                  <use href="#h-plane-path" transform="rotate(-65.4) translate(-50 -50)" />
                </svg>
              </span>
              <span className="h-pin h-pin--stop" style={{ left: "302px", top: "124px" }} />
              <span className="h-pin h-pin--num" style={{ left: "216px", top: "108px" }}>1</span>
              <span className="h-pin h-pin--num" style={{ left: "112px", top: "98px" }}>2</span>
              <span className="h-pin h-pin--num" style={{ left: "160px", top: "144px" }}>3</span>
              <span className="h-map__chip" style={{ left: "306px", top: "94px" }}>PTY</span>
              <span className="h-map__chip" style={{ left: "210px", top: "78px" }}>San José</span>
              <span className="h-map__chip h-map__chip--start" style={{ left: "86px", top: "64px" }}>La Fortuna</span>
              <span className="h-map__chip h-map__chip--start" style={{ left: "182px", top: "148px" }}>Manuel Antonio</span>
              <span className="h-map__badge">
                <svg className="h-mark" width="28" height="28" aria-hidden="true" focusable="false">
                  <use href="#hermi-mark" />
                </svg>
              </span>
            </div>
          </div>
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <div className="h-screen doc-frame doc-frame--map">
            <div className="h-map" role="img" aria-label="Map of the Costa Rica route. Dotted routes join the flight stop in Panama City, then San José, La Fortuna and Manuel Antonio.">
              <svg className="h-map__svg" viewBox="0 0 390 194" aria-hidden="true" focusable="false">
                <defs>
                  <clipPath id="cr-band-d">
                    <path d="M-20 48C-10 34.7 20 46.3 40 46C60 45.7 81.7 45.3 100 46C118.3 46.7 133.3 48.3 150 50C166.7 51.7 183.3 53.7 200 56C216.7 58.3 233.3 60.3 250 64C266.7 67.7 283.3 73 300 78C316.7 83 331.7 89.3 350 94C368.3 98.7 400 92.3 410 106C420 119.7 421.7 165.3 410 176C398.3 186.7 360 170 340 170C320 170 306.7 174.3 290 176C273.3 177.7 256.7 180.3 240 180C223.3 179.7 206.7 176.7 190 174C173.3 171.3 155 167.7 140 164C125 160.3 113.3 156.3 100 152C86.7 147.7 73.3 142 60 138C46.7 134 33.3 130 20 128C6.7 126 -13.3 139.3 -20 126C-26.7 112.7 -30 61.3 -20 48Z" />
                  </clipPath>
                </defs>
                <rect className="h-map__water" width="390" height="194" />
                <path className="h-map__halo" d="M-20 48C-10 34.7 20 46.3 40 46C60 45.7 81.7 45.3 100 46C118.3 46.7 133.3 48.3 150 50C166.7 51.7 183.3 53.7 200 56C216.7 58.3 233.3 60.3 250 64C266.7 67.7 283.3 73 300 78C316.7 83 331.7 89.3 350 94C368.3 98.7 400 92.3 410 106C420 119.7 421.7 165.3 410 176C398.3 186.7 360 170 340 170C320 170 306.7 174.3 290 176C273.3 177.7 256.7 180.3 240 180C223.3 179.7 206.7 176.7 190 174C173.3 171.3 155 167.7 140 164C125 160.3 113.3 156.3 100 152C86.7 147.7 73.3 142 60 138C46.7 134 33.3 130 20 128C6.7 126 -13.3 139.3 -20 126C-26.7 112.7 -30 61.3 -20 48Z" />
                <path className="h-map__land h-map__land--bare" d="M-20 48C-10 34.7 20 46.3 40 46C60 45.7 81.7 45.3 100 46C118.3 46.7 133.3 48.3 150 50C166.7 51.7 183.3 53.7 200 56C216.7 58.3 233.3 60.3 250 64C266.7 67.7 283.3 73 300 78C316.7 83 331.7 89.3 350 94C368.3 98.7 400 92.3 410 106C420 119.7 421.7 165.3 410 176C398.3 186.7 360 170 340 170C320 170 306.7 174.3 290 176C273.3 177.7 256.7 180.3 240 180C223.3 179.7 206.7 176.7 190 174C173.3 171.3 155 167.7 140 164C125 160.3 113.3 156.3 100 152C86.7 147.7 73.3 142 60 138C46.7 134 33.3 130 20 128C6.7 126 -13.3 139.3 -20 126C-26.7 112.7 -30 61.3 -20 48Z" />
                <g clipPath="url(#cr-band-d)">
                  <path className="h-map__land h-map__land--alt" d="M-40 0L58 0L56 96L64 190L-40 190Z" />
                  <path className="h-map__land h-map__land--alt" d="M334 96L430 96L430 300L342 300Z" />
                  <path className="h-map__hill" d="M150 112C159.3 107 179.3 103.7 196 104C212.7 104.3 239 108 250 114C261 120 266.7 132.3 262 140C257.3 147.7 237.3 158 222 160C206.7 162 183.7 156.3 170 152C156.3 147.7 143.3 140.7 140 134C136.7 127.3 140.7 117 150 112Z" />
                </g>
                <path className="h-map__coast" d="M-20 48C-10 34.7 20 46.3 40 46C60 45.7 81.7 45.3 100 46C118.3 46.7 133.3 48.3 150 50C166.7 51.7 183.3 53.7 200 56C216.7 58.3 233.3 60.3 250 64C266.7 67.7 283.3 73 300 78C316.7 83 331.7 89.3 350 94C368.3 98.7 400 92.3 410 106C420 119.7 421.7 165.3 410 176C398.3 186.7 360 170 340 170C320 170 306.7 174.3 290 176C273.3 177.7 256.7 180.3 240 180C223.3 179.7 206.7 176.7 190 174C173.3 171.3 155 167.7 140 164C125 160.3 113.3 156.3 100 152C86.7 147.7 73.3 142 60 138C46.7 134 33.3 130 20 128C6.7 126 -13.3 139.3 -20 126C-26.7 112.7 -30 61.3 -20 48Z" />
                <path className="h-route h-route--a" d="M403.6 142.5C398.9 142.1 384.3 141.3 375.4 140.4C366.5 139.6 358.5 138.6 350.1 137.4C341.7 136.1 333 134.4 324.9 132.9C316.8 131.4 305.2 129.2 301.2 128.4" pathLength="99" />
                <path className="h-route h-route--b" d="M404.4 133.5C399.7 133.2 385 132.3 376.2 131.4C367.4 130.6 359.8 129.7 351.5 128.5C343.2 127.2 334.7 125.6 326.6 124.1C318.4 122.6 306.8 120.3 302.8 119.6" pathLength="99" />
                <path className="h-route h-route--a" d="M302.3 128.5C297.2 128.9 282 132.4 272 130.8C262.1 129.2 252.1 122.1 242.6 119C233.1 115.9 219.6 113.5 215 112.4" pathLength="88" />
                <path className="h-route h-route--b" d="M301.7 119.5C296.6 119.9 280.5 123.2 270.7 121.6C261 119.9 252.4 112.7 243.4 109.7C234.5 106.7 221.4 104.6 217 103.6" pathLength="88" />
                <path className="h-route h-route--a" d="M214.8 112.3C212.4 111.6 204.5 109.4 200.2 108.2C196 107 193.2 106.2 189.2 105.1C185.2 104 180.5 102.9 176.3 101.7C172.1 100.5 168.3 99 164 97.9C159.7 96.7 155 95.1 150.3 94.8C145.7 94.4 140.4 95.1 136.2 95.8C132.1 96.4 129.4 97.5 125.5 98.6C121.6 99.7 115.1 101.8 113 102.4" pathLength="110" />
                <path className="h-route h-route--b" d="M217.2 103.7C214.8 103 207.4 100.9 202.7 99.6C198 98.2 193.2 96.9 188.8 95.7C184.4 94.5 180.4 93.5 176.3 92.3C172.2 91.1 168.7 89.7 164.1 88.6C159.5 87.4 153.2 85.9 148.7 85.6C144.2 85.2 141.6 85.6 137.3 86.4C133 87.1 127.3 88.8 122.9 90C118.5 91.2 113 93 111 93.6" pathLength="110" />
                <path className="h-route h-route--a" d="M116.5 98.4C116 100.8 112.6 108.3 113.5 112.7C114.4 117.2 118.5 121.8 121.9 125.2C125.3 128.5 129.8 131 134 132.9C138.2 134.8 142.7 135.6 147.2 136.7C151.8 137.9 158.8 139.2 161.2 139.7" pathLength="77" />
                <path className="h-route h-route--b" d="M107.5 97.6C107 100.1 104.1 107.8 104.5 112.6C104.9 117.4 107.5 122.4 110.2 126.3C112.9 130.1 116.8 132.9 120.6 135.5C124.5 138.2 129.2 140.6 133.3 142.3C137.4 143.9 141 144.5 145.3 145.5C149.5 146.5 156.6 147.9 158.8 148.3" pathLength="88" />
              </svg>
              <span className="h-plane-disc" style={{ left: "258.2px", top: "121.8px" }}>
                <svg viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
                  <use href="#h-plane-path" transform="rotate(-65.4) translate(-50 -50)" />
                </svg>
              </span>
              <span className="h-pin h-pin--stop" style={{ left: "302px", top: "124px" }} />
              <span className="h-pin h-pin--num" style={{ left: "216px", top: "108px" }}>1</span>
              <span className="h-pin h-pin--num" style={{ left: "112px", top: "98px" }}>2</span>
              <span className="h-pin h-pin--num" style={{ left: "160px", top: "144px" }}>3</span>
              <span className="h-map__chip" style={{ left: "306px", top: "94px" }}>PTY</span>
              <span className="h-map__chip" style={{ left: "210px", top: "78px" }}>San José</span>
              <span className="h-map__chip h-map__chip--start" style={{ left: "86px", top: "64px" }}>La Fortuna</span>
              <span className="h-map__chip h-map__chip--start" style={{ left: "182px", top: "148px" }}>Manuel Antonio</span>
              <span className="h-map__badge">
                <svg className="h-mark" width="28" height="28" aria-hidden="true" focusable="false">
                  <use href="#hermi-mark" />
                </svg>
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function Block_map_shapes_Demo() {
  return (
    <>
      <div className="h-screen doc-frame doc-frame--map">
      <div className="h-map" role="img" aria-label="Illustrated map of La Fortuna">
        <svg className="h-map__svg" viewBox="0 0 390 194" aria-hidden="true" focusable="false">
          <rect className="h-map__ground" width="390" height="194" />
          <g transform="translate(0 -44)">
            <path className="h-map__halo" d="M-30 132C-18.3 92 15 121 40 120C65 119 95 122.3 120 126C145 129.7 168.3 135 190 142C211.7 149 226.7 162.3 250 168C273.3 173.7 301.7 176 330 176C358.3 176 403.3 137.3 420 168C436.7 198.7 505 328 430 360C355 392 46.7 398 -30 360C-106.7 322 -41.7 172 -30 132Z" />
            <path className="h-map__land h-map__land--bare" d="M-30 132C-18.3 92 15 121 40 120C65 119 95 122.3 120 126C145 129.7 168.3 135 190 142C211.7 149 226.7 162.3 250 168C273.3 173.7 301.7 176 330 176C358.3 176 403.3 137.3 420 168C436.7 198.7 505 328 430 360C355 392 46.7 398 -30 360C-106.7 322 -41.7 172 -30 132Z" />
            <ellipse className="h-map__relief" cx="288" cy="118" rx="112" ry="84" transform="rotate(-18 288 118)" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="80" ry="58" transform="rotate(-18 288 118)" fillOpacity="0.1" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="52" ry="37" transform="rotate(-18 288 118)" fillOpacity="0.14" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="26" ry="18" transform="rotate(-18 288 118)" fillOpacity="0.2" />
            <path className="h-map__river" d="M262 146C259.3 151 253 168.3 246 176C239 183.7 228.3 185.7 220 192C211.7 198.3 207.7 208 196 214C184.3 220 164.3 221.7 150 228C135.7 234.3 116.7 248 110 252" />
            <path className="h-map__halo" d="M-20 66C-11.7 59.3 15 61.3 30 62C45 62.7 56.3 69.7 70 70C83.7 70.3 100 62.7 112 64C124 65.3 140.3 72.3 142 78C143.7 83.7 131 93.7 122 98C113 102.3 99 103.7 88 104C77 104.3 67.3 99.3 56 100C44.7 100.7 32.7 107.7 20 108C7.3 108.3 -13.3 109 -20 102C-26.7 95 -28.3 72.7 -20 66Z" />
            <path className="h-map__lake" d="M-20 66C-11.7 59.3 15 61.3 30 62C45 62.7 56.3 69.7 70 70C83.7 70.3 100 62.7 112 64C124 65.3 140.3 72.3 142 78C143.7 83.7 131 93.7 122 98C113 102.3 99 103.7 88 104C77 104.3 67.3 99.3 56 100C44.7 100.7 32.7 107.7 20 108C7.3 108.3 -13.3 109 -20 102C-26.7 95 -28.3 72.7 -20 66Z" />
            <path className="h-map__peak" d="M281 121L288 110L295 121Z" />
          </g>
        </svg>
      </div>
    </div>
    </>
  )
}

export function Block_map_shapes() {
  return (
    <section className="doc-block" id="map-shapes">
      <h3 className="doc-h3">Map shapes</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-map__ground</code>
            {' '}
            <code>.h-map__land--bare</code>
            {' '}
            <code>.h-map__halo</code>
            {' '}
            <code>.h-map__relief</code>
            {' '}
            <code>.h-map__lake</code>
            {' '}
            <code>.h-map__river</code>
            {' '}
            <code>.h-map__peak</code>
            {' '}
            <code>.h-map__land--islet</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>05 section 4.21, illustration layer.</dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            {"Compose a map from these shape classes inside "}
            <code>.h-map__svg</code>
            . Fills come from tokens, so dark mode needs no extra work.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_map_shapes_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_map_shapes_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_markers_Demo() {
  return (
    <>
      <div className="h-screen doc-frame doc-frame--short">
      <div className="h-map" role="img" aria-label="Map sample">
        <svg className="h-map__svg" viewBox="0 0 390 180" aria-hidden="true" focusable="false">
          <rect className="h-map__water" width="390" height="180" />
          <path className="h-map__halo" d="M-30 20C-5 -11.7 81.7 6.7 120 10C158.3 13.3 176.7 38.3 200 40C223.3 41.7 223.3 21.7 260 20C296.7 18.3 393.3 0 420 30C446.7 60 495 171.7 420 200C345 228.3 45 230 -30 200C-105 170 -55 51.7 -30 20Z" />
          <path className="h-map__land" d="M-30 20C-5 -11.7 81.7 6.7 120 10C158.3 13.3 176.7 38.3 200 40C223.3 41.7 223.3 21.7 260 20C296.7 18.3 393.3 0 420 30C446.7 60 495 171.7 420 200C345 228.3 45 230 -30 200C-105 170 -55 51.7 -30 20Z" />
        </svg>
        <span className="h-pin h-pin--num h-pin--outdoors" style={{ left: "40px", top: "70px" }}>1</span>
        <span className="h-pin h-pin--num h-pin--food" style={{ left: "100px", top: "70px" }}>2</span>
        <span className="h-pin h-pin--num h-pin--culture" style={{ left: "160px", top: "70px" }}>3</span>
        <span className="h-pin h-pin--stop" style={{ left: "215px", top: "70px" }} />
        <span className="h-pin h-pin--start h-pin--a" style={{ left: "250px", top: "70px" }} />
        <span className="h-pin h-pin--start h-pin--b" style={{ left: "275px", top: "70px" }} />
        <span className="h-plane-disc" style={{ left: "320px", top: "70px" }}>
          <svg viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
            <use href="#h-plane-path" transform="rotate(60) translate(-50 -50)" />
          </svg>
        </span>
        <span className="h-plane-disc h-plane-disc--sm" style={{ left: "362px", top: "70px" }}>
          <svg viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
            <use href="#h-plane-path" transform="rotate(0) translate(-50 -50)" />
          </svg>
        </span>
        <span className="h-pin h-pin--price-active" style={{ left: "70px", top: "140px" }}>$142</span>
        <span className="h-pin h-pin--price" style={{ left: "150px", top: "140px" }}>$188</span>
        <span className="h-map__chip" style={{ left: "250px", top: "128px" }}>La Fortuna</span>
        <span className="h-map__chip h-map__chip--code" style={{ left: "330px", top: "128px" }}>RDU</span>
      </div>
    </div>
    </>
  )
}

export function Block_markers() {
  return (
    <section className="doc-block" id="markers">
      <h3 className="doc-h3">Map markers</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-pin--num</code>
            {' '}
            <code>.h-pin--stop</code>
            {' '}
            <code>.h-pin--start</code>
            {' '}
            <code>.h-pin--price</code>
            {' '}
            <code>.h-pin--price-active</code>
            {' '}
            <code>.h-plane-disc</code>
            {' '}
            <code>.h-map__chip</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.21, becomes "}
            <code>{"<MapPin>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Numbered stops take their activity group as the ring (--culture, --food, --outdoors, --shopping, --neutral). The plane marks where the trip is; rotate its glyph along the route.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_markers_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_markers_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_routes_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--paper">
      <svg className="doc-route" viewBox="0 0 358 120" role="img" aria-label="Route stroke sizes: default twin route, large single route and small route">
        <path className="h-route h-route--a" d="M9.6 65.5C14 65.3 28.3 64.5 36.5 64C44.8 63.5 51.1 63.2 59 62.4C66.9 61.5 75.9 60.6 83.9 58.8C92 57 99.4 54.4 107.1 51.5C114.9 48.5 122.6 44.3 130.4 40.8C138.3 37.3 146.5 33.1 154.3 30.3C162 27.5 168.8 25.5 177 23.9C185.1 22.2 195 21.2 203.1 20.4C211.2 19.6 217.9 19.3 225.6 18.9C233.4 18.4 245.6 17.7 249.6 17.5" pathLength="242" />
        <path className="h-route h-route--b" d="M10.4 74.5C14.9 74.2 28.8 73.5 37 73C45.3 72.5 51.7 72.2 59.8 71.3C68 70.4 77.7 69.3 85.8 67.6C93.8 65.8 100.4 63.7 108.1 60.7C115.8 57.8 124.1 53.6 131.9 50.1C139.8 46.5 147.4 42.5 155.2 39.6C163 36.7 170.5 34.4 178.7 32.7C186.8 31 196 30.2 203.9 29.4C211.8 28.6 218.3 28.3 226.1 27.9C233.9 27.4 246.4 26.7 250.4 26.5" pathLength="242" />
        <path className="h-route h-route--a h-route--lg" d="M10 104C14.5 103.8 27.6 103 36.8 102.6C46 102.1 56.4 101.5 65.2 101.1C74.1 100.7 81.3 100.3 90 100C98.7 99.7 108.3 99.3 117.5 99C126.7 98.7 136.2 98.4 145 98.3C153.8 98.1 161.2 98 170 98C178.8 98 188.4 98.2 197.7 98.4C207 98.6 217.1 99 225.9 99.2C234.6 99.5 246 99.9 250 100" pathLength="240" />
        <path className="h-route h-route--b h-route--sm" d="M280 40L348 40" />
        <path className="h-route h-route--a h-route--sm" d="M280 56L348 56" />
      </svg>
    </div>
    </>
  )
}

export function Block_routes() {
  return (
    <section className="doc-block" id="routes">
      <h3 className="doc-h3">Route strokes</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-route--a</code>
            {' '}
            <code>.h-route--b</code>
            {' '}
            <code>.h-route--lg</code>
            {' '}
            <code>.h-route--sm</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 2.9, route pattern. Becomes "}
            <code>{"<RoutePath>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Dotted routes in SVG: pink is traveler 1, yellow is traveler 2. Round caps make the dots. Set pathLength to dots times 11 so the dots fit the path exactly.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_routes_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_routes_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_sheet_Demo() {
  return (
    <>
      <div className="h-screen doc-frame doc-frame--sheet">
      <div className="h-map" role="img" aria-label="Illustrated map of La Fortuna">
        <svg className="h-map__svg" viewBox="0 0 390 194" aria-hidden="true" focusable="false">
          <rect className="h-map__ground" width="390" height="194" />
          <g transform="translate(0 -44)">
            <path className="h-map__halo" d="M-30 132C-18.3 92 15 121 40 120C65 119 95 122.3 120 126C145 129.7 168.3 135 190 142C211.7 149 226.7 162.3 250 168C273.3 173.7 301.7 176 330 176C358.3 176 403.3 137.3 420 168C436.7 198.7 505 328 430 360C355 392 46.7 398 -30 360C-106.7 322 -41.7 172 -30 132Z" />
            <path className="h-map__land h-map__land--bare" d="M-30 132C-18.3 92 15 121 40 120C65 119 95 122.3 120 126C145 129.7 168.3 135 190 142C211.7 149 226.7 162.3 250 168C273.3 173.7 301.7 176 330 176C358.3 176 403.3 137.3 420 168C436.7 198.7 505 328 430 360C355 392 46.7 398 -30 360C-106.7 322 -41.7 172 -30 132Z" />
            <ellipse className="h-map__relief" cx="288" cy="118" rx="112" ry="84" transform="rotate(-18 288 118)" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="80" ry="58" transform="rotate(-18 288 118)" fillOpacity="0.1" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="52" ry="37" transform="rotate(-18 288 118)" fillOpacity="0.14" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="26" ry="18" transform="rotate(-18 288 118)" fillOpacity="0.2" />
            <path className="h-map__river" d="M262 146C259.3 151 253 168.3 246 176C239 183.7 228.3 185.7 220 192C211.7 198.3 207.7 208 196 214C184.3 220 164.3 221.7 150 228C135.7 234.3 116.7 248 110 252" />
            <path className="h-map__halo" d="M-20 66C-11.7 59.3 15 61.3 30 62C45 62.7 56.3 69.7 70 70C83.7 70.3 100 62.7 112 64C124 65.3 140.3 72.3 142 78C143.7 83.7 131 93.7 122 98C113 102.3 99 103.7 88 104C77 104.3 67.3 99.3 56 100C44.7 100.7 32.7 107.7 20 108C7.3 108.3 -13.3 109 -20 102C-26.7 95 -28.3 72.7 -20 66Z" />
            <path className="h-map__lake" d="M-20 66C-11.7 59.3 15 61.3 30 62C45 62.7 56.3 69.7 70 70C83.7 70.3 100 62.7 112 64C124 65.3 140.3 72.3 142 78C143.7 83.7 131 93.7 122 98C113 102.3 99 103.7 88 104C77 104.3 67.3 99.3 56 100C44.7 100.7 32.7 107.7 20 108C7.3 108.3 -13.3 109 -20 102C-26.7 95 -28.3 72.7 -20 66Z" />
            <path className="h-map__peak" d="M281 121L288 110L295 121Z" />
          </g>
        </svg>
      </div>
      <Sheet>
        <SheetGrabber />
        <SheetBody>
          <h4 className="h-heading">Bottom sheet</h4>
          <p className="h-soft">Elevation level 3, 20 px top corners, a 36 by 5 grabber.</p>
        </SheetBody>
      </Sheet>
    </div>
    </>
  )
}

export function Block_sheet() {
  return (
    <section className="doc-block" id="sheet">
      <h3 className="doc-h3">Bottom sheet</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-sheet</code>
            {' '}
            <code>__grabber</code>
            {' '}
            <code>__body</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.19 Bottom sheet, becomes "}
            <code>{"<Sheet>"}</code>
            {" (vaul on phones)."}
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Content over the map. Use on phones for trip screens and forms; web converts it to a 480 px dialog or a side panel.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_sheet_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_sheet_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_navbtn_Demo() {
  return (
    <>
      <div className="h-screen doc-frame doc-frame--short">
      <div className="h-map" role="img" aria-label="Illustrated map of La Fortuna">
        <svg className="h-map__svg" viewBox="0 0 390 194" aria-hidden="true" focusable="false">
          <rect className="h-map__ground" width="390" height="194" />
          <g transform="translate(0 -44)">
            <path className="h-map__halo" d="M-30 132C-18.3 92 15 121 40 120C65 119 95 122.3 120 126C145 129.7 168.3 135 190 142C211.7 149 226.7 162.3 250 168C273.3 173.7 301.7 176 330 176C358.3 176 403.3 137.3 420 168C436.7 198.7 505 328 430 360C355 392 46.7 398 -30 360C-106.7 322 -41.7 172 -30 132Z" />
            <path className="h-map__land h-map__land--bare" d="M-30 132C-18.3 92 15 121 40 120C65 119 95 122.3 120 126C145 129.7 168.3 135 190 142C211.7 149 226.7 162.3 250 168C273.3 173.7 301.7 176 330 176C358.3 176 403.3 137.3 420 168C436.7 198.7 505 328 430 360C355 392 46.7 398 -30 360C-106.7 322 -41.7 172 -30 132Z" />
            <ellipse className="h-map__relief" cx="288" cy="118" rx="112" ry="84" transform="rotate(-18 288 118)" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="80" ry="58" transform="rotate(-18 288 118)" fillOpacity="0.1" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="52" ry="37" transform="rotate(-18 288 118)" fillOpacity="0.14" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="26" ry="18" transform="rotate(-18 288 118)" fillOpacity="0.2" />
            <path className="h-map__river" d="M262 146C259.3 151 253 168.3 246 176C239 183.7 228.3 185.7 220 192C211.7 198.3 207.7 208 196 214C184.3 220 164.3 221.7 150 228C135.7 234.3 116.7 248 110 252" />
            <path className="h-map__halo" d="M-20 66C-11.7 59.3 15 61.3 30 62C45 62.7 56.3 69.7 70 70C83.7 70.3 100 62.7 112 64C124 65.3 140.3 72.3 142 78C143.7 83.7 131 93.7 122 98C113 102.3 99 103.7 88 104C77 104.3 67.3 99.3 56 100C44.7 100.7 32.7 107.7 20 108C7.3 108.3 -13.3 109 -20 102C-26.7 95 -28.3 72.7 -20 66Z" />
            <path className="h-map__lake" d="M-20 66C-11.7 59.3 15 61.3 30 62C45 62.7 56.3 69.7 70 70C83.7 70.3 100 62.7 112 64C124 65.3 140.3 72.3 142 78C143.7 83.7 131 93.7 122 98C113 102.3 99 103.7 88 104C77 104.3 67.3 99.3 56 100C44.7 100.7 32.7 107.7 20 108C7.3 108.3 -13.3 109 -20 102C-26.7 95 -28.3 72.7 -20 66Z" />
            <path className="h-map__peak" d="M281 121L288 110L295 121Z" />
          </g>
        </svg>
      </div>
      <a className="h-navbtn h-navbtn--back" href="#" aria-label="Back to Trips">
        <Icon name="chevron-left" />
      </a>
      <button className="h-navbtn h-navbtn--menu" type="button" aria-haspopup="menu" aria-label="Trip menu: share, settings, export">
        <Icon name="ellipsis" />
      </button>
    </div>
    </>
  )
}

export function Block_navbtn() {
  return (
    <section className="doc-block" id="navbtn">
      <h3 className="doc-h3">Nav buttons</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-navbtn</code>
            {' '}
            <code>--back</code>
            {' '}
            <code>--menu</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 5.2 Navigation bar, becomes "}
            <code>{"<NavButton>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Round floating back and menu buttons over the map. Both are 44 pt, elevation level 2, and need an aria-label.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_navbtn_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_navbtn_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_tabbar_Demo() {
  return (
    <>
      <div className="h-screen doc-frame doc-frame--bar">
      <TabBar
        active="trips"
        items={[
          { key: "trips", label: "Trips", icon: "luggage", href: "02-trips-home.html" },
          { key: "discover", label: "Discover", icon: "compass", href: "#discover" },
          { key: "activity", label: "Activity", icon: "bell", href: "#activity", badge: 3 },
          { key: "account", label: "Account", icon: "circle-user", href: "#account" },
        ]}
      />
    </div>
    </>
  )
}

export function Block_tabbar() {
  return (
    <section className="doc-block" id="tabbar">
      <h3 className="doc-h3">Tab bar</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-tabbar</code>
            {' '}
            <code>__bar</code>
            {' '}
            <code>__item</code>
            {' '}
            <code>__badge</code>
            {' '}
            <code>--active</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.20 Tab bar, becomes "}
            <code>{"<TabBar>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Four tabs: Trips, Discover, Activity, Account. A floating pill over a fade. Hide it in full-screen sheets and present mode.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_tabbar_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_tabbar_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_strip_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <SectionTabs
        label="Trip sections"
        active="overview"
        items={[
          { key: "overview", label: "Overview", href: "03-trip-overview.html" },
          { key: "flights", label: "Flights", href: "05-fare-detail.html" },
          { key: "stays", label: "Stays", href: "06-stays-vote.html" },
          { key: "plan", label: "Plan", href: "04-plan-day.html" },
          { key: "group", label: "Group", href: "#group" },
          { key: "present", label: "Present", href: "#present" },
        ]}
      />
    </div>
    </>
  )
}

export function Block_strip() {
  return (
    <section className="doc-block" id="strip">
      <h3 className="doc-h3">Section strip</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-strip</code>
            {' '}
            <code>__tab</code>
            {' '}
            <code>[aria-selected="true"]</code>
            {' '}
            <code>[aria-current="page"]</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 5.2 Section strip, becomes "}
            <code>{"<SectionTabs>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>{'Six scrollable pill tabs under a trip header. A nav of links; the current one has aria-current="page".'}</dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_strip_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_strip_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_seg_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <SegmentedControl aria-label="Plan view">
        <SegItem selected>Days</SegItem>
        <SegItem>Calendar</SegItem>
        <SegItem>Map</SegItem>
      </SegmentedControl>
      <SegmentedControl narrow aria-label="Stays view">
        <SegItem>List</SegItem>
        <SegItem selected>Compare</SegItem>
      </SegmentedControl>
    </div>
    </>
  )
}

export function Block_seg() {
  return (
    <section className="doc-block" id="seg">
      <h3 className="doc-h3">Segmented control</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-seg</code>
            {' '}
            <code>__item</code>
            {' '}
            <code>--narrow</code>
            {' '}
            <code>[aria-selected="true"]</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.21 Segmented control, becomes "}
            <code>{"<SegmentedControl>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>A view toggle such as List or Map. A 34 px visual inside a 44 pt target.</dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_seg_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_seg_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_daychip_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <DayChips aria-label="Days">
        <DayChip href="#day1" aria-label="Day 1, Wed 25 Nov">D1</DayChip>
        <DayChip href="#day2" aria-label="Day 2, Thu 26 Nov">D2</DayChip>
        <DayChip href="#day3" aria-label="Day 3, Fri 27 Nov">D3</DayChip>
        <DayChip selected current href="#day4" aria-label="Day 4, Sat 28 Nov">D4</DayChip>
        <DayChip href="#day5" aria-label="Day 5, Sun 29 Nov">D5</DayChip>
        <DayChip href="#day6" aria-label="Day 6, Mon 30 Nov">D6</DayChip>
        <DayChip href="#day7" aria-label="Day 7, Tue 1 Dec">D7</DayChip>
        <DayChip href="#day8" aria-label="Day 8, Wed 2 Dec">D8</DayChip>
        <DayChip href="#day9" aria-label="Day 9, Thu 3 Dec">D9</DayChip>
        <DayChip href="#day10" aria-label="Day 10, Fri 4 Dec">D10</DayChip>
        <DayChip href="#day11" aria-label="Day 11, Sat 5 Dec">D11</DayChip>
        <DayChip href="#day12" aria-label="Day 12, Sun 6 Dec">D12</DayChip>
      </DayChips>
    </div>
    </>
  )
}

export function Block_daychip() {
  return (
    <section className="doc-block" id="daychip">
      <h3 className="doc-h3">Day chips</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-daychips</code>
            {' '}
            <code>.h-daychip</code>
            {' '}
            <code>[aria-selected="true"]</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.7 Calendar, becomes "}
            <code>{"<DayChips>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>A scrolling row of days on the Plan view. The selected day is ink.</dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_daychip_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_daychip_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_ticket_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <TripTicket as="a" href="#" aria-label="Costa Rica, 25 November to 6 December 2026, flight booked, 2 travelers, departs in 53 days">
        <div className="h-ticket__body">
          <div className="h-ticket__top">
            <h4 className="h-ticket__name">Costa Rica</h4>
            <span className="h-ticket__dates">25 Nov to 6 Dec 2026</span>
          </div>
          <div className="h-codes">
            <span className="h-codes__code">RDU</span>
            <svg className="h-codes__route" viewBox="0 0 140 34" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">
              <path className="h-route h-route--a h-route--sm" d="M5 27C26 27 42 11 61 11" />
              <path className="h-route h-route--b h-route--sm" d="M79 11C98 11 114 27 135 27" />
              <circle className="h-codes__start--a" cx="5" cy="27" r="3.4" />
              <circle className="h-codes__start--b" cx="135" cy="27" r="3.4" />
              <use className="h-codes__plane" href="#h-plane-path" transform="translate(70 11) rotate(90) scale(.3) translate(-50 -50)" />
            </svg>
            <span className="h-codes__code">SJO</span>
          </div>
          <dl className="h-ticket__fields">
            <Field label="Nights">11</Field>
            <Field label="Travelers" text>
              <Avatars>
                <Avatar tone="t1" label="Ana">AN</Avatar>
                <Avatar tone="t2" label="Leo">LE</Avatar>
              </Avatars>
            </Field>
            <Field label="Flight">Copa</Field>
          </dl>
        </div>
        <TicketStub>
          <StatusStub status="booked">Booked</StatusStub>
          <span className="h-ticket__note">
            {"Departs in "}
            <span className="h-mono">53</span>
            {" days"}
          </span>
          <Icon name="chevron-right" size={20} className="h-ticket__go" />
        </TicketStub>
      </TripTicket>
      <TripTicket as="a" mod={['sky']} href="#" aria-label="Costa Rica, flights booked">
        <div className="h-ticket__head h-ticket__head--sky">
          <div className="h-ticket__top">
            <h4 className="h-ticket__name h-ticket__name--lg">Costa Rica</h4>
            <span className="h-ticket__dates">25 Nov to 6 Dec 2026</span>
          </div>
          <div className="h-codes h-codes--lg">
            <span className="h-codes__code">RDU</span>
            <svg className="h-codes__route" viewBox="0 0 140 34" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">
              <path className="h-route h-route--a h-route--sm" d="M5 27C26 27 42 11 61 11" />
              <path className="h-route h-route--b h-route--sm" d="M79 11C98 11 114 27 135 27" />
              <circle className="h-codes__start--a" cx="5" cy="27" r="3.4" />
              <circle className="h-codes__start--b" cx="135" cy="27" r="3.4" />
              <use className="h-codes__plane" href="#h-plane-path" transform="translate(70 11) rotate(90) scale(.3) translate(-50 -50)" />
            </svg>
            <span className="h-codes__code">SJO</span>
          </div>
        </div>
        <div className="h-ticket__body">
          <dl className="h-ticket__fields">
            <Field label="Nights">11</Field>
            <Field label="Travelers" text>
              <Avatars>
                <Avatar tone="t1" label="Ana">AN</Avatar>
                <Avatar tone="t2" label="Leo">LE</Avatar>
              </Avatars>
            </Field>
            <Field label="Flight">Copa</Field>
            <Field label="Via">PTY</Field>
          </dl>
        </div>
        <TicketStub>
          <StatusStub status="booked">Booked</StatusStub>
          <span className="h-ticket__note">
            {"Departs in "}
            <span className="h-mono">53</span>
            {" days"}
          </span>
          <Icon name="chevron-right" size={20} className="h-ticket__go" />
        </TicketStub>
      </TripTicket>
      <TripTicket as="a" mod={['two-line']} href="#" aria-label="Lisbon and Porto, planning, fare watch from 612 dollars">
        <div className="h-ticket__body">
          <div className="h-ticket__top">
            <h4 className="h-ticket__name">Lisbon and Porto</h4>
            <span className="h-ticket__dates">12 to 19 Mar 2027</span>
          </div>
          <div className="h-codes">
            <span className="h-codes__code">RDU</span>
            <svg className="h-codes__route" viewBox="0 0 140 34" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">
              <path className="h-route h-route--a h-route--sm" d="M5 27C26 27 42 11 61 11" />
              <path className="h-route h-route--b h-route--sm" d="M79 11C98 11 114 27 135 27" />
              <circle className="h-codes__start--a" cx="5" cy="27" r="3.4" />
              <circle className="h-codes__start--b" cx="135" cy="27" r="3.4" />
              <use className="h-codes__plane" href="#h-plane-path" transform="translate(70 11) rotate(90) scale(.3) translate(-50 -50)" />
            </svg>
            <span className="h-codes__code">LIS</span>
          </div>
          <dl className="h-ticket__fields">
            <Field label="Nights">7</Field>
            <Field label="Travelers" text>
              <Avatars>
                <Avatar tone="t1" label="Ana">AN</Avatar>
                <Avatar tone="t2" label="Leo">LE</Avatar>
              </Avatars>
            </Field>
            <Field label="From">
              <b>$612</b>
            </Field>
          </dl>
        </div>
        <TicketStub>
          <StatusStub status="planning">Planning</StatusStub>
          <span className="h-ticket__note h-ticket__note--stack">
            <span className="h-trend h-trend--down">
              <Icon name="arrow-down" size={16} bold />
              Down $42 since Tuesday
            </span>
            <span className="h-soft">Aviasales, checked 3 h ago</span>
          </span>
          <Icon name="chevron-right" size={20} className="h-ticket__go" />
        </TicketStub>
      </TripTicket>
    </div>
    </>
  )
}

export function Block_ticket() {
  return (
    <section className="doc-block" id="ticket">
      <h3 className="doc-h3">Ticket</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-ticket</code>
            {' '}
            <code>__card</code>
            {' '}
            <code>__head</code>
            {' '}
            <code>__head--sky</code>
            {' '}
            <code>__body</code>
            {' '}
            <code>__stub</code>
            {' '}
            <code>__tear</code>
            {' '}
            <code>--sky</code>
            {' '}
            <code>--two-line</code>
            {' '}
            <code>--lg</code>
            {' '}
            <code>--float</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.4 Trip card, becomes "}
            <code>{"<TripTicket>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            {"A trip, a flight, a summary. A masked card with notches at each tear: "}
            <code>--h-tear-a</code>
            {" and "}
            <code>--h-stub-h</code>
            {" position them. The hairline is a drop-shadow chain on the wrapper, so the notches are outlined too. Use "}
            <code>--sky</code>
            {" for the hero on a trip overview."}
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_ticket_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_ticket_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_ticket_cta_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <TripTicket mod={['sky', 'cta', 'lg']}>
        <div className="h-ticket__head h-ticket__head--sky h-ticket__head--center">
          <svg className="h-mark" width="56" height="56" aria-hidden="true" focusable="false">
            <use href="#hermi-mark" />
          </svg>
          <span className="h-lockup__name">Hermi</span>
        </div>
        <div className="h-ticket__body h-ticket__body--roomy">
          <h4 className="h-display">
            <span className="h-display__line">Plan together.</span>
            <span className="h-display__line">Know the fare.</span>
          </h4>
          <p className="h-lead">Build a trip with the people you are going with, and see what flights really cost.</p>
        </div>
        <TicketStub>
          <LinkBtn variant="primary" href="#">Plan a trip</LinkBtn>
          <LinkBtn variant="secondary" href="#">Sign in</LinkBtn>
          <p className="h-fine">
            {"By continuing you agree to the "}
            <a className="h-link" href="#terms">Terms</a>
            {" and the "}
            <a className="h-link" href="#privacy">Privacy policy</a>
            .
          </p>
        </TicketStub>
      </TripTicket>
    </div>
    </>
  )
}

export function Block_ticket_cta() {
  return (
    <section className="doc-block" id="ticket-cta">
      <h3 className="doc-h3">Ticket with actions</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-ticket--cta</code>
            {' '}
            <code>.h-ticket--lg</code>
            {' '}
            <code>.h-ticket--float</code>
            {' '}
            <code>.h-ticket__head--center</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 6.1 Splash and onboarding, becomes "}
            <code>{"<WelcomePass>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            {"The welcome pass: a sky head, the promise, then buttons in the stub. "}
            <code>--float</code>
            {" pins it to the bottom of a screen over the map (not shown here)."}
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_ticket_cta_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_ticket_cta_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_ticket_side_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <ol className="h-timeline">
        <li className="h-timeline__row h-timeline__row--outdoors">
          <div className="h-timeline__time">
            <span className="h-timeline__clock">7:30</span>
            <span className="h-timeline__ampm">AM</span>
          </div>
          <span className="h-timeline__node" aria-hidden="true">1</span>
          <TripTicket mod={['side']}>
            <div className="h-ticket__body">
              <span className="h-timeline__title">Arenal Hanging Bridges</span>
              <span className="h-timeline__meta">
                <Icon name="mountain" size={16} />
                {"Outdoors "}
                <span className="h-timeline__dur">2 h 30 min</span>
              </span>
            </div>
            <TicketStub bare>
              <span className="h-ticket__tear" aria-hidden="true" />
              <span className="h-label">Added by</span>
              <span className="h-timeline__by h-timeline__by--t1">
                <Avatar tone="t1" size="xs" label="Ana">AN</Avatar>
                Ana
              </span>
            </TicketStub>
          </TripTicket>
        </li>
      </ol>
      <TripTicket mod={['side', 'stub-wide']} role="group" aria-label="Aviasales, 612 dollars, checked 3 hours ago">
        <div className="h-ticket__body">
          <span className="h-provider__name">Aviasales</span>
          <span className="h-provider__price">
            <span className="h-provider__amount">$612</span>
            3 h ago
          </span>
        </div>
        <TicketStub bare>
          <span className="h-ticket__tear" aria-hidden="true" />
          <Btn variant="secondary" mod={['stub']} aria-label="Book on Aviasales, opens in a browser">
            Book on Aviasales
            <Icon name="external-link" size={14} />
          </Btn>
        </TicketStub>
      </TripTicket>
    </div>
    </>
  )
}

export function Block_ticket_side() {
  return (
    <section className="doc-block" id="ticket-side">
      <h3 className="doc-h3">Side stub ticket</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-ticket--side</code>
            {' '}
            <code>.h-ticket--stub-wide</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.8 Day card and 4.13 Affiliate offer, becomes "}
            <code>{"<ItemTicket>"}</code>
            {" and "}
            <code>{"<ProviderRow>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            A ticket turned 90 degrees: the tear is vertical and the stub is on the right. Use it for a timeline item (72 px stub) or a row with an action (168 px stub).
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_ticket_side_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_ticket_side_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_stub_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <div className="doc-row">
        <StatusStub status="booked">Booked</StatusStub>
        <StatusStub status="planning">Planning</StatusStub>
        <StatusStub status="done">Done</StatusStub>
        <StatusStub status="votes">Both like this</StatusStub>
      </div>
    </div>
    </>
  )
}

export function Block_stub() {
  return (
    <section className="doc-block" id="stub">
      <h3 className="doc-h3">Status tag</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-stub</code>
            {' '}
            <code>--booked</code>
            {' '}
            <code>--planning</code>
            {' '}
            <code>--done</code>
            {' '}
            <code>--votes</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.21 Ticket stub, becomes "}
            <code>{"<StatusStub>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            A status in a boarding-pass stub: notched left edge, three perforation dots. Text plus icon, never color alone.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_stub_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_stub_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_field_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <dl className="h-ticket__fields">
        <Field label="Nights">11</Field>
        <Field label="Travelers" text>
          <Avatars>
            <Avatar tone="t1" label="Ana">AN</Avatar>
            <Avatar tone="t2" label="Leo">LE</Avatar>
          </Avatars>
        </Field>
        <Field label="Airline" text>TAP Air Portugal</Field>
        <Field label="Duration">13 h 05 min</Field>
      </dl>
    </div>
    </>
  )
}

export function Block_field() {
  return (
    <section className="doc-block" id="field">
      <h3 className="doc-h3">Labeled value</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-field</code>
            {' '}
            <code>__label</code>
            {' '}
            <code>__value</code>
            {' '}
            <code>--text</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.4, becomes "}
            <code>{"<Field>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            {"A label over a value, inside a "}
            <code>dl</code>
            {". Values are mono (numbers, codes) unless "}
            <code>--text</code>
            .
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_field_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_field_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_codes_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <div className="h-codes">
        <span className="h-codes__code">RDU</span>
        <svg className="h-codes__route" viewBox="0 0 140 34" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">
          <path className="h-route h-route--a h-route--sm" d="M5 27C26 27 42 11 61 11" />
          <path className="h-route h-route--b h-route--sm" d="M79 11C98 11 114 27 135 27" />
          <circle className="h-codes__start--a" cx="5" cy="27" r="3.4" />
          <circle className="h-codes__start--b" cx="135" cy="27" r="3.4" />
          <use className="h-codes__plane" href="#h-plane-path" transform="translate(70 11) rotate(90) scale(.3) translate(-50 -50)" />
        </svg>
        <span className="h-codes__code">SJO</span>
      </div>
      <div className="h-codes h-codes--md">
        <span className="h-codes__code">RDU</span>
        <svg className="h-codes__route" viewBox="0 0 140 34" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">
          <path className="h-route h-route--a h-route--sm" d="M5 27C26 27 42 11 61 11" />
          <path className="h-route h-route--b h-route--sm" d="M79 11C98 11 114 27 135 27" />
          <circle className="h-codes__start--a" cx="5" cy="27" r="3.4" />
          <circle className="h-codes__start--b" cx="135" cy="27" r="3.4" />
          <use className="h-codes__plane" href="#h-plane-path" transform="translate(70 11) rotate(90) scale(.3) translate(-50 -50)" />
        </svg>
        <span className="h-codes__code">LIS</span>
      </div>
      <div className="doc-on-sky">
        <div className="h-codes h-codes--lg">
          <span className="h-codes__code">RDU</span>
          <svg className="h-codes__route" viewBox="0 0 140 34" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">
            <path className="h-route h-route--a h-route--sm" d="M5 27C26 27 42 11 61 11" />
            <path className="h-route h-route--b h-route--sm" d="M79 11C98 11 114 27 135 27" />
            <circle className="h-codes__start--a" cx="5" cy="27" r="3.4" />
            <circle className="h-codes__start--b" cx="135" cy="27" r="3.4" />
            <use className="h-codes__plane" href="#h-plane-path" transform="translate(70 11) rotate(90) scale(.3) translate(-50 -50)" />
          </svg>
          <span className="h-codes__code">SJO</span>
        </div>
      </div>
    </div>
    </>
  )
}

export function Block_codes() {
  return (
    <section className="doc-block" id="codes">
      <h3 className="doc-h3">Airport codes</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-codes</code>
            {' '}
            <code>__code</code>
            {' '}
            <code>__route</code>
            {' '}
            <code>--md</code>
            {' '}
            <code>--lg</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 2.4 type-code, becomes "}
            <code>{"<RouteCodes>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Big codes like a bag tag, joined by the small twin route and a plane. 05 allows 24 to 48 px, with 36 to 48 px on tickets and passes; the kit uses 36, 40 and 44 px.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_codes_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_codes_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_avatar_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <div className="doc-row">
        <Avatar tone="t1" label="Ana">AN</Avatar>
        <Avatar tone="t2" label="Leo">LE</Avatar>
        <Avatar tone="t3" label="Traveler 3">T3</Avatar>
        <Avatar tone="t4" label="Traveler 4">T4</Avatar>
        <Avatar tone="t5" label="Traveler 5">T5</Avatar>
        <Avatar tone="t6" label="Traveler 6">T6</Avatar>
        <Avatar tone="t7" label="Traveler 7">T7</Avatar>
        <Avatar tone="t8" label="Traveler 8">T8</Avatar>
      </div>
      <div className="doc-row">
        <Avatars>
          <Avatar tone="t1" label="Ana">AN</Avatar>
          <Avatar tone="t2" label="Leo">LE</Avatar>
        </Avatars>
        <Avatar tone="t1" size="sm">AN</Avatar>
        <Avatar tone="t2" size="xs">LE</Avatar>
      </div>
    </div>
    </>
  )
}

export function Block_avatar() {
  return (
    <section className="doc-block" id="avatar">
      <h3 className="doc-h3">Avatar</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-avatar</code>
            {' '}
            <code>--t1</code>
            {' '}
            <code>--t8</code>
            {' '}
            <code>--sm</code>
            {' '}
            <code>--xs</code>
            {' '}
            <code>.h-avatars</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.21 Avatar and avatar stack, becomes "}
            <code>{"<Avatar>"}</code>
            {" and "}
            <code>{"<AvatarStack>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>Initials on the person's traveler color, in join order. Always with a name or initials.</dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_avatar_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_avatar_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_vote_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <div className="doc-row">
        <button className="h-vote h-vote--t1" type="button" aria-pressed="true" aria-label="Ana likes this stay">
          <Avatar tone="t1" size="sm">AN</Avatar>
          <svg className="h-vote__heart" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <use href="#i-heart" />
          </svg>
        </button>
        <button className="h-vote h-vote--t2" type="button" aria-pressed="false" aria-label="Leo has not liked this stay">
          <Avatar tone="t2" size="sm">LE</Avatar>
          <svg className="h-vote__heart" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <use href="#i-heart" />
          </svg>
        </button>
        <button className="h-vote h-vote--t3" type="button" aria-pressed="true" aria-label="Sam likes this stay">
          <Avatar tone="t3" size="sm">T3</Avatar>
          <svg className="h-vote__heart" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <use href="#i-heart" />
          </svg>
        </button>
        <button className="h-vote h-vote--t4" type="button" aria-pressed="false" aria-label="Kai has not liked this stay">
          <Avatar tone="t4" size="sm">T4</Avatar>
          <svg className="h-vote__heart" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <use href="#i-heart" />
          </svg>
        </button>
      </div>
    </div>
    </>
  )
}

export function Block_vote() {
  return (
    <section className="doc-block" id="vote">
      <h3 className="doc-h3">Heart toggle</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-vote</code>
            {' '}
            <code>--t1</code>
            {' '}
            <code>--t8</code>
            {' '}
            <code>[aria-pressed="true"]</code>
            {' '}
            <code>.h-vote__heart</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.10 Lodging card with votes, becomes "}
            <code>{"<VoteButton>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Hearts are the only vote. State comes from aria-pressed; the heart fills with the voter's traveler color.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_vote_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_vote_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_tile_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <div className="h-tiles">
        <a className="h-tile" href="#" aria-label="Stays, 3 shortlisted, Leo has not voted">
          <span className="h-label">Stays</span>
          <span className="h-tile__value">
            {"3 "}
            <span className="h-tile__unit">shortlisted</span>
          </span>
          <span className="h-soft">Leo has not voted</span>
        </a>
        <a className="h-tile" href="#" aria-label="Plan, 6 of 12 days planned">
          <span className="h-label">Plan</span>
          <span className="h-tile__value">
            {"6 of 12 "}
            <span className="h-tile__unit">planned</span>
          </span>
          <svg className="h-tile__progress" viewBox="0 0 131 14" aria-hidden="true" focusable="false">
            <circle className="h-tile__progress-done" cx="4" cy="7" r="3" />
            <circle className="h-tile__progress-done" cx="14.5" cy="7" r="3" />
            <circle className="h-tile__progress-done" cx="25" cy="7" r="3" />
            <circle className="h-tile__progress-done" cx="35.5" cy="7" r="3" />
            <circle className="h-tile__progress-done" cx="46" cy="7" r="3" />
            <circle className="h-tile__progress-done" cx="56.5" cy="7" r="3" />
            <use className="h-tile__progress-plane" href="#h-plane-path" transform="translate(70 7) rotate(90) scale(.13) translate(-50 -50)" />
            <circle className="h-tile__progress-open" cx="83.5" cy="7" r="2.2" />
            <circle className="h-tile__progress-open" cx="94" cy="7" r="2.2" />
            <circle className="h-tile__progress-open" cx="104.5" cy="7" r="2.2" />
            <circle className="h-tile__progress-open" cx="115" cy="7" r="2.2" />
            <circle className="h-tile__progress-open" cx="125.5" cy="7" r="2.2" />
          </svg>
        </a>
      </div>
    </div>
    </>
  )
}

export function Block_tile() {
  return (
    <section className="doc-block" id="tile">
      <h3 className="doc-h3">Summary tile</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-tiles</code>
            {' '}
            <code>.h-tile</code>
            {' '}
            <code>__label</code>
            {' '}
            <code>__value</code>
            {' '}
            <code>__unit</code>
            {' '}
            <code>__progress</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.3 Cards, becomes "}
            <code>{"<SummaryTile>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            A quiet card link on the trip overview: a label, one mono value, one line of context. The plane in the progress dots sits between planned and open days.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_tile_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_tile_Demo />
        </div>
      </div>
    </section>
  )
}

export function Block_listcard() {
  return (
    <section className="doc-block" id="listcard">
      <h3 className="doc-h3">List card</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-listcard</code>
            {' '}
            <code>__title</code>
            {' '}
            <code>__row</code>
            {' '}
            <code>__check</code>
            {' '}
            <code>__text</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 6.x Overview Next steps, becomes "}
            <code>{"<NextSteps>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            A short list of what to do next: a check circle, one plain sentence, a chevron. Two or three rows.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <div className="doc-stage doc-stage--sheet doc-stage--pad">
            <section className="h-listcard" aria-labelledby="ns-l">
              <h4 className="h-label h-listcard__title" id="ns-l">Next steps</h4>
              <a className="h-listcard__row" href="#">
                <Icon name="circle" className="h-listcard__check" />
                <span className="h-listcard__text">Pick a place to stay in La Fortuna</span>
                <Icon name="chevron-right" size={20} className="h-listcard__go" />
              </a>
              <a className="h-listcard__row" href="#">
                <Icon name="circle" className="h-listcard__check" />
                <span className="h-listcard__text">Plan the other 6 days</span>
                <Icon name="chevron-right" size={20} className="h-listcard__go" />
              </a>
            </section>
          </div>
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <div className="doc-stage doc-stage--sheet doc-stage--pad">
            <section className="h-listcard" aria-labelledby="ns-d">
              <h4 className="h-label h-listcard__title" id="ns-d">Next steps</h4>
              <a className="h-listcard__row" href="#">
                <Icon name="circle" className="h-listcard__check" />
                <span className="h-listcard__text">Pick a place to stay in La Fortuna</span>
                <Icon name="chevron-right" size={20} className="h-listcard__go" />
              </a>
              <a className="h-listcard__row" href="#">
                <Icon name="circle" className="h-listcard__check" />
                <span className="h-listcard__text">Plan the other 6 days</span>
                <Icon name="chevron-right" size={20} className="h-listcard__go" />
              </a>
            </section>
          </div>
        </div>
      </div>
    </section>
  )
}

function Block_ai_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <a className="h-ai-entry" href="#ai" aria-label="Plan with AI, 12 credits left">
        <span className="h-ai-entry__icon" aria-hidden="true">
          <Icon name="sparkles" size={18} />
        </span>
        <span className="h-ai-entry__text">Plan with AI</span>
        <span className="h-credit">
          <Icon name="coins" size={14} />
          <span className="h-credit__n">12</span>
          {" credits left"}
        </span>
      </a>
      <button className="h-ai-entry h-ai-entry--pill" type="button" aria-label="Explain this fare, costs 1 credit">
        <span className="h-ai-entry__icon" aria-hidden="true">
          <Icon name="sparkles" size={20} />
        </span>
        <span className="h-ai-entry__text">Explain this fare</span>
        <span className="h-credit">
          <Icon name="coins" size={14} />
          <span className="h-credit__n">1</span>
          {" credit"}
        </span>
      </button>
      <div className="doc-row">
        <span className="h-credit">
          <Icon name="coins" size={14} />
          <span className="h-credit__n">12</span>
          {" credits left"}
        </span>
        <span className="h-credit">
          <Icon name="coins" size={14} />
          <span className="h-credit__n">1</span>
          {" credit"}
        </span>
      </div>
    </div>
    </>
  )
}

export function Block_ai() {
  return (
    <section className="doc-block" id="ai">
      <h3 className="doc-h3">AI entry and credit chip</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-ai-entry</code>
            {' '}
            <code>__icon</code>
            {' '}
            <code>__text</code>
            {' '}
            <code>--pill</code>
            {' '}
            <code>.h-credit</code>
            {' '}
            <code>__n</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.11 Credit cost chip, becomes "}
            <code>{"<AiEntry>"}</code>
            {" and "}
            <code>{"<CreditChip>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Say what it costs before the tap. The card row shows the balance; the pill form sits on a screen that already has a subject.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_ai_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_ai_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_btn_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <LinkBtn variant="primary" href="#">Plan a trip</LinkBtn>
      <LinkBtn variant="secondary" href="#">Sign in</LinkBtn>
      <div className="doc-row">
        <Btn variant="primary" mod={['lead']}>
          <Icon name="plus" size={20} />
          Add a stay
        </Btn>
        <Btn variant="primary" mod={['icon']} aria-label="New trip">
          <Icon name="plus" size={24} bold />
        </Btn>
        <Btn variant="secondary" mod={['sm']}>
          <Icon name="plus" size={20} />
          Add to day 4
        </Btn>
        <Btn variant="text">
          Sort: Hearts
          <Icon name="chevrons-up-down" size={18} />
        </Btn>
      </div>
      <Btn variant="primary" disabled>Mark as booked</Btn>
    </div>
    </>
  )
}

export function Block_btn() {
  return (
    <section className="doc-block" id="btn">
      <h3 className="doc-h3">Button</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-btn</code>
            {' '}
            <code>--primary</code>
            {' '}
            <code>--secondary</code>
            {' '}
            <code>--text</code>
            {' '}
            <code>--icon</code>
            {' '}
            <code>--sm</code>
            {' '}
            <code>--lead</code>
            {' '}
            <code>--stub</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.1 Button, becomes "}
            <code>{"<Button>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            One primary per screen or sheet: a 48 px brand pill. Secondary is the 1.5 px edge outline, equal weight for the free path. Text and icon forms are quiet. Disabled is 50% and explains itself in nearby text.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_btn_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_btn_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_input_Demo({ s }: { s: "l" | "d" }) {
  return (
    <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <TextField label="Email" id={`in-email-${s}`} type="email" defaultValue="maya@example.com" helper="We will send a six digit code. No password needed." />
      <TextField label="Six digit code" id={`in-code-${s}`} code defaultValue="123456" error="That code is not right. Check the email we sent and try again." />
      <TextField label="Destination" id={`in-off-${s}`} disabled helper="Add a trip first." />
    </div>
  )
}

export function Block_input() {
  return (
    <section className="doc-block" id="input">
      <h3 className="doc-h3">Text input</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-input</code>
            {' '}
            <code>__label</code>
            {' '}
            <code>__field</code>
            {' '}
            <code>__help</code>
            {' '}
            <code>__error</code>
            {' '}
            <code>--error</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.2, becomes "}
            <code>{"<TextField>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>{"Label above, 44 px field, helper below. Error adds a danger icon and message and turns the border danger. Disabled is 50% and the helper says why."}</dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_input_Demo s="l" />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_input_Demo s="d" />
        </div>
      </div>
    </section>
  )
}

function Block_btn_state_Demo() {
  return (
    <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <Btn variant="primary" busy>Send code</Btn>
      <Btn variant="secondary" busy>Continue with Google</Btn>
      <Btn variant="primary" mod={['apple']}>Continue with Apple</Btn>
    </div>
  )
}

export function Block_btn_state() {
  return (
    <section className="doc-block" id="btn-state">
      <h3 className="doc-h3">Button loading and Apple</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-btn[aria-busy]</code>
            {' '}
            <code>__label</code>
            {' '}
            <code>__spin</code>
            {' '}
            <code>--apple</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.1 loading state, becomes "}
            <code>{"<Btn busy>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>{"Loading keeps the width, hides the label and shows a 16 px spinner; repeat taps are blocked. Apple follows the Human Interface Guidelines: black in light, white in dark."}</dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_btn_state_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_btn_state_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_chart_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <section className="h-chart" aria-label="Price history">
        <div className="h-chart__head">
          <h4 className="h-label h-chart__title">Price history</h4>
          <span className="h-chart__legend">
            <span className="h-chart__swatch h-chart__swatch--cached" />
            Aviasales, cached
          </span>
        </div>
        <svg className="h-chart__plot" role="img" aria-label="Aviasales fare from 19 Sep to 3 Oct. 668 dollars on 19 Sep, 654 dollars on Tuesday, 612 dollars now. Down 42 dollars since Tuesday." viewBox="0 0 334 52">
          <line className="h-chart__grid" x1="44" y1="9" x2="326" y2="9" />
          <line className="h-chart__grid" x1="44" y1="37" x2="326" y2="37" />
          <text className="h-chart__axis" x="0" y="13">$700</text>
          <text className="h-chart__axis" x="0" y="41">$600</text>
          <polyline className="h-chart__line h-chart__line--cached" points="44,18 64.1,17.4 84.3,16.8 104.4,17.7 124.6,19.1 144.7,19.9 164.9,19.6 185,20.5 205.1,20.7 225.3,21.3 245.4,21.9 265.6,25.5 285.7,28.3 305.9,30.8 326,33.6" />
          <circle className="h-chart__dot h-chart__dot--ring h-chart__dot--cached" cx="245.4" cy="21.9" r="4" />
          <circle className="h-chart__dot h-chart__dot--cached" cx="326" cy="33.6" r="4.5" />
          <text className="h-chart__callout" x="245.4" y="13.9" textAnchor="middle">Tue $654</text>
          <text className="h-chart__axis" x="44" y="50">19 Sep</text>
          <text className="h-chart__axis" x="326" y="50" textAnchor="end">3 Oct</text>
        </svg>
      </section>
    </div>
    </>
  )
}

export function Block_chart() {
  return (
    <section className="doc-block" id="chart">
      <h3 className="doc-h3">Price chart</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-chart</code>
            {' '}
            <code>__head</code>
            {' '}
            <code>__legend</code>
            {' '}
            <code>__plot</code>
            {' '}
            <code>__line</code>
            {' '}
            <code>__dot</code>
            {' '}
            <code>__callout</code>
            {' '}
            <code>--live</code>
            {' '}
            <code>--cached</code>
            {' '}
            <code>--agent</code>
            {' '}
            <code>--google</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.6 Price chart, becomes "}
            <code>{"<PriceChart>"}</code>
            {" (Recharts in the app)."}
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            A fare history. The series color follows the price source (live, cached, agent, Google), never its rank. Pair it with a text summary.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_chart_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_chart_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_timeline_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <ol className="h-timeline">
        <li className="h-timeline__row h-timeline__row--outdoors">
          <div className="h-timeline__time">
            <span className="h-timeline__clock">7:30</span>
            <span className="h-timeline__ampm">AM</span>
          </div>
          <span className="h-timeline__node" aria-hidden="true">1</span>
          <TripTicket mod={['side']}>
            <div className="h-ticket__body">
              <span className="h-timeline__title">Arenal Hanging Bridges</span>
              <span className="h-timeline__meta">
                <Icon name="mountain" size={16} />
                {"Outdoors "}
                <span className="h-timeline__dur">2 h 30 min</span>
              </span>
            </div>
            <TicketStub bare>
              <span className="h-ticket__tear" aria-hidden="true" />
              <span className="h-label">Added by</span>
              <span className="h-timeline__by h-timeline__by--t1">
                <Avatar tone="t1" size="xs" label="Ana">AN</Avatar>
                Ana
              </span>
            </TicketStub>
          </TripTicket>
        </li>
        <li className="h-timeline__row h-timeline__row--link">
          <span />
          <span className="h-timeline__spine" aria-hidden="true" />
          <span className="h-timeline__travel">
            <Icon name="car" size={16} />
            11 mi, 25 min drive
          </span>
        </li>
        <li className="h-timeline__row h-timeline__row--food">
          <div className="h-timeline__time">
            <span className="h-timeline__clock">12:30</span>
            <span className="h-timeline__ampm">PM</span>
          </div>
          <span className="h-timeline__node" aria-hidden="true">2</span>
          <TripTicket mod={['side']}>
            <div className="h-ticket__body">
              <span className="h-timeline__title">Lunch in La Fortuna</span>
              <span className="h-timeline__meta">
                <Icon name="utensils" size={16} />
                Food
              </span>
            </div>
            <TicketStub bare>
              <span className="h-ticket__tear" aria-hidden="true" />
              <span className="h-label">Added by</span>
              <span className="h-timeline__by h-timeline__by--t2">
                <Avatar tone="t2" size="xs" label="Leo">LE</Avatar>
                Leo
              </span>
            </TicketStub>
          </TripTicket>
        </li>
        <li className="h-timeline__row h-timeline__row--link-end">
          <span />
          <span className="h-timeline__spine" aria-hidden="true" />
          <span />
        </li>
        <li className="h-timeline__row h-timeline__row--add">
          <span />
          <span className="h-timeline__node h-timeline__node--open" aria-hidden="true" />
          <Btn variant="secondary" mod={['sm']}>
            <Icon name="plus" size={20} />
            Add to day 4
          </Btn>
        </li>
      </ol>
    </div>
    </>
  )
}

export function Block_timeline() {
  return (
    <section className="doc-block" id="timeline">
      <h3 className="doc-h3">Timeline</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-timeline</code>
            {' '}
            <code>__row</code>
            {' '}
            <code>__time</code>
            {' '}
            <code>__node</code>
            {' '}
            <code>__spine</code>
            {' '}
            <code>__travel</code>
            {' '}
            <code>--outdoors</code>
            {' '}
            <code>--food</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.8 Day card, becomes "}
            <code>{"<DayTimeline>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            A day as an ordered list: time, a numbered node ringed in the activity group color, and a side ticket. The twin dotted spine between rows is two repeating radial-gradients, so it ports without SVG.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_timeline_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_timeline_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_small_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <div className="doc-row doc-row--top">
        <div className="h-photo-ph" role="img" aria-label="Listing photo placeholder">
          <Icon name="image" />
          <span>Listing photo</span>
        </div>
        <p className="h-disclosure">We earn a commission if you book here. The price can change on the booking site.</p>
      </div>
      <span className="h-label">Typical weather</span>
    </div>
    </>
  )
}

export function Block_small() {
  return (
    <section className="doc-block" id="small">
      <h3 className="doc-h3">Photo placeholder, disclosure and label</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-photo-ph</code>
            {' '}
            <code>.h-disclosure</code>
            {' '}
            <code>.h-label</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>05 sections 4.9, 4.13 and 2.4 type-label.</dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Photo placeholder when a listing has no image yet. The disclosure sits directly under the actions it explains and is never truncated. The label is 11 px uppercase, set by CSS so screen readers read normal words.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_small_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_small_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_extras_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <header className="h-pagehead">
        <svg className="h-mark" width="28" height="28" aria-hidden="true" focusable="false">
          <use href="#hermi-mark" />
        </svg>
        <div className="h-pagehead__text">
          <h4 className="h-pagehead__title">Trips</h4>
          <div className="h-pagehead__meta">
            <span className="h-soft">2 of 2 active trips</span>
            <span className="h-chip">Free</span>
          </div>
        </div>
        <Btn variant="primary" mod={['icon']} aria-haspopup="menu" aria-label="New trip">
          <Icon name="plus" size={24} bold />
        </Btn>
      </header>
      <div className="h-dayhead">
        <div className="h-dayhead__col h-dayhead__col--num">
          <span className="h-label">Day</span>
          <span className="h-dayhead__num">4</span>
        </div>
        <div className="h-dayhead__col">
          <span className="h-label">Date</span>
          <span className="h-dayhead__date">Sat 28 Nov</span>
          <span className="h-dayhead__place">La Fortuna</span>
        </div>
        <div className="h-dayhead__col h-dayhead__col--grow">
          <span className="h-label">Typical weather</span>
          <span className="h-dayhead__weather">
            <Icon name="cloud-rain" />
            <span>
              <span className="h-dayhead__temp">84°F</span>
              , showers after 2 PM
            </span>
          </span>
        </div>
      </div>
      <div className="doc-row">
        <span className="h-figure">$612</span>
        <span className="h-trend h-trend--down">
          <Icon name="arrow-down" size={16} bold />
          Down $42 since Tuesday
        </span>
        <span className="h-trend h-trend--up">
          <Icon name="arrow-up" size={16} bold />
          Up $30 this week
        </span>
      </div>
    </div>
    </>
  )
}

export function Block_extras() {
  return (
    <section className="doc-block" id="extras">
      <h3 className="doc-h3">Page head, day header, fare figure and trend</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-pagehead</code>
            {' '}
            <code>.h-chip</code>
            {' '}
            <code>.h-dayhead</code>
            {' '}
            <code>.h-figure</code>
            {' '}
            <code>.h-trend--down</code>
            {' '}
            <code>.h-trend--up</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 sections 4.12, 4.5 and 6.x, become "}
            <code>{"<PageHeader>"}</code>
            {", "}
            <code>{"<DayHeader>"}</code>
            {", "}
            <code>{"<FareFigure>"}</code>
            {", "}
            <code>{"<TrendText>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Pieces the screens share. A fall in price is success, a rise is warning ink; both carry an arrow and words.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_extras_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_extras_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_stay_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <TripTicket as="article" mod={['actions']} aria-label="Casita with volcano view, Airbnb, 142 dollars a night, 568 dollars total, rating 4.9, Ana likes this">
        <div className="h-ticket__body h-ticket__body--row">
          <div className="h-photo-ph" role="img" aria-label="Listing photo placeholder">
            <Icon name="image" />
            <span>Listing photo</span>
          </div>
          <a className="h-stay__main" href="#stay" aria-label="Open Casita with volcano view">
            <h2 className="h-stay__name">Casita with volcano view</h2>
            <span className="h-stay__meta">
              <span className="h-label">Airbnb</span>
              <span className="h-stay__rating">
                <Icon name="star" size={14} />
                4.9
              </span>
            </span>
            <span className="h-soft">Price from 30 Sep</span>
          </a>
          <div className="h-stay__price">
            <span className="h-stay__night-row">
              <span className="h-stay__night">$142</span>
              <span className="h-soft">a night</span>
            </span>
            <span className="h-stay__total">$568 total</span>
            <span className="h-stay__each">$284 each</span>
          </div>
        </div>
        <TicketStub bare>
          <span className="h-ticket__tear" aria-hidden="true" />
          <span className="h-stay__count">
            <span>
              <span className="h-stay__count-n">1 of 2</span>
              {" like this"}
            </span>
            <span className="h-soft">Ana hearted it</span>
          </span>
          <div className="h-stay__votes">
            <button className="h-vote h-vote--t1" type="button" aria-pressed="true" aria-label="Ana likes Casita with volcano view">
              <Avatar tone="t1" size="sm">AN</Avatar>
              <svg className="h-vote__heart" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <use href="#i-heart" />
              </svg>
            </button>
            <button className="h-vote h-vote--t2" type="button" aria-pressed="false" aria-label="Leo has not liked Casita with volcano view">
              <Avatar tone="t2" size="sm">LE</Avatar>
              <svg className="h-vote__heart" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <use href="#i-heart" />
              </svg>
            </button>
          </div>
        </TicketStub>
      </TripTicket>
    </div>
    </>
  )
}

export function Block_stay() {
  return (
    <section className="doc-block" id="stay">
      <h3 className="doc-h3">Lodging ticket with votes</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-ticket--actions</code>
            {' '}
            <code>.h-stay__main</code>
            {' '}
            <code>.h-stay__price</code>
            {' '}
            <code>.h-stay__votes</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.10 Lodging card with votes, becomes "}
            <code>{"<StayTicket>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            A shortlisted stay: photo, name and source, price per night with total and per person, and the hearts in the stub. The summary reads hearts over travelers.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_stay_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_stay_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_scrim_Demo() {
  return (
    <>
      <div className="h-screen doc-frame doc-frame--sheet">
      <div className="h-map" role="img" aria-label="Illustrated map of La Fortuna">
        <svg className="h-map__svg" viewBox="0 0 390 194" aria-hidden="true" focusable="false">
          <rect className="h-map__ground" width="390" height="194" />
          <g transform="translate(0 -44)">
            <path className="h-map__halo" d="M-30 132C-18.3 92 15 121 40 120C65 119 95 122.3 120 126C145 129.7 168.3 135 190 142C211.7 149 226.7 162.3 250 168C273.3 173.7 301.7 176 330 176C358.3 176 403.3 137.3 420 168C436.7 198.7 505 328 430 360C355 392 46.7 398 -30 360C-106.7 322 -41.7 172 -30 132Z" />
            <path className="h-map__land h-map__land--bare" d="M-30 132C-18.3 92 15 121 40 120C65 119 95 122.3 120 126C145 129.7 168.3 135 190 142C211.7 149 226.7 162.3 250 168C273.3 173.7 301.7 176 330 176C358.3 176 403.3 137.3 420 168C436.7 198.7 505 328 430 360C355 392 46.7 398 -30 360C-106.7 322 -41.7 172 -30 132Z" />
            <ellipse className="h-map__relief" cx="288" cy="118" rx="112" ry="84" transform="rotate(-18 288 118)" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="80" ry="58" transform="rotate(-18 288 118)" fillOpacity="0.1" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="52" ry="37" transform="rotate(-18 288 118)" fillOpacity="0.14" />
            <ellipse className="h-map__relief h-map__relief--fill" cx="288" cy="118" rx="26" ry="18" transform="rotate(-18 288 118)" fillOpacity="0.2" />
            <path className="h-map__river" d="M262 146C259.3 151 253 168.3 246 176C239 183.7 228.3 185.7 220 192C211.7 198.3 207.7 208 196 214C184.3 220 164.3 221.7 150 228C135.7 234.3 116.7 248 110 252" />
            <path className="h-map__halo" d="M-20 66C-11.7 59.3 15 61.3 30 62C45 62.7 56.3 69.7 70 70C83.7 70.3 100 62.7 112 64C124 65.3 140.3 72.3 142 78C143.7 83.7 131 93.7 122 98C113 102.3 99 103.7 88 104C77 104.3 67.3 99.3 56 100C44.7 100.7 32.7 107.7 20 108C7.3 108.3 -13.3 109 -20 102C-26.7 95 -28.3 72.7 -20 66Z" />
            <path className="h-map__lake" d="M-20 66C-11.7 59.3 15 61.3 30 62C45 62.7 56.3 69.7 70 70C83.7 70.3 100 62.7 112 64C124 65.3 140.3 72.3 142 78C143.7 83.7 131 93.7 122 98C113 102.3 99 103.7 88 104C77 104.3 67.3 99.3 56 100C44.7 100.7 32.7 107.7 20 108C7.3 108.3 -13.3 109 -20 102C-26.7 95 -28.3 72.7 -20 66Z" />
            <path className="h-map__peak" d="M281 121L288 110L295 121Z" />
          </g>
        </svg>
      </div>
      <div className="h-scrim" aria-hidden="true" />
      <Sheet className="doc-top-96" role="dialog" aria-modal="true" aria-label="Sheet over a scrim">
        <SheetGrabber />
        <SheetBody>
          <h4 className="h-heading">Modal sheet</h4>
          <p className="h-soft">The screen behind is inert and under the scrim.</p>
        </SheetBody>
      </Sheet>
    </div>
    </>
  )
}

export function Block_scrim() {
  return (
    <section className="doc-block" id="scrim">
      <h3 className="doc-h3">Scrim and dimmed screen</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-dim</code>
            {' '}
            <code>.h-scrim</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 2.7 and 4.19, becomes "}
            <code>{"<Scrim>"}</code>
            {" and "}
            <code>{"<InertScreen>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            {"A modal sheet (paywall, AI actions) sits over the screen it came from. Keep that screen in a "}
            <code>.h-dim</code>
            {" wrapper with aria-hidden and inert, then a "}
            <code>.h-scrim</code>
            {" over it. The scrim token is 45% ink in light and 60% black in dark."}
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_scrim_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_scrim_Demo />
        </div>
      </div>
    </section>
  )
}

export function Block_paywall() {
  return (
    <section className="doc-block" id="paywall">
      <h3 className="doc-h3">Paywall sheet and plan options</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-sheet--paywall</code>
            {' '}
            <code>.h-sheet__head--sky</code>
            {' '}
            <code>.h-sheet__route</code>
            {' '}
            <code>.h-ticket--plan</code>
            {' '}
            <code>.h-plan__input</code>
            {' '}
            <code>.h-more</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.14 Paywall sheet, becomes "}
            <code>{"<PaywallSheet>"}</code>
            {" and "}
            <code>{"<PlanOption>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Sky head with the two routes meeting at a plane, one headline, one line of what the person gets. Offers are side-stub tickets that are radios: checked is a 2 px brand outline and a brand-soft body. Name the next offer in the More options row.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <div className="h-screen doc-frame doc-frame--paywall">
            <Sheet mod={['paywall']} className="doc-top-0" role="dialog" aria-modal="true" aria-labelledby="cpw-h-l">
              <div className="h-sheet__head h-sheet__head--sky">
                <SheetGrabber />
                <svg className="h-sheet__route" viewBox="0 0 390 62" aria-hidden="true" focusable="false">
                  <path className="h-route h-route--a h-route--lg" d="M36 50C40.2 50.3 52.4 51.7 61 51.9C69.6 52.1 79.4 52.1 87.6 51.2C95.7 50.4 102.1 48.5 110 46.8C117.9 45.1 126.7 42.9 134.7 40.9C142.7 38.8 150.2 36.5 158.1 34.5C166 32.5 178 29.9 182 29" pathLength="144" />
                  <path className="h-route h-route--b h-route--lg" d="M354 50C349.8 50.3 337.6 51.7 329 51.9C320.4 52.1 310.6 52.1 302.4 51.2C294.3 50.4 287.9 48.5 280 46.8C272.1 45.1 263.3 42.9 255.3 40.9C247.3 38.8 239.8 36.5 231.9 34.5C224 32.5 212 29.9 208 29" pathLength="144" />
                  <circle className="h-sheet__ring" cx="36" cy="50" r="9" />
                  <circle className="h-sheet__dot--a" cx="36" cy="50" r="6.5" />
                  <circle className="h-sheet__ring" cx="354" cy="50" r="9" />
                  <circle className="h-sheet__dot--b" cx="354" cy="50" r="6.5" />
                </svg>
                <span className="h-plane-disc" style={{ left: "195px", top: "41px" }}>
                  <svg viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
                    <use href="#h-plane-path" transform="rotate(0) translate(-50 -50)" />
                  </svg>
                </span>
                <h4 className="h-display" id="cpw-h-l">
                  <span className="h-display__line">Plan together.</span>
                  <span className="h-display__line">They join free.</span>
                </h4>
                <p className="h-sheet__lead">
                  {"Add up to "}
                  <span className="h-num">6</span>
                  {" people to Costa Rica. Only you pay."}
                </p>
              </div>
              <SheetBody mod={['roomy']}>
                <div className="h-stack h-stack--roomy" role="radiogroup" aria-label="Choose a plan">
                  <TripTicket as="label" mod={['side', 'plan']}>
                    <input className="h-plan__input" type="radio" name="plan-l" defaultValue="trip_pass" defaultChecked />
                    <span className="h-ticket__body">
                      <span className="h-plan__radio" aria-hidden="true">
                        <Icon name="check" size={16} heavy />
                      </span>
                      <span className="h-plan__text">
                        <span className="h-plan__name">Trip Pass</span>
                        <span className="h-plan__line">One trip, 90 days</span>
                        <span className="h-plan__line">6 people, 40 credits</span>
                        <span className="h-plan__line">Does not renew</span>
                      </span>
                    </span>
                    <TicketStub as="span" bare>
                      <span className="h-ticket__tear" aria-hidden="true" />
                      <span className="h-plan__price">$9.99</span>
                      <span className="h-plan__unit">once</span>
                    </TicketStub>
                  </TripTicket>
                  <TripTicket as="label" mod={['side', 'plan']}>
                    <input className="h-plan__input" type="radio" name="plan-l" defaultValue="plus_annual" />
                    <span className="h-ticket__body">
                      <span className="h-plan__radio" aria-hidden="true">
                        <Icon name="check" size={16} heavy />
                      </span>
                      <span className="h-plan__text">
                        <span className="h-plan__name">Plus annual</span>
                        <span className="h-plan__line">6 people, 60 credits a month</span>
                        <span className="h-plan__line">About $3.33 a month</span>
                        <span className="h-plan__line">Save $31.89 a year</span>
                      </span>
                    </span>
                    <TicketStub as="span" bare>
                      <span className="h-ticket__tear" aria-hidden="true" />
                      <span className="h-plan__price">$39.99</span>
                      <span className="h-plan__unit">a year</span>
                    </TicketStub>
                  </TripTicket>
                </div>
                <button className="h-more" type="button" aria-expanded="false">
                  <span className="h-more__label">More options</span>
                  <span className="h-more__value">
                    {"Plus monthly "}
                    <span className="h-num h-num--ink">$5.99</span>
                    {" a month"}
                    <Icon name="chevron-down" size={18} />
                  </span>
                </button>
              </SheetBody>
            </Sheet>
          </div>
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <div className="h-screen doc-frame doc-frame--paywall">
            <Sheet mod={['paywall']} className="doc-top-0" role="dialog" aria-modal="true" aria-labelledby="cpw-h-d">
              <div className="h-sheet__head h-sheet__head--sky">
                <SheetGrabber />
                <svg className="h-sheet__route" viewBox="0 0 390 62" aria-hidden="true" focusable="false">
                  <path className="h-route h-route--a h-route--lg" d="M36 50C40.2 50.3 52.4 51.7 61 51.9C69.6 52.1 79.4 52.1 87.6 51.2C95.7 50.4 102.1 48.5 110 46.8C117.9 45.1 126.7 42.9 134.7 40.9C142.7 38.8 150.2 36.5 158.1 34.5C166 32.5 178 29.9 182 29" pathLength="144" />
                  <path className="h-route h-route--b h-route--lg" d="M354 50C349.8 50.3 337.6 51.7 329 51.9C320.4 52.1 310.6 52.1 302.4 51.2C294.3 50.4 287.9 48.5 280 46.8C272.1 45.1 263.3 42.9 255.3 40.9C247.3 38.8 239.8 36.5 231.9 34.5C224 32.5 212 29.9 208 29" pathLength="144" />
                  <circle className="h-sheet__ring" cx="36" cy="50" r="9" />
                  <circle className="h-sheet__dot--a" cx="36" cy="50" r="6.5" />
                  <circle className="h-sheet__ring" cx="354" cy="50" r="9" />
                  <circle className="h-sheet__dot--b" cx="354" cy="50" r="6.5" />
                </svg>
                <span className="h-plane-disc" style={{ left: "195px", top: "41px" }}>
                  <svg viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
                    <use href="#h-plane-path" transform="rotate(0) translate(-50 -50)" />
                  </svg>
                </span>
                <h4 className="h-display" id="cpw-h-d">
                  <span className="h-display__line">Plan together.</span>
                  <span className="h-display__line">They join free.</span>
                </h4>
                <p className="h-sheet__lead">
                  {"Add up to "}
                  <span className="h-num">6</span>
                  {" people to Costa Rica. Only you pay."}
                </p>
              </div>
              <SheetBody mod={['roomy']}>
                <div className="h-stack h-stack--roomy" role="radiogroup" aria-label="Choose a plan">
                  <TripTicket as="label" mod={['side', 'plan']}>
                    <input className="h-plan__input" type="radio" name="plan-d" defaultValue="trip_pass" defaultChecked />
                    <span className="h-ticket__body">
                      <span className="h-plan__radio" aria-hidden="true">
                        <Icon name="check" size={16} heavy />
                      </span>
                      <span className="h-plan__text">
                        <span className="h-plan__name">Trip Pass</span>
                        <span className="h-plan__line">One trip, 90 days</span>
                        <span className="h-plan__line">6 people, 40 credits</span>
                        <span className="h-plan__line">Does not renew</span>
                      </span>
                    </span>
                    <TicketStub as="span" bare>
                      <span className="h-ticket__tear" aria-hidden="true" />
                      <span className="h-plan__price">$9.99</span>
                      <span className="h-plan__unit">once</span>
                    </TicketStub>
                  </TripTicket>
                  <TripTicket as="label" mod={['side', 'plan']}>
                    <input className="h-plan__input" type="radio" name="plan-d" defaultValue="plus_annual" />
                    <span className="h-ticket__body">
                      <span className="h-plan__radio" aria-hidden="true">
                        <Icon name="check" size={16} heavy />
                      </span>
                      <span className="h-plan__text">
                        <span className="h-plan__name">Plus annual</span>
                        <span className="h-plan__line">6 people, 60 credits a month</span>
                        <span className="h-plan__line">About $3.33 a month</span>
                        <span className="h-plan__line">Save $31.89 a year</span>
                      </span>
                    </span>
                    <TicketStub as="span" bare>
                      <span className="h-ticket__tear" aria-hidden="true" />
                      <span className="h-plan__price">$39.99</span>
                      <span className="h-plan__unit">a year</span>
                    </TicketStub>
                  </TripTicket>
                </div>
                <button className="h-more" type="button" aria-expanded="false">
                  <span className="h-more__label">More options</span>
                  <span className="h-more__value">
                    {"Plus monthly "}
                    <span className="h-num h-num--ink">$5.99</span>
                    {" a month"}
                    <Icon name="chevron-down" size={18} />
                  </span>
                </button>
              </SheetBody>
            </Sheet>
          </div>
        </div>
      </div>
    </section>
  )
}

function Block_paywall_actions_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad doc-stage--gap">
      <Btn variant="primary">
        {"Get Trip Pass, "}
        <span className="h-btn__price">$9.99</span>
      </Btn>
      <div className="h-btnpair">
        <Btn variant="secondary">Keep my one collaborator</Btn>
        <Btn variant="secondary">Not now</Btn>
      </div>
      <p className="h-disclosure h-disclosure--legal">
        {"Trip Pass is "}
        <span className="h-num h-num--ink">$9.99</span>
        {" once, for Costa Rica. It lasts 90 days from the day you apply it and does not renew. Plus renews until you cancel in Settings."}
      </p>
      <div className="h-linkrow">
        <a className="h-linkrow__item" href="#billing">How billing works</a>
        <a className="h-linkrow__item" href="#terms">Terms</a>
        <a className="h-linkrow__item" href="#privacy">Privacy</a>
        <button className="h-linkrow__item" type="button">Restore purchases</button>
      </div>
    </div>
    </>
  )
}

export function Block_paywall_actions() {
  return (
    <section className="doc-block" id="paywall-actions">
      <h3 className="doc-h3">Paywall actions</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-btn__price</code>
            {' '}
            <code>.h-btnpair</code>
            {' '}
            <code>.h-disclosure--legal</code>
            {' '}
            <code>.h-linkrow</code>
            {' '}
            <code>__item</code>
            {' '}
            <code>.h-num</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.14 and 8, becomes "}
            <code>{"<PaywallActions>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            One primary purchase button with the price in mono. "Not now" and the free route are real buttons of the same size. The legal line states the price, the term and how to cancel; links sit below with 44 pt targets.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_paywall_actions_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_paywall_actions_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_ai_sheet_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <div className="h-sheet__bar doc-bar-flush">
        <div className="h-sheet__bar-text">
          <h4 className="h-sheet__title">Plan with AI</h4>
          <span className="h-sheet__sub">AI is on for Costa Rica</span>
        </div>
        <a className="h-sheet__balance" href="#credits" aria-label="Balance, 12 credits left">
          <span className="h-credit h-credit--lg">
            <Icon name="coins" size={14} />
            <span className="h-credit__n">12</span>
            {" credits left"}
          </span>
        </a>
      </div>
      <div className="h-actionlist doc-list-flush" role="group" aria-label="AI actions, each with its credit cost">
        <button className="h-action" type="button" aria-pressed="false" aria-label="Draft this day, costs 1 credit">
          <span className="h-action__text">
            <span className="h-action__title">Draft this day</span>
            <span className="h-action__desc">Sat 28 Nov, from your places</span>
          </span>
          <span className="h-action__side">
            <span className="h-credit">
              <Icon name="coins" size={14} />
              <span className="h-credit__n">1</span>
              {" credit"}
            </span>
          </span>
        </button>
        <button className="h-action" type="button" aria-pressed="true" aria-label="Research a question, costs 8 credits. Selected">
          <span className="h-action__text">
            <span className="h-action__title">Research a question</span>
            <span className="h-action__desc">“Where to go if it rains after 2 PM?”</span>
          </span>
          <span className="h-action__side">
            <span className="h-credit">
              <Icon name="coins" size={14} />
              <span className="h-credit__n">8</span>
              {" credits"}
            </span>
          </span>
        </button>
        <button className="h-action" type="button" aria-pressed="false" aria-label="Deep agent run, costs 40 credits. You have 12">
          <span className="h-action__text">
            <span className="h-action__title">Deep agent run</span>
            <span className="h-action__desc h-action__desc--cache">8 credits from shared cache</span>
          </span>
          <span className="h-action__side">
            <span className="h-credit h-credit--warn">
              <Icon name="coins" size={14} />
              <span className="h-credit__n">40</span>
              {" credits"}
            </span>
            <span className="h-action__note">You have 12</span>
          </span>
        </button>
        <button className="h-action" type="button" aria-pressed="false" aria-label="Explain, costs 1 credit">
          <span className="h-action__text">
            <span className="h-action__title">Explain</span>
            <span className="h-action__desc">Short answer about a place or plan</span>
          </span>
          <span className="h-action__side">
            <span className="h-credit">
              <Icon name="coins" size={14} />
              <span className="h-credit__n">1</span>
              {" credit"}
            </span>
          </span>
        </button>
      </div>
    </div>
    </>
  )
}

export function Block_ai_sheet() {
  return (
    <section className="doc-block" id="ai-sheet">
      <h3 className="doc-h3">AI actions list</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-sheet--ai</code>
            {' '}
            <code>.h-sheet__bar</code>
            {' '}
            <code>.h-actionlist</code>
            {' '}
            <code>.h-action</code>
            {' '}
            <code>__title</code>
            {' '}
            <code>__desc</code>
            {' '}
            <code>__desc--cache</code>
            {' '}
            <code>__note</code>
            {' '}
            <code>.h-credit--warn</code>
            {' '}
            <code>.h-credit--lg</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.11 Credit cost chip and 6.x AI sheet, becomes "}
            <code>{"<AiSheet>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Each row names the action and shows its cost chip. One row is selected (aria-pressed). A cost the person cannot cover uses the warning chip and says what they have. A cached result says so in success green.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_ai_sheet_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_ai_sheet_Demo />
        </div>
      </div>
    </section>
  )
}

export function Block_confirm() {
  return (
    <section className="doc-block" id="confirm">
      <h3 className="doc-h3">Spend confirmation</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-confirm</code>
            {' '}
            <code>__title</code>
            {' '}
            <code>__text</code>
            {' '}
            <code>__actions</code>
            {' '}
            <code>.h-btn--spend</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.11, becomes "}
            <code>{"<ConfirmStub>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            Required at 6 credits or more, never auto-confirmed. Say the cost and what is left, then the spend button with the cost inside it, beside Cancel. It is pinned to the bottom of the sheet; the 34 px under the buttons is the home indicator.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <div className="h-screen doc-frame doc-frame--confirm">
            <Sheet className="doc-top-0">
              <div className="h-confirm" role="group" aria-labelledby="ccf-h-l">
                <h4 className="h-confirm__title" id="ccf-h-l">Research this question?</h4>
                <p className="h-confirm__text">
                  {"Costs "}
                  <span className="h-num">8</span>
                  {" credits. You have "}
                  <span className="h-num">12</span>
                  {", so "}
                  <span className="h-num">4</span>
                  {" left."}
                </p>
                <div className="h-confirm__actions">
                  <Btn variant="primary" mod={['spend']} aria-label="Start research, costs 8 credits">
                    Start research
                    <span className="h-credit">
                      <Icon name="coins" size={14} />
                      <span className="h-credit__n">8</span>
                      {" credits"}
                    </span>
                  </Btn>
                  <Btn variant="secondary">Cancel</Btn>
                </div>
              </div>
            </Sheet>
          </div>
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <div className="h-screen doc-frame doc-frame--confirm">
            <Sheet className="doc-top-0">
              <div className="h-confirm" role="group" aria-labelledby="ccf-h-d">
                <h4 className="h-confirm__title" id="ccf-h-d">Research this question?</h4>
                <p className="h-confirm__text">
                  {"Costs "}
                  <span className="h-num">8</span>
                  {" credits. You have "}
                  <span className="h-num">12</span>
                  {", so "}
                  <span className="h-num">4</span>
                  {" left."}
                </p>
                <div className="h-confirm__actions">
                  <Btn variant="primary" mod={['spend']} aria-label="Start research, costs 8 credits">
                    Start research
                    <span className="h-credit">
                      <Icon name="coins" size={14} />
                      <span className="h-credit__n">8</span>
                      {" credits"}
                    </span>
                  </Btn>
                  <Btn variant="secondary">Cancel</Btn>
                </div>
              </div>
            </Sheet>
          </div>
        </div>
      </div>
    </section>
  )
}

function Block_run_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <TripTicket mod={['sky', 'run']} role="group" aria-label="Run outcome: done">
        <div className="h-ticket__head h-ticket__head--sky">
          <span className="h-label h-label--onsky">Agent run</span>
          <h4 className="h-ticket__name">Draft day 4 in La Fortuna</h4>
          <dl className="h-ticket__fields h-ticket__fields--run">
            <Field label="Elapsed">00:58</Field>
            <Field label="Credits used">8</Field>
            <Field label="Credits left">4</Field>
          </dl>
        </div>
        <div className="h-run">
          <svg className="h-run__route" viewBox="0 0 326 30" aria-hidden="true" focusable="false">
            <g className="h-run__dots">
              <circle className="h-run__dot" cx="44.6" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="54.7" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="64.7" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="74.8" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="84.8" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="110.8" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="120.6" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="130.4" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="140.2" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="150" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="176" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="185.8" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="195.6" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="205.4" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="215.2" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="241.2" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="253.9" cy="15" r="2.6" />
              <circle className="h-run__dot" cx="266.7" cy="15" r="2.6" />
            </g>
            <g transform="translate(32.6 15)">
              <circle className="h-run__stop-ring" r="10.5" />
              <circle className="h-run__stop-core" r="8.5" />
              <path className="h-run__stop-check" d="M-3.6 .2L-1 2.8L3.8 -2.6" />
            </g>
            <g transform="translate(97.8 15)">
              <circle className="h-run__stop-ring" r="10.5" />
              <circle className="h-run__stop-core" r="8.5" />
              <path className="h-run__stop-check" d="M-3.6 .2L-1 2.8L3.8 -2.6" />
            </g>
            <g transform="translate(163 15)">
              <circle className="h-run__stop-ring" r="10.5" />
              <circle className="h-run__stop-core" r="8.5" />
              <path className="h-run__stop-check" d="M-3.6 .2L-1 2.8L3.8 -2.6" />
            </g>
            <g transform="translate(228.2 15)">
              <circle className="h-run__stop-ring" r="10.5" />
              <circle className="h-run__stop-core" r="8.5" />
              <path className="h-run__stop-check" d="M-3.6 .2L-1 2.8L3.8 -2.6" />
            </g>
            <g transform="translate(293.4 15)">
              <g className="h-run__plane">
                <circle className="h-run__plane-ring" r="15" />
                <circle className="h-run__plane-core" r="12.5" />
                <use className="h-run__plane-glyph" href="#h-plane-path" transform="rotate(90) scale(.205) translate(-50 -50)" />
              </g>
            </g>
          </svg>
          <ol className="h-run__steps" aria-label="Steps of this run, all finished">
            <li className="h-run__step" aria-label="Searching, 00:12">
              <span>Searching</span>
              <span className="h-run__time">00:12</span>
            </li>
            <li className="h-run__step" aria-label="Reading a page, 00:31">
              <span>Reading</span>
              <span className="h-run__time">00:31</span>
            </li>
            <li className="h-run__step" aria-label="Checking a source, 00:44">
              <span>Checking</span>
              <span className="h-run__time">00:44</span>
            </li>
            <li className="h-run__step" aria-label="Saving a finding, 00:52">
              <span>Saving</span>
              <span className="h-run__time">00:52</span>
            </li>
            <li className="h-run__step" aria-label="Done, 00:58">
              <span>Done</span>
              <span className="h-run__time">00:58</span>
            </li>
          </ol>
        </div>
        <TicketStub>
          <span className="h-touchdown">
            <StatusStub status="done">Done</StatusStub>
          </span>
          <span className="h-ticket__note h-ticket__note--stack">
            <strong>2 notes found</strong>
            <span className="h-soft">
              <span className="h-num h-num--ink">8</span>
              {" credits used from shared cache"}
            </span>
          </span>
        </TicketStub>
      </TripTicket>
    </div>
    </>
  )
}

export function Block_run() {
  return (
    <section className="doc-block" id="run">
      <h3 className="doc-h3">Run outcome ticket</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-ticket--run</code>
            {' '}
            <code>.h-run</code>
            {' '}
            <code>__route</code>
            {' '}
            <code>__dot</code>
            {' '}
            <code>__stop-core</code>
            {' '}
            <code>__plane</code>
            {' '}
            <code>__steps</code>
            {' '}
            <code>.h-touchdown</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.21 Progress and run timeline and Ticket stub, becomes "}
            <code>{"<RunTicket>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            The result of an agent run. Steps are dots on a route, each finished step a check, the plane landed at the end; the stub lands with touchdown. Under reduced motion it renders in its final state.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_run_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_run_Demo />
        </div>
      </div>
    </section>
  )
}

function Block_evidence_Demo() {
  return (
    <>
      <div className="doc-stage doc-stage--sheet doc-stage--pad">
      <TripTicket mod={['evidence']} role="group" aria-label="Note found: showers build after 2 PM, cr-weather.org">
        <div className="h-ticket__body">
          <div className="h-evidence__top">
            <h3 className="h-evidence__title">Showers build after 2 PM</h3>
            <span className="h-label h-evidence__kind">Note</span>
          </div>
          <span className="h-evidence__source">
            <span className="h-evidence__icon" aria-hidden="true">
              <Icon name="globe" size={12} />
            </span>
            La Fortuna weather by month
          </span>
          <a className="h-evidence__link" href="#source">Found on cr-weather.org, checked 3 Oct</a>
          <span className="h-evidence__quote">“Mornings are clearer. Showers build after 2 PM.”</span>
        </div>
        <TicketStub bare>
          <span className="h-ticket__tear" aria-hidden="true" />
          <a className="h-ticket__action" href="#source" aria-label="Open source, showers build after 2 PM, cr-weather.org, opens in a browser">
            Open source
            <Icon name="external-link" size={14} />
          </a>
          <button className="h-ticket__action h-ticket__action--brand" type="button">Save to trip</button>
          <button className="h-ticket__action h-ticket__action--soft" type="button">Dismiss</button>
        </TicketStub>
      </TripTicket>
    </div>
    </>
  )
}

export function Block_evidence() {
  return (
    <section className="doc-block" id="evidence">
      <h3 className="doc-h3">Evidence ticket</h3>
      <dl className="doc-meta">
        <div>
          <dt>Classes</dt>
          <dd>
            <code>.h-ticket--evidence</code>
            {' '}
            <code>.h-evidence__title</code>
            {' '}
            <code>__source</code>
            {' '}
            <code>__link</code>
            {' '}
            <code>__quote</code>
            {' '}
            <code>.h-ticket__action</code>
          </dd>
        </div>
        <div>
          <dt>Spec</dt>
          <dd>
            {"05 section 4.21 Evidence label and Evidence row, becomes "}
            <code>{"<EvidenceTicket>"}</code>
            .
          </dd>
        </div>
        <div>
          <dt>Use</dt>
          <dd>
            One fact an agent found, with the page it came from and the date it was checked. The whole source line is a link. The stub holds three choices: open the source, save it to the trip, dismiss it.
          </dd>
        </div>
      </dl>
      <div className="doc-pair">
        <div className="doc-demo light" data-mode="light">
          <span className="doc-demo__tag">Light</span>
          <Block_evidence_Demo />
        </div>
        <div className="doc-demo dark" data-mode="dark">
          <span className="doc-demo__tag">Dark</span>
          <Block_evidence_Demo />
        </div>
      </div>
    </section>
  )
}

export const BLOCKS = [
  { id: "screen", Block: Block_screen },
  { id: "map", Block: Block_map },
  { id: "map-shapes", Block: Block_map_shapes },
  { id: "markers", Block: Block_markers },
  { id: "routes", Block: Block_routes },
  { id: "sheet", Block: Block_sheet },
  { id: "navbtn", Block: Block_navbtn },
  { id: "tabbar", Block: Block_tabbar },
  { id: "strip", Block: Block_strip },
  { id: "seg", Block: Block_seg },
  { id: "daychip", Block: Block_daychip },
  { id: "ticket", Block: Block_ticket },
  { id: "ticket-cta", Block: Block_ticket_cta },
  { id: "ticket-side", Block: Block_ticket_side },
  { id: "stub", Block: Block_stub },
  { id: "field", Block: Block_field },
  { id: "codes", Block: Block_codes },
  { id: "avatar", Block: Block_avatar },
  { id: "vote", Block: Block_vote },
  { id: "tile", Block: Block_tile },
  { id: "listcard", Block: Block_listcard },
  { id: "ai", Block: Block_ai },
  { id: "btn", Block: Block_btn },
  { id: "input", Block: Block_input },
  { id: "btn-state", Block: Block_btn_state },
  { id: "chart", Block: Block_chart },
  { id: "timeline", Block: Block_timeline },
  { id: "small", Block: Block_small },
  { id: "extras", Block: Block_extras },
  { id: "stay", Block: Block_stay },
  { id: "scrim", Block: Block_scrim },
  { id: "paywall", Block: Block_paywall },
  { id: "paywall-actions", Block: Block_paywall_actions },
  { id: "ai-sheet", Block: Block_ai_sheet },
  { id: "confirm", Block: Block_confirm },
  { id: "run", Block: Block_run },
  { id: "evidence", Block: Block_evidence },
]
