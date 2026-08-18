'use client';

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode
} from 'react';

import {cn} from '@/lib/cn';

export type ToastTone = 'info' | 'success' | 'danger';

export interface ToastOptions {
  /** Already-translated message. Toasts never build copy themselves. */
  message: string;
  tone?: ToastTone;
  /** Auto-dismiss delay in ms. `0` keeps the toast until it is dismissed. */
  durationMs?: number;
}

interface ToastRecord extends Required<Omit<ToastOptions, 'durationMs'>> {
  id: number;
  durationMs: number;
}

const TONE_CLASSES: Record<ToastTone, string> = {
  info: 'border-gold-700 text-cream',
  success: 'border-success/60 text-success-text',
  danger: 'border-danger/60 text-danger-text'
};

const ACCENT_CLASSES: Record<ToastTone, string> = {
  info: 'bg-gold-gradient',
  success: 'bg-success',
  danger: 'bg-danger'
};

export interface ToastProps extends ToastOptions {
  /** Translated accessible name for the dismiss button. */
  closeLabel: string;
  onDismiss?: () => void;
  className?: string;
}

/**
 * A single notification. Exported on its own so it can be rendered statically
 * — in the styleguide, or as an inline form result — without a provider.
 */
export function Toast({message, tone = 'info', closeLabel, onDismiss, className}: ToastProps) {
  return (
    <div
      className={cn(
        'pointer-events-auto flex w-[min(24rem,calc(100vw-2rem))] items-start gap-3 overflow-hidden',
        'rounded-md border bg-ground-elevated py-3 pr-3 pl-4 shadow-modal',
        'motion-safe:animate-toast-in',
        TONE_CLASSES[tone],
        className
      )}
    >
      <span className={cn('-my-3 -ml-4 w-1 self-stretch', ACCENT_CLASSES[tone])} aria-hidden="true" />
      <p className="flex-1 text-body">{message}</p>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          aria-label={closeLabel}
          className="-my-1 flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-sm text-cream/60 transition-colors duration-[var(--motion-fast)] hover:bg-ground-border hover:text-cream"
        >
          <svg
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            className="size-4"
            aria-hidden="true"
          >
            <path d="M5 5l10 10M15 5L5 15" />
          </svg>
        </button>
      ) : null}
    </div>
  );
}

interface ToastContextValue {
  show: (options: ToastOptions) => void;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

/**
 * Publishes `useToast()` and renders the live region that hosts the stack.
 *
 * The region is `aria-live="polite"`, so a queued message is announced without
 * interrupting whatever the user is doing — the right level for "saved" and
 * "could not save" alike.
 */
export function ToastProvider({
  children,
  closeLabel
}: {
  children: ReactNode;
  /** Translated accessible name applied to every toast's dismiss button. */
  closeLabel: string;
}) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const nextId = useRef(0);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback(
    ({message, tone = 'info', durationMs = 5000}: ToastOptions) => {
      const id = nextId.current++;
      setToasts((current) => [...current, {id, message, tone, durationMs}]);

      if (durationMs > 0) {
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), durationMs)
        );
      }
    },
    [dismiss]
  );

  const value = useMemo<ToastContextValue>(() => ({show, dismiss}), [show, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 sm:items-end"
      >
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            tone={toast.tone}
            closeLabel={closeLabel}
            onDismiss={() => dismiss(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Queues a toast. Throws when called outside `ToastProvider` — a wiring bug. */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used inside a ToastProvider');
  return context;
}
