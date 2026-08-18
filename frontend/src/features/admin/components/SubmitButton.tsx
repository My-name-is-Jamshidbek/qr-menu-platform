'use client';

import {useFormStatus} from 'react-dom';

import {Button, type ButtonProps} from '@/components/ui';

export interface SubmitButtonProps extends Omit<ButtonProps, 'type' | 'children'> {
  label: string;
  /** Shown while the enclosing form is in flight. Defaults to `label`. */
  pendingLabel?: string;
}

/**
 * Submit control that disables itself while its form is posting.
 *
 * `useFormStatus` reads the state of the *enclosing* form, so one component
 * covers every Server Action form in the panel without any of them having to
 * track a pending flag of their own — and a double click cannot fire the
 * action twice.
 */
export function SubmitButton({label, pendingLabel, ...props}: SubmitButtonProps) {
  const {pending} = useFormStatus();

  return (
    <Button type="submit" disabled={pending} {...props}>
      {pending ? (pendingLabel ?? label) : label}
    </Button>
  );
}
