import { fireEvent, render, screen, within } from '@testing-library/react'

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authStore } from '../routes/auth/authStore'
import { MemoryRouter } from 'react-router'
import { AppRoutes } from './routes'
import { AppShell } from './AppShell'

// The Trips tab needs a session; the list call is stubbed.
beforeEach(() => {
  vi.stubGlobal('fetch', async () => Response.json({ items: [], next_cursor: null, has_more: false }))
  authStore.signIn('tok', 'free')
})

const at = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )

describe('shell routing', () => {
  it('renders Trips at /', () => {
    at('/')
    expect(screen.getByRole('heading', { level: 1, name: 'Trips' })).toBeInTheDocument()
  })
  it('keeps the click for the browser when a modifier key is held', () => {
    at('/')
    const link = within(screen.getByRole('navigation', { name: 'Tabs' })).getByRole('link', { name: 'Account' })
    expect(fireEvent.click(link, { ctrlKey: true })).toBe(true)
    expect(screen.getByRole('heading', { level: 1, name: 'Trips' })).toBeInTheDocument()
  })
  it.each(['Trips', 'Discover', 'Activity', 'Account'])('renders the %s placeholder inside the shell', (name) => {
    at(name === 'Trips' ? '/' : `/${name.toLowerCase()}`)
    expect(screen.getByRole('heading', { level: 1, name })).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
  })
})

describe('shell nav', () => {
  it('has the four tabs in order in the tab bar, the rail and the sidebar nav', () => {
    at('/')
    const nav = screen.getByRole('navigation', { name: 'Main' })
    expect(within(nav).getAllByRole('link').map((a) => a.textContent)).toEqual(['Trips', 'Discover', 'Activity', 'Account'])
    const tabs = screen.getByRole('navigation', { name: 'Tabs' })
    expect(within(tabs).getAllByRole('link').map((a) => a.textContent)).toEqual(['Trips', 'Discover', 'Activity', 'Account'])
  })
  it('marks only the active item with aria-current=page and follows a click', () => {
    at('/')
    const nav = screen.getByRole('navigation', { name: 'Main' })
    expect(within(nav).getByRole('link', { name: 'Trips' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Discover' })).not.toHaveAttribute('aria-current')
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Tabs' })).getByRole('link', { name: 'Activity' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Activity' })).toBeInTheDocument()
    // Trips and Activity are different screens, so the shell remounts: read the nav again.
    const after = screen.getByRole('navigation', { name: 'Main' })
    expect(within(after).getByRole('link', { name: 'Activity' })).toHaveAttribute('aria-current', 'page')
    expect(within(after).getByRole('link', { name: 'Trips' })).not.toHaveAttribute('aria-current')
  })
  it('renders a sticky strip nav with aria-current when given strip items', () => {
    render(
      <MemoryRouter>
        <AppShell active="trips" strip={{ label: 'Sections', active: 'b', items: [{ key: 'a', label: 'A', href: '#a' }, { key: 'b', label: 'B', href: '#b' }] }}>
          <p>x</p>
        </AppShell>
      </MemoryRouter>,
    )
    const strip = screen.getByRole('navigation', { name: 'Sections' })
    expect(strip.className).toContain('shell-strip')
    expect(within(strip).getByRole('link', { name: 'B' })).toHaveAttribute('aria-current', 'page')
  })
})

describe('trip switcher', () => {
  it('lists the five most recent trips and All trips in the sidebar, and marks the open one', async () => {
    const items = Array.from({ length: 7 }, (_, i) => ({ id: `t${i}`, name: `Trip ${i}`, status: 'planning', start_date: null, end_date: null, destinations_label: '', member_count: 1, my_role: 'owner' }))
    vi.stubGlobal('fetch', async (u: string) => (String(u).endsWith('/v1/trips') ? Response.json({ items, next_cursor: null, has_more: false }) : new Response('{}', { status: 404 })))
    vi.stubGlobal('matchMedia', (q: string) => ({ matches: true, media: q, addEventListener() {}, removeEventListener() {} }))
    at('/trips/t1')
    const nav = await screen.findByRole('navigation', { name: 'Trip switcher' })
    expect(within(nav).getAllByRole('link')).toHaveLength(6)
    expect(within(nav).getByRole('link', { name: 'All trips' })).toHaveAttribute('href', '/')
    expect(within(nav).getByRole('link', { name: 'Trip 1' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).queryByText('Trip 5')).not.toBeInTheDocument()
  })
})
