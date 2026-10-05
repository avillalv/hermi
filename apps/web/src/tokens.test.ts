import { describe, expect, it } from 'vitest'
import spec from '../../../app-buildout/phase-1-launch/05-ui-ux-spec.md?raw'
import kitCss from '../../../app-buildout/phase-1-launch/design/tokens.css?raw'
import tokensCss from '../../../packages/tokens/tokens.css?raw'

/** The text of spec section 2.1 up to the start of 2.4. */
const section = spec.slice(spec.indexOf('### 2.1 '), spec.indexOf('### 2.4 '))
const rows = section
  .split('\n')
  .filter((l) => l.startsWith('|'))
  .map((l) => l.split('|').slice(1, -1).map((c) => c.trim()))

const HEX = /^`(#[0-9A-Fa-f]{6})`$/
type Mode = 'light' | 'dark'

/** Token rows of 2.1 and 2.2: name in backticks first, two hex cells next. */
const specTokens: Record<string, Record<Mode, string>> = {}
for (const [first, light, dark] of rows) {
  const name = first?.match(/^`(--[a-z0-9-]+)`/)?.[1]
  if (name && HEX.test(light ?? '') && HEX.test(dark ?? '')) {
    specTokens[name] = { light: light.match(HEX)![1].toLowerCase(), dark: dark.match(HEX)![1].toLowerCase() }
  }
}

/** Declarations of a top-level CSS block whose header matches. */
function block(css: string, header: RegExp, mustHave: string): Record<string, string> {
  const clean = css.replace(/\/\*[\s\S]*?\*\//g, '')
  for (const m of clean.matchAll(/^([^{}\n][^{}]*)\{([^{}]*)\}/gm)) {
    if (header.test(m[1].trim()) && m[2].includes(mustHave)) {
      const out: Record<string, string> = {}
      for (const d of m[2].matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)) out[d[1]] = d[2].trim().toLowerCase()
      return out
    }
  }
  throw new Error(`block ${header} not found`)
}

const css = {
  light: block(tokensCss, /\.light\s*$/, '--tp-paper'),
  dark: block(tokensCss, /^\.dark$/, '--tp-paper'),
}

describe('tokens.css', () => {
  it('is an exact copy of design/tokens.css', () => {
    expect(tokensCss).toBe(kitCss)
  })

  it('parses the spec tables', () => {
    expect(Object.keys(specTokens).length).toBeGreaterThanOrEqual(61)
    for (const n of ['--tp-edge', '--tp-warning-ink', '--tp-sky', '--tp-route-a-ink', '--tp-ticket', '--viz-band']) {
      expect(specTokens[n], n).toBeDefined()
    }
  })

  for (const mode of ['light', 'dark'] as const) {
    it(`matches 05 section 2.1 to 2.2 in ${mode} mode`, () => {
      for (const [name, v] of Object.entries(specTokens)) {
        expect(css[mode][name], `${name} (${mode})`).toBe(v[mode])
      }
    })
  }

  it('applies the same dark values under prefers-color-scheme', () => {
    const media = tokensCss.slice(tokensCss.indexOf('@media (prefers-color-scheme: dark)'))
    for (const [name, v] of Object.entries(specTokens)) {
      expect(media.toLowerCase(), name).toContain(`${name}:`)
      const re = new RegExp(`${name}:\\s*${v.dark}`)
      expect(media.toLowerCase(), name).toMatch(re)
    }
  })

  it('keeps the aliases equal', () => {
    for (const mode of ['light', 'dark'] as const) {
      expect(css[mode]['--tp-ticket']).toBe(css[mode]['--tp-paper'])
      expect(css[mode]['--viz-band']).toBe(css[mode]['--tp-brand-soft'])
    }
  })
})

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

/** Each contrast row: the foreground and background token. */
const PAIRS: Record<string, [string, string]> = {
  'Ink on paper': ['--tp-ink', '--tp-paper'],
  'Ink on card': ['--tp-ink', '--tp-sheet'],
  'Soft ink on paper': ['--tp-ink-soft', '--tp-paper'],
  'Soft ink on card': ['--tp-ink-soft', '--tp-sheet'],
  'Brand on card (links, text buttons)': ['--tp-brand', '--tp-sheet'],
  'Brand ink on brand (primary button label)': ['--tp-brand-ink', '--tp-brand'],
  'Success on card': ['--tp-success', '--tp-sheet'],
  'Warning on card': ['--tp-warning', '--tp-sheet'],
  'Warning ink on card': ['--tp-warning-ink', '--tp-sheet'],
  'Danger on card': ['--tp-danger', '--tp-sheet'],
  'Sky ink on sky': ['--tp-sky-ink', '--tp-sky'],
  'Sky soft on sky': ['--tp-sky-soft', '--tp-sky'],
  'Sky ink on sky raised (active row)': ['--tp-sky-ink', '--tp-sky-raised'],
  'Route A ink on card': ['--tp-route-a-ink', '--tp-sheet'],
  'Route B ink on card': ['--tp-route-b-ink', '--tp-sheet'],
  '`--tp-edge` on card (control borders)': ['--tp-edge', '--tp-sheet'],
  '`--tp-edge` on paper': ['--tp-edge', '--tp-paper'],
  'Ink on sunken (ticket stubs, chips)': ['--tp-ink', '--tp-sunken'],
  'Soft ink on sunken': ['--tp-ink-soft', '--tp-sunken'],
  'Success on sunken': ['--tp-success', '--tp-sunken'],
  'Brand on sunken': ['--tp-brand', '--tp-sunken'],
  'Route A ink on sunken (the "Added by" name on a stub)': ['--tp-route-a-ink', '--tp-sunken'],
  'Route B ink on sunken': ['--tp-route-b-ink', '--tp-sunken'],
  '`--tp-edge` on sunken (control borders on a stub)': ['--tp-edge', '--tp-sunken'],
  ...Object.fromEntries(
    [1, 2, 3, 4, 5].map((n) => [`\`--heat-ink-${n}\` on \`--heat-${n}\``, [`--heat-ink-${n}`, `--heat-${n}`]]),
  ),
}

const contrastStart = spec.indexOf('### 2.3 ')
const contrastRows = spec
  .slice(contrastStart, spec.indexOf('### 2.4 '))
  .split('\n')
  .filter((l) => l.startsWith('|'))
  .map((l) => l.split('|').slice(1, -1).map((c) => c.trim()))
  .filter(([pair, light]) => pair && light && /^[\d.]+/.test(light))

describe('2.3 measured contrast', () => {
  it('lists every row we can recompute', () => {
    const names = contrastRows.map(([pair]) => pair)
    expect(names.length).toBe(30)
    for (const n of names) {
      expect(PAIRS[n] ?? n.startsWith('Traveler initials'), n).toBeTruthy()
    }
  })

  for (const [pair, light, dark] of contrastRows) {
    it(`${pair}`, () => {
      const cells: Record<Mode, number> = { light: parseFloat(light), dark: parseFloat(dark) }
      for (const mode of ['light', 'dark'] as const) {
        const colors = (n: string) => css[mode][n]
        const computed = pair.startsWith('Traveler initials')
          ? Math.min(...[1, 2, 3, 4, 5, 6, 7, 8].map((i) => ratio(colors(`--tp-traveler-ink-${i}`), colors(`--tp-traveler-${i}`))))
          : ratio(colors(PAIRS[pair][0]), colors(PAIRS[pair][1]))
        expect(Math.abs(computed - cells[mode]), `${pair} ${mode}: ${computed.toFixed(3)} vs ${cells[mode]}`).toBeLessThanOrEqual(0.011)
      }
    })
  }
})

describe('2.3 contrast floors (WCAG 2.x)', () => {
  // Body text 4.5 to 1, UI boundaries 3 to 1. "Warning on card" is large text only in light mode (4.36), so it is held to 3.
  const floor = (pair: string, mode: Mode) =>
    pair.includes('--tp-edge') ? 3 : pair === 'Warning on card' && mode === 'light' ? 3 : 4.5
  for (const mode of ['light', 'dark'] as const) {
    it(`every 2.3 pair meets its floor in ${mode} mode`, () => {
      for (const [pair] of contrastRows) {
        const r = pair.startsWith('Traveler initials')
          ? Math.min(...[1, 2, 3, 4, 5, 6, 7, 8].map((i) => ratio(css[mode][`--tp-traveler-ink-${i}`], css[mode][`--tp-traveler-${i}`])))
          : ratio(css[mode][PAIRS[pair][0]], css[mode][PAIRS[pair][1]])
        expect(r, `${pair} ${mode}: ${r.toFixed(2)}`).toBeGreaterThanOrEqual(floor(pair, mode))
      }
    })
  }

  it('small warning text, control borders and the sky surface use the pairs that pass', () => {
    for (const mode of ['light', 'dark'] as const) {
      expect(ratio(css[mode]['--tp-warning-ink'], css[mode]['--tp-sheet'])).toBeGreaterThanOrEqual(4.5)
      expect(ratio(css[mode]['--tp-edge'], css[mode]['--tp-sheet'])).toBeGreaterThanOrEqual(3)
      expect(ratio(css[mode]['--tp-sky-ink'], css[mode]['--tp-sky'])).toBeGreaterThanOrEqual(4.5)
    }
  })
})
