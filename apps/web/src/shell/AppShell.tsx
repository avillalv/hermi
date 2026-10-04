import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'
import { Icon, Logo, SectionTabs, Sprite, TabBar, cx, type SectionTab, type TabItem } from '../components/kit'
import './shell.css'

export const TABS = [
  { key: 'trips', label: 'Trips', icon: 'luggage', href: '/' },
  { key: 'discover', label: 'Discover', icon: 'compass', href: '/discover' },
  { key: 'activity', label: 'Activity', icon: 'bell', href: '/activity' },
  { key: 'account', label: 'Account', icon: 'circle-user', href: '/account' },
] as const

export type Strip = { label: string; active: string; items: SectionTab[] }

/**
 * DL section 3: a sticky strip, the sheet scrolling under it, the floating tab bar under 768 px, the 72 px icon rail
 * at 768 to 1199 px and the 248 px sidebar from 1200 px (05 5.3). `strip` is the optional section strip of a screen.
 */
export function AppShell({ active, strip, children }: { active: string; strip?: Strip; children: ReactNode }) {
  const navigate = useNavigate()
  const items: TabItem[] = TABS.map((t) => ({
    ...t,
    onClick: (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return // let the browser open a new tab
      e.preventDefault()
      navigate(t.href)
    },
  }))
  return (
    <div className="shell">
      <Sprite />
      <aside className="shell-side">
        <Link to="/" className="shell-brand" aria-label="Hermi, Trips">
          <Logo variant="mark" height={36} className="shell-mark" />
          <Logo variant="lockup" mode="light" height={36} className="shell-lockup shell-lockup--light" />
          <Logo variant="lockup" mode="dark" height={36} className="shell-lockup shell-lockup--dark" />
        </Link>
        <nav className="shell-nav" aria-label="Main">
          {TABS.map((t) => (
            <Link key={t.key} to={t.href} className="shell-link" aria-current={t.key === active ? 'page' : undefined}>
              <Icon name={t.icon} />
              <span className="shell-link__label">{t.label}</span>
            </Link>
          ))}
        </nav>
        <div className="shell-trips">Recent trips will show here.</div>
      </aside>
      <div className="shell-main">
        {strip && <SectionTabs className={cx('shell-strip')} items={strip.items} active={strip.active} label={strip.label} />}
        <main className="shell-sheet">{children}</main>
      </div>
      <div className="shell-tabs">
        <TabBar items={items} active={active} label="Tabs" />
      </div>
    </div>
  )
}
