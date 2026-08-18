'use client';

import {useEffect, useId, useRef, type ReactNode} from 'react';

import {cn} from '@/lib/cn';

export interface DialogProps {
  open: boolean;
  /** Called on Escape, backdrop click and close-button press. */
  onClose: () => void;
  /** Translated dialog title. Becomes the accessible name. */
  title: string;
  /** Translated accessible name for the close button. */
  closeLabel: string;
  /** Optional translated sentence under the title. */
  description?: string;
  /** Footer actions, laid out right-aligned. */
  footer?: ReactNode;
  children?: ReactNode;
  className?: string;
}

/**
 * Modal built on the native `<dialog>` element. `showModal()` gives the focus
 * trap, the inert background, the top-layer stacking and Escape handling for
 * free — a hand-rolled portal would reimplement all four, worse.
 *
 * The backdrop is styled through `::backdrop` in `globals.css`.
 */
export function Dialog({
  open,
  onClose,
  title,
  closeLabel,
  description,
  footer,
  children,
  className
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = `${titleId}-description`;

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    if (open && !element.open) {
      element.showModal();
    } else if (!open && element.open) {
      element.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      // Fires for Escape as well as `close()`, so both paths stay in sync
      // with the caller's state.
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
      // The dialog element itself fills the top layer; a click that lands on it
      // rather than on the inner panel is a backdrop click.
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      className={cn(
        'm-auto w-[min(34rem,calc(100vw-2rem))] rounded-lg border border-ground-border',
        'bg-ground-surface p-0 text-cream shadow-modal',
        'backdrop:bg-ground-base/70 backdrop:backdrop-blur-[3px]',
        'open:motion-safe:animate-toast-in',
        className
      )}
    >
      <div className="flex items-start justify-between gap-4 border-b border-ground-border px-6 py-5">
        <div className="flex flex-col gap-1">
          <h2 id={titleId} className="font-display text-title text-cream">
            {title}
          </h2>
          {description ? (
            <p id={descriptionId} className="text-body text-muted">
              {description}
            </p>
          ) : null}
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label={closeLabel}
          className={cn(
            'flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-md',
            'text-cream/70 transition-colors duration-[var(--motion-fast)]',
            'hover:bg-ground-elevated hover:text-gold-200'
          )}
        >
          <svg
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            className="size-5"
            aria-hidden="true"
          >
            <path d="M5 5l10 10M15 5L5 15" />
          </svg>
        </button>
      </div>

      {children ? <div className="px-6 py-5 text-body text-cream/80">{children}</div> : null}

      {footer ? (
        <div className="flex flex-wrap justify-end gap-3 border-t border-ground-border px-6 py-4">
          {footer}
        </div>
      ) : null}
    </dialog>
  );
}
