import type {ReactNode} from 'react';

import {cn} from '@/lib/cn';

export interface EmptyStateProps {
  /** Short, translated headline. Say what is absent, not "no data". */
  title: string;
  /** Optional translated sentence explaining what to do next. */
  description?: string;
  /** Decorative glyph shown in the gold ring. Defaults to a plate motif. */
  icon?: ReactNode;
  /** Primary recovery action — usually a `Button` or a locale-aware `Link`. */
  action?: ReactNode;
  className?: string;
}

/** Plate-and-cloche motif: an empty state for a restaurant, not a generic app. */
function PlateIcon() {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      className="size-7"
      aria-hidden="true"
    >
      <path d="M4 22h24" />
      <path d="M6.5 22a9.5 9.5 0 0 1 19 0" />
      <path d="M16 12.5V10" />
      <circle cx="16" cy="8.5" r="1.6" />
    </svg>
  );
}

/**
 * Shown when a list resolves to nothing — an empty category, a search with no
 * match, a table with no scans. Never leave the region blank: an empty screen
 * is indistinguishable from a failed one.
 */
export function EmptyState({title, description, icon, action, className}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-ground-border',
        'bg-ground-surface/60 px-6 py-14 text-center',
        className
      )}
    >
      <span className="flex size-14 items-center justify-center rounded-pill border border-gold-800 bg-ground-elevated text-gold-300">
        {icon ?? <PlateIcon />}
      </span>

      <div className="flex flex-col gap-1.5">
        <p className="font-display text-card text-cream">{title}</p>
        {description ? (
          <p className="max-w-prose text-body text-muted">{description}</p>
        ) : null}
      </div>

      {action}
    </div>
  );
}
