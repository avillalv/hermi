import { useId, type InputHTMLAttributes, type Ref } from 'react'
import { cx } from './cx'
import { Icon } from './Icon'

/**
 * `h-input` (05 4.2): visible label, 44 px field, helper, and an error with a danger icon. The error is linked with
 * `aria-describedby` and `aria-invalid`. Pass `code` for the six digit code look.
 */
export function TextField({
  label,
  helper,
  error,
  code,
  inputRef,
  className,
  id,
  ...rest
}: {
  label: string
  helper?: string
  error?: string | null
  code?: boolean
  inputRef?: Ref<HTMLInputElement>
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'aria-invalid'>) {
  const auto = useId()
  const fid = id ?? auto
  const [helpId, errId] = [`${fid}-help`, `${fid}-error`]
  const describedBy = [error && errId, helper && helpId].filter(Boolean).join(' ')
  return (
    <div className={cx('h-input', error && 'h-input--error')}>
      <label className="h-input__label" htmlFor={fid}>
        {label}
      </label>
      <input
        ref={inputRef}
        id={fid}
        className={cx('h-input__field', code && 'h-input__field--code', className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        {...rest}
      />
      {helper && (
        <p id={helpId} className="h-input__help">
          {helper}
        </p>
      )}
      {error && (
        <p id={errId} role="alert" className="h-input__error">
          <Icon name="circle-alert" size={16} />
          {error}
        </p>
      )}
    </div>
  )
}
