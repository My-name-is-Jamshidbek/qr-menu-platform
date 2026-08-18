'use client';

import {useId, type TextareaHTMLAttributes} from 'react';

import {cn} from '@/lib/cn';

import {
  CONTROL_CLASSES,
  CONTROL_ERROR_CLASSES,
  describedBy,
  Field,
  type FieldOwnProps
} from './Field';

export interface TextareaProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id'>,
    FieldOwnProps {
  className?: string;
  textareaClassName?: string;
}

/** Multi-line control — product descriptions in the admin panel. */
export function Textarea({
  label,
  hint,
  error,
  labelSuffix,
  className,
  textareaClassName,
  rows = 4,
  ...props
}: TextareaProps) {
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
      <textarea
        id={controlId}
        rows={rows}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(hint, error, hintId, errorId)}
        className={cn(
          CONTROL_CLASSES,
          error && CONTROL_ERROR_CLASSES,
          'resize-y leading-relaxed',
          textareaClassName
        )}
        {...props}
      />
    </Field>
  );
}
