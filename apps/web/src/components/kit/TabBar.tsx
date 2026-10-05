import type { MouseEventHandler } from 'react'
import { cx } from './cx'
import { Icon } from './Icon'

export type TabItem = { key: string; label: string; icon: string; href: string; badge?: number; onClick?: MouseEventHandler<HTMLAnchorElement> }

/** Text shown in the badge: the count up to 9, then 9+. */
export const badgeText = (n: number) => (n > 9 ? '9+' : String(n))

/** 05 4.20. The floating pill. The active tab carries aria-current="page"; a badge gives its tab the name "Activity, 3 new". */
export function TabBar({ items, active, label = 'Main' }: { items: TabItem[]; active: string; label?: string }) {
  return (
    <nav className="h-tabbar" aria-label={label}>
      <div className="h-tabbar__bar">
        {items.map((t) => {
          const on = t.key === active
          const count = t.badge && t.badge > 0 ? t.badge : 0
          return (
            <a
              key={t.key}
              className={cx('h-tabbar__item', on && 'h-tabbar__item--active')}
              href={t.href}
              aria-current={on ? 'page' : undefined}
              aria-label={count ? `${t.label}, ${count} new` : undefined}
              onClick={t.onClick}
            >
              <Icon name={t.icon} />
              <span>{t.label}</span>
              {count ? (
                <span className="h-tabbar__badge" aria-hidden="true">
                  {badgeText(count)}
                </span>
              ) : null}
            </a>
          )
        })}
      </div>
    </nav>
  )
}
