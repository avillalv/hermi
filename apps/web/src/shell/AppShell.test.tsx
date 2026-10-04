import { fireEvent, render, screen, within } from '@testing-library/react'

import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router'
import { AppRoutes } from './routes'
import { AppShell } from './AppShell'

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
    expect(within(nav).getByRole('link', { name: 'Activity' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Trips' })).not.toHaveAttribute('aria-current')
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
