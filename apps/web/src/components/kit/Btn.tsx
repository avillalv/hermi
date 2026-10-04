import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from 'react'
import { cx, mods } from './cx'

type Variant = 'primary' | 'secondary' | 'text'
type Mod = 'sm' | 'icon' | 'lead' | 'spend' | 'stub' | 'wrap'

/** `h-btn` as a button. Pass `variant` and any of `sm icon lead spend stub wrap` in `mod`. Use `LinkBtn` for navigation. */
export function Btn({ variant, mod, className, ...rest }: { variant: Variant; mod?: Mod[] } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={cx(mods('h-btn', [variant, ...(mod ?? [])]), className)} {...rest} />
}

export function LinkBtn({ variant, mod, className, children, ...rest }: { variant: Variant; mod?: Mod[] } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a className={cx(mods('h-btn', [variant, ...(mod ?? [])]), className)} {...rest}>
      {children}
    </a>
  )
}
