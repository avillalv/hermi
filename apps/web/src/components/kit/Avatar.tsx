import type { HTMLAttributes } from 'react'
import { cx } from './cx'

export type Tone = 't1' | 't2' | 't3' | 't4' | 't5' | 't6' | 't7' | 't8'

/** A traveler's initials in their color. With `label` it is an image with that name; without, it is decorative. */
export function Avatar({
  tone,
  size,
  label,
  className,
  children,
  ...rest
}: { tone: Tone; size?: 'sm' | 'xs'; label?: string } & HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cx('h-avatar', size && `h-avatar--${size}`, `h-avatar--${tone}`, className)}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      {...rest}
    >
      {children}
    </span>
  )
}

/** Overlapping avatars. */
export function Avatars({ className, ...rest }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cx('h-avatars', className)} {...rest} />
}
