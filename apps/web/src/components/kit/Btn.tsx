import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from 'react'
import { cx, mods } from './cx'

type Variant = 'primary' | 'secondary' | 'text'
type Mod = 'sm' | 'icon' | 'lead' | 'spend' | 'stub' | 'wrap' | 'apple'

/**
 * `h-btn` as a button. Pass `variant` and any of `sm icon lead spend stub wrap apple` in `mod`. Use `LinkBtn` for navigation.
 * `busy` (05 4.1 loading) sets aria-busy, swaps the label for a 16 px spinner at the same width and blocks repeat taps.
 */
export function Btn({
  variant,
  mod,
  className,
  busy,
  onClick,
  children,
  ...rest
}: { variant: Variant; mod?: Mod[]; busy?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cx(mods('h-btn', [variant, ...(mod ?? [])]), className)}
      aria-busy={busy || undefined}
      onClick={busy ? (e) => e.preventDefault() : onClick}
      {...rest}
    >
      {busy === undefined ? (
        children
      ) : (
        <>
          <span className="h-btn__label">{children}</span>
          {busy && <span className="h-btn__spin" aria-hidden="true" />}
        </>
      )}
    </button>
  )
}

export function LinkBtn({ variant, mod, className, children, ...rest }: { variant: Variant; mod?: Mod[] } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a className={cx(mods('h-btn', [variant, ...(mod ?? [])]), className)} {...rest}>
      {children}
    </a>
  )
}
