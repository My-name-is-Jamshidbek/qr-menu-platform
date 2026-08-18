'use client';

import {useId, type SelectHTMLAttributes} from 'react';

import {cn} from '@/lib/cn';

import {
  CONTROL_CLASSES,
  CONTROL_ERROR_CLASSES,
  describedBy,
  Field,
  type FieldOwnProps
} from './Field';

export interface SelectProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'id'>,
    FieldOwnProps {
  className?: string;
  selectClassName?: string;
}

/**
 * Native `<select>`, restyled rather than reimplemented: the OS picker is
 * faster on a phone, accessible for free, and adds nothing to the bundle.
 * The chevron is a background image so the control keeps its native behaviour.
 */
export function Select({
  label,
  hint,
  error,
  labelSuffix,
  className,
  selectClassName,
  children,
  ...props
}: SelectProps) {
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
      <select
        id={controlId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(hint, error, hintId, errorId)}
        className={cn(
          CONTROL_CLASSES,
          error && CONTROL_ERROR_CLASSES,
          'cursor-pointer appearance-none bg-[image:var(--chevron-down)] bg-[length:0.7rem] bg-[position:right_1rem_center] bg-no-repeat pr-10',
          selectClassName
        )}
        {...props}
      >
        {children}
      </select>
    </Field>
  );
}
