/** Join class names, dropping falsy parts. Kit class order (block, then modifiers, then extras) is kept as given. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}

/** `h-block` plus `h-block--mod` for each modifier. */
export function mods(base: string, list: ReadonlyArray<string | false | null | undefined> = []): string {
  return cx(base, ...list.map((m) => m && `${base}--${m}`))
}
