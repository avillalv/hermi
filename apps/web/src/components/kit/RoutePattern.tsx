import type { SVGProps } from 'react'

/** One dotted route stroke (design/hermi.css `.h-route`). Pass pathLength as dots * 11 (lg 12, sm 9) to fit dots exactly. */
export function RoutePath({
  d,
  traveler,
  size,
  pathLength,
  ...rest
}: { d: string; traveler: 'a' | 'b'; size?: 'lg' | 'sm'; pathLength?: number } & Omit<SVGProps<SVGPathElement>, 'd'>) {
  const cls = ['h-route', `h-route--${traveler}`, size && `h-route--${size}`].filter(Boolean).join(' ')
  return <path className={cls} d={d} pathLength={pathLength} {...rest} />
}

/** The twin pink (traveler a) and yellow (traveler b) dotted routes of 05 section 2.9. Decorative unless `title` is set. */
export function RoutePattern({
  a,
  b,
  viewBox,
  size,
  title,
  ...rest
}: { a: string; b: string; viewBox: string; size?: 'lg' | 'sm'; title?: string } & Omit<SVGProps<SVGSVGElement>, 'viewBox'>) {
  return (
    <svg
      viewBox={viewBox}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      {...rest}
    >
      <RoutePath d={a} traveler="a" size={size} />
      <RoutePath d={b} traveler="b" size={size} />
    </svg>
  )
}
