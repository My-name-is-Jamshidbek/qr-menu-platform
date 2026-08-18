'use client';

import {useId, type InputHTMLAttributes} from 'react';

import {cn} from '@/lib/cn';

import {
  CONTROL_CLASSES,
  CONTROL_ERROR_CLASSES,
  describedBy,
  Field,
  type FieldOwnProps
} from './Field';

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'>,
    FieldOwnProps {
  /** Wrapper class. Use `inputClassName` to reach the control itself. */
  className?: string;
  inputClassName?: string;
  /** Right-aligns and tabularises the value. For prices and quantities. */
  numeric?: boolean;
}

/** Single-line text control with its label, hint and error wired for a11y. */
export function Input({
  label,
  hint,
  error,
  labelSuffix,
  className,
  inputClassName,
  numeric = false,
  type = 'text',
  ...props
}: InputProps) {
  const controlId = useId();
  const hintId = `${controlId}-hint`;
  const errorId = `${controlId}-error`;

  return (
    <Field
      label={label}
      hint={hint}
      error={error}
      labelSuffix={labelSuffix}
      controlId={controlId}
      hintId={hintId}
      errorId={errorId}
      className={className}
    >
      <input
        id={controlId}
        type={type}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(hint, error, hintId, errorId)}
        className={cn(
          CONTROL_CLASSES,
          error && CONTROL_ERROR_CLASSES,
          numeric && 'tabular text-right font-display',
          inputClassName
        )}
        {...props}
      />
    </Field>
  );
}
