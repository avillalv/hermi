import markUrl from '../../../../../app-buildout/brand/hermi-mark.svg'
import wordmarkUrl from '../../../../../app-buildout/brand/hermi-wordmark.svg'
import wordmarkLightUrl from '../../../../../app-buildout/brand/hermi-wordmark-light.svg'
import lockupUrl from '../../../../../app-buildout/brand/hermi-logo-transparent.svg'
import lockupDarkUrl from '../../../../../app-buildout/brand/hermi-logo-dark-transparent.svg'

export type LogoVariant = 'mark' | 'wordmark' | 'lockup'

const SRC: Record<LogoVariant, Record<'light' | 'dark', string>> = {
  mark: { light: markUrl, dark: markUrl },
  wordmark: { light: wordmarkUrl, dark: wordmarkLightUrl },
  lockup: { light: lockupUrl, dark: lockupDarkUrl },
}

/** The Hermi logo from the brand SVGs. `mode` is the surface it sits on: dark text goes on light, light text on dark. */
export function Logo({
  variant = 'lockup',
  mode = 'light',
  height = 32,
  className,
}: {
  variant?: LogoVariant
  mode?: 'light' | 'dark'
  height?: number
  className?: string
}) {
  return <img src={SRC[variant][mode]} alt="Hermi" height={height} className={className} style={{ height, width: 'auto' }} />
}
