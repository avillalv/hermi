import { useEffect, useId, useRef, type ReactNode } from "react"

const FOCUSABLE = "button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex]:not([tabindex='-1'])"

/**
 * A modal bottom sheet (05 4.19): a scrim, a dialog that slides up on phones and centers from 768 px, Escape closes,
 * Tab stays inside, and focus returns to what opened it. shortcut: no swipe-to-dismiss; the Close button and Escape are the ways out.
 */
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const id = useId()
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const was = document.activeElement as HTMLElement | null
    ;(box.current?.querySelector<HTMLElement>(FOCUSABLE) ?? box.current)?.focus()
    return () => was?.focus?.()
  }, [])
  // A native listener, so the dialog div carries no handler prop (jsx-a11y): the keys are a modal's own, not a control's.
  useEffect(() => {
    const el = box.current
    if (!el) return
    const keys = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== "Tab") return
      const els = [...el.querySelectorAll<HTMLElement>(FOCUSABLE)]
      const [first, last] = [els[0], els[els.length - 1]]
      if (!first || !last) return
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    el.addEventListener("keydown", keys)
    return () => el.removeEventListener("keydown", keys)
  }, [onClose])
  return (
    <div className="plan__modal">
      <div className="plan__scrim" onClick={onClose} aria-hidden="true" />
      <div className="plan__dialog" role="dialog" aria-modal="true" aria-labelledby={id} tabIndex={-1} ref={box}>
        <div className="h-sheet__grabber" aria-hidden="true" />
        <h2 className="h-title" id={id}>
          {title}
        </h2>
        {children}
      </div>
    </div>
  )
}
