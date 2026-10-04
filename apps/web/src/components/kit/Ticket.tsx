import type { ElementType, HTMLAttributes, ReactNode } from 'react'
import { cx, mods } from './cx'
import { Icon } from './Icon'

type TicketMod = 'sky' | 'two-line' | 'lg' | 'float' | 'side' | 'plan' | 'cta' | 'run' | 'evidence' | 'actions' | 'stub-wide' | 'fare'

/**
 * 05 4.4 and 4.21 ticket: div.h-ticket around one card. `as` is the card element (a, label, article or div).
 * Children are the card content: a body or head, then a `TicketStub`. Other props go to the card.
 */
export function TripTicket({
  as: Card = 'div',
  mod,
  className,
  children,
  ...card
}: { as?: ElementType; mod?: TicketMod[]; className?: string; children?: ReactNode } & Record<string, unknown>) {
  return (
    <div className={mods('h-ticket', mod)}>
      <Card className={cx('h-ticket__card', className)} {...card}>
        {children}
      </Card>
    </div>
  )
}

/** The tinted stub under the tear line. `bare` leaves the tear out. */
export function TicketStub({
  as: Tag = 'div',
  bare,
  children,
  className,
  ...rest
}: { as?: ElementType; bare?: boolean } & HTMLAttributes<HTMLElement>) {
  return (
    <Tag className={cx('h-ticket__stub', className)} {...rest}>
      {bare ? null : <span className="h-ticket__tear" aria-hidden="true" />}
      {children}
    </Tag>
  )
}

const STUB_ICON = { booked: 'check', planning: 'pencil', done: 'circle-check', votes: 'heart' } as const

/** A status in a boarding-pass stub. Icon plus text, never color alone. */
export function StatusStub({ status, icon, children }: { status: keyof typeof STUB_ICON; icon?: string; children: ReactNode }) {
  return (
    <span className={`h-stub h-stub--${status}`}>
      <Icon name={icon ?? STUB_ICON[status]} size={14} bold />
      {children}
    </span>
  )
}

/** A label over a value, inside a dl. Values are mono unless `text`. */
export function Field({ label, text, children }: { label: ReactNode; text?: boolean; children: ReactNode }) {
  return (
    <div className={cx('h-field', text && 'h-field--text')}>
      <dt className="h-field__label">{label}</dt>
      <dd className="h-field__value">{children}</dd>
    </div>
  )
}
