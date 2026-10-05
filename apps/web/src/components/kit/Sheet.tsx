import type { HTMLAttributes } from 'react'
import { cx, mods } from './cx'

/** The level 3 bottom sheet (05 4.19). */
export function Sheet({ mod, className, ...rest }: { mod?: Array<'ai' | 'paywall'> } & HTMLAttributes<HTMLDivElement>) {
  return <div className={cx(mods('h-sheet', mod), className)} {...rest} />
}

export const SheetGrabber = () => <div className="h-sheet__grabber" aria-hidden="true" />

export function SheetBody({ mod, className, ...rest }: { mod?: Array<'flush' | 'roomy' | 'snug' | 'tight'> } & HTMLAttributes<HTMLDivElement>) {
  return <div className={cx(mods('h-sheet__body', mod), className)} {...rest} />
}
