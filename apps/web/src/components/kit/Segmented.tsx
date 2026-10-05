import type { AnchorHTMLAttributes, ButtonHTMLAttributes, HTMLAttributes } from 'react'
import { cx } from './cx'

/** 05 4.21 segmented control: a tablist of buttons, state from aria-selected. */
export function SegmentedControl({ narrow, className, ...rest }: { narrow?: boolean } & HTMLAttributes<HTMLDivElement>) {
  return <div className={cx('h-seg', narrow && 'h-seg--narrow', className)} role="tablist" {...rest} />
}

export function SegItem({ selected, className, ...rest }: { selected?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={cx('h-seg__item', className)} type="button" role="tab" aria-selected={!!selected} {...rest} />
}

/** 05 4.7 day chips: a scrolling tablist of days. */
export function DayChips({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx('h-daychips', className)} role="tablist" {...rest} />
}

/** `current` marks today (aria-current="date"). */
export function DayChip({
  selected,
  current,
  className,
  children,
  ...rest
}: { selected?: boolean; current?: boolean } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a className={cx('h-daychip', className)} role="tab" aria-selected={!!selected} aria-current={current ? 'date' : undefined} {...rest}>
      {children}
    </a>
  )
}
