import type {ReactNode} from 'react';

import {cn} from '@/lib/cn';

/**
 * Shared chrome for `Input`, `Select` and `Textarea`: label, optional hint and
 * the error message. Keeping it in one place is what guarantees the three
 * controls stay visually identical and wire up `aria-describedby` the same way.
 */
export interface FieldOwnProps {
  /** Visible label. Never omit it — a placeholder is not a label. */
  label: string;
  /** Helper text shown under the control while there is no error. */
  hint?: string;
  /** Validation message. Its presence turns the control into its invalid state. */
  error?: string;
  /**
   * Trailing note next to the label, e.g. a translated "optional" marker.
   * A node rather than a flag, so the copy stays in the caller's message file.
   */
  labelSuffix?: ReactNode;
}

export interface FieldProps extends FieldOwnProps {
  controlId: string;
  hintId: string;
  errorId: string;
  className?: string;
  children: ReactNode;
}

/** Class list every text-entry control shares. */
export const CONTROL_CLASSES =
  'w-full min-h-11 rounded-md border bg-ground-base px-3.5 py-2.5 text-body text-cream ' +
  'border-ground-border placeholder:text-muted ' +
  'transition-[border-color,background-color] duration-[var(--motion-fast)] ease-out ' +
  'hover:border-gold-700 focus:border-gold-500 ' +
  'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-ground-border';

/** Applied on top of `CONTROL_CLASSES` when the field carries an error. */
export const CONTROL_ERROR_CLASSES = 'border-danger hover:border-danger focus:border-danger';

/**
 * Builds the `aria-describedby` value: hint and error are announced together,
 * so a screen reader user hears why the value was rejected and what is allowed.
 */
export function describedBy(
  hint: string | undefined,
  error: string | undefined,
  hintId: string,
  errorId: string
): string | undefined {
  const ids = [hint ? hintId : null, error ? errorId : null].filter(Boolean);
  return ids.length > 0 ? ids.join(' ') : undefined;
}

export function Field({
  label,
  hint,
  error,
  labelSuffix,
  controlId,
  hintId,
  errorId,
  className,
  children
}: FieldProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label
        htmlFor={controlId}
        className="flex items-baseline gap-2 text-label text-gold-200 uppercase"
      >
        {label}
        {labelSuffix ? (
          <span className="text-muted normal-case tracking-normal">{labelSuffix}</span>
        ) : null}
      </label>

      {children}

      {error ? (
        <p id={errorId} className="text-label text-danger-text normal-case tracking-normal">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-label text-muted normal-case tracking-normal">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
