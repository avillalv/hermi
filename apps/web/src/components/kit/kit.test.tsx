import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import kitCss from '../../../../../app-buildout/phase-1-launch/design/hermi.css?raw'
import hermiCss from '../../../../../packages/tokens/hermi.css?raw'
import pkg from '../../../../../packages/tokens/package.json'
import logo from '../../../../../app-buildout/brand/hermi-logo.svg?raw'
import logoDark from '../../../../../app-buildout/brand/hermi-logo-dark.svg?raw'
import transparent from '../../../../../app-buildout/brand/hermi-logo-transparent.svg?raw'
import transparentDark from '../../../../../app-buildout/brand/hermi-logo-dark-transparent.svg?raw'
import { Logo } from './Logo'
import { RoutePath, RoutePattern } from './RoutePattern'

describe('hermi.css', () => {
  it('is an exact copy of design/hermi.css', () => expect(hermiCss).toBe(kitCss))
  it('is exported from the tokens package', () => expect(pkg.exports['./hermi.css']).toBe('./hermi.css'))
  it('makes no external requests', () => expect(hermiCss).not.toMatch(/https?:\/\/|googleapis|gstatic/))
})

describe('Logo', () => {
  it('has the accessible name Hermi in every variant', () => {
    for (const variant of ['mark', 'wordmark', 'lockup'] as const) {
      const { unmount } = render(<Logo variant={variant} />)
      expect(screen.getByRole('img', { name: 'Hermi' })).toBeTruthy()
      unmount()
    }
  })
  it('swaps the wordmark and lockup in dark mode, not the mark', () => {
    const src = (v: 'mark' | 'wordmark' | 'lockup', mode: 'light' | 'dark') => {
      const { unmount, container } = render(<Logo variant={v} mode={mode} />)
      const s = container.querySelector('img')!.getAttribute('src')
      unmount()
      return s
    }
    expect(src('mark', 'dark')).toBe(src('mark', 'light'))
    expect(src('wordmark', 'dark')).not.toBe(src('wordmark', 'light'))
    expect(src('lockup', 'dark')).not.toBe(src('lockup', 'light'))
  })
})

describe('transparent lockups', () => {
  it('have no full-canvas background rect and differ from the opaque ones', () => {
    for (const [t, o] of [[transparent, logo], [transparentDark, logoDark]]) {
      expect(t).not.toContain('<rect width="1474"')
      expect(o).toContain('<rect width="1474"')
      expect(t).not.toBe(o)
    }
  })
})

describe('RoutePattern', () => {
  it('draws the twin routes with the kit classes', () => {
    const { container } = render(<RoutePattern a="M0 0L10 10" b="M0 5L10 15" viewBox="0 0 10 20" />)
    expect(container.querySelector('svg')!.getAttribute('aria-hidden')).toBe('true')
    expect(container.querySelectorAll('path.h-route--a')).toHaveLength(1)
    expect(container.querySelectorAll('path.h-route--b')).toHaveLength(1)
  })
  it('is named when given a title, and takes a size', () => {
    render(<RoutePattern a="M0 0" b="M0 1" viewBox="0 0 1 1" title="Routes" size="sm" />)
    expect(screen.getByRole('img', { name: 'Routes' })).toBeTruthy()
    const { container } = render(<RoutePath d="M0 0" traveler="a" size="lg" />)
    expect(container.querySelector('path')!.getAttribute('class')).toBe('h-route h-route--a h-route--lg')
  })
})

const publicFiles = Object.keys(import.meta.glob('../../../public/*.{svg,png}', { query: '?url' }))

describe('web icons', () => {
  it('exist and are linked from index.html', async () => {
    const html = (await import('../../../index.html?raw')).default
    for (const f of ['favicon.svg', 'favicon-32.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png']) {
      expect(publicFiles, f).toContain(`../../../public/${f}`)
    }
    for (const f of ['favicon.svg', 'favicon-32.png', 'apple-touch-icon.png']) expect(html).toContain(`/${f}`)
  })
})
