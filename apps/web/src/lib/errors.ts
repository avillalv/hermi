/**
 * True when code failed to load because Hermi was rebuilt since this tab opened (the old
 * page asks for files the new build no longer has). Chrome, Firefox, and Safari word it differently.
 */
export function isStaleBuild(error: unknown): boolean {
  return (
    error instanceof Error &&
    /dynamically imported module|importing a module script failed|unable to preload css/i.test(error.message)
  )
}
