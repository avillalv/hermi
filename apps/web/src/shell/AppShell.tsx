import { useSyncExternalStore, type ReactNode } from 'react'
import { Link, useMatch, useNavigate } from 'react-router'
import { SyncIndicator } from '../components/sync-indicator/SyncIndicator'
import { Icon, Logo, SectionTabs, Sprite, TabBar, cx, type SectionTab, type TabItem } from '../components/kit'
import { t } from '../lib/i18n'
import { useAuth } from '../routes/auth/authStore'
import { useTrips } from '../routes/onboarding/trips'
import './shell.css'

export const TABS = [
  { key: 'trips', label: 'Trips', icon: 'luggage', href: '/' },
  { key: 'discover', label: 'Discover', icon: 'compass', href: '/discover' },
  { key: 'activity', label: 'Activity', icon: 'bell', href: '/activity' },
  { key: 'account', label: 'Account', icon: 'circle-user', href: '/account' },
] as const

/** `tripId` marks a trip section: the sync indicator chip (05 4.21) sits above the strip, except on Overview, whose hero pass carries its own. */
export type Strip = { label: string; active: string; items: SectionTab[]; tripId?: string }

/**
 * DL section 3: a sticky strip, the sheet scrolling under it, the floating tab bar under 768 px, the 72 px icon rail
 * at 768 to 1199 px and the 248 px sidebar from 1200 px (05 5.3). `strip` is the optional section strip of a screen.
 */
/** 05 5.3 sidebar trip switcher: the five most recent trips and All trips. The list is the one Trips home loads, so it costs no extra call. */
const SIDEBAR = '(min-width: 1200px)'
const sidebarOn = (cb: () => void) => {
  const m = window.matchMedia?.(SIDEBAR)
  m?.addEventListener('change', cb)
  return () => m?.removeEventListener('change', cb)
}

function TripSwitcher() {
  const { token } = useAuth()
  // Only the 1200 px sidebar shows it, so narrower screens skip the list (and its call) altogether.
  const wide = useSyncExternalStore(sidebarOn, () => !!window.matchMedia?.(SIDEBAR).matches)
  const trips = useTrips(!!token && wide)
  const open = useMatch('/trips/:id/*')?.params.id
  if (!wide || !trips.data?.length) return null
  return (
    <nav className="shell-trips" aria-label={t('trips.switcher')}>
      {trips.data.slice(0, 5).map((tr) => (
        <Link key={tr.id} to={`/trips/${tr.id}`} className="shell-trip" aria-current={tr.id === open ? 'page' : undefined}>
          {tr.name}
        </Link>
      ))}
      <Link to="/" className="shell-trip shell-trip--all">
        {t('trips.allTrips')}
      </Link>
    </nav>
  )
}

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
        <TripSwitcher />
      </aside>
      <div className="shell-main">
        {strip?.tripId && strip.active !== 'overview' && <SyncIndicator tripId={strip.tripId} />}
        {strip && <SectionTabs className={cx('shell-strip')} items={strip.items} active={strip.active} label={strip.label} />}
        <main className="shell-sheet">{children}</main>
      </div>
      <div className="shell-tabs">
        <TabBar items={items} active={active} label="Tabs" />
      </div>
    </div>
  )
}
