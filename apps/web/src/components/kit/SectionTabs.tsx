import type { MouseEventHandler } from 'react'
import { cx } from './cx'

export type SectionTab = { key: string; label: string; href: string; onClick?: MouseEventHandler<HTMLAnchorElement> }

/** 05 5.2. The section strip: a nav of links, the current one marked with aria-current="page". */
export function SectionTabs({ items, active, label, className }: { items: SectionTab[]; active: string; label: string; className?: string }) {
  return (
    <nav className={cx('h-strip', className)} aria-label={label}>
      {items.map((t) => (
        <a key={t.key} className="h-strip__tab" href={t.href} aria-current={t.key === active ? 'page' : undefined} onClick={t.onClick}>
          {t.label}
        </a>
      ))}
    </nav>
  )
}
