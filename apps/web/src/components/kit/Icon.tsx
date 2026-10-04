import type { SVGProps } from 'react'
import { cx } from './cx'

/** A lucide line icon from the sprite (`<Sprite />` must be on the page). `name` is the symbol id without `i-`. */
export function Icon({
  name,
  size = 22,
  bold,
  heavy,
  className,
  ...rest
}: { name: string; size?: number; bold?: boolean; heavy?: boolean } & Omit<SVGProps<SVGSVGElement>, 'name'>) {
  return (
    <svg
      className={cx('h-icon', bold && 'h-icon--bold', heavy && 'h-icon--heavy', className)}
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      <use href={`#i-${name}`} />
    </svg>
  )
}
