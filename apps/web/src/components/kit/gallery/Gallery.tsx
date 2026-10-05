import { useLayoutEffect } from 'react'
import { Sprite } from '../Sprite'
import { BLOCKS } from './blocks'
import { SheetChrome } from './SheetChrome'
import './gallery.css'

/**
 * Every component block of design/components.html, rendered from the React kit components. Dev and test only:
 * it is served from kit-gallery.html (not an input of the production build) and e2e/kit compares it with the kit page.
 * `#dark` in the URL puts the page in dark mode, as it does on the kit sheet.
 */
export function Gallery() {
  useLayoutEffect(() => {
    document.documentElement.classList.toggle('dark', window.location.hash === '#dark')
  }, [])
  return (
    <>
      <Sprite />
      <SheetChrome />
      {/* shortcut: a hand-tuned 0.28125 px offset matches the kit sheet as it is today; if the sections above the blocks on
          components.html change height, re-measure #screen's y fraction (kit.spec/parity fails with 1 px size diffs) and update it.
          Element screenshots round by the block's fractional y offset. The kit sheet has #screen at a y ending in .78125 (the
          sections above it add up that way); this sub-pixel padding gives the gallery the same fraction, so the pixel sizes match. */}
      <main className="doc" style={{ paddingTop: '0.28125px' }}>
        <section className="doc-section" id="components">
          {BLOCKS.map(({ id, Block }) => (
            <Block key={id} />
          ))}
        </section>
      </main>
    </>
  )
}
