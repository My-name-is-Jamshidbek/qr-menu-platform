import type {HTMLAttributes} from 'react';

import {cn} from '@/lib/cn';

export type BadgeTone = 'gold' | 'outline' | 'neutral' | 'success' | 'danger' | 'warning';

/**
 * `gold` is the metallic price badge — ink on gold, never cream. The status
 * tones are tinted fills rather than saturated blocks so a row of them does not
 * compete with the gold accent.
 */
const TONE_CLASSES: Record<BadgeTone, string> = {
  gold: 'bg-gold-gradient text-ink border border-gold-600/50',
  outline: 'border border-gold-700 text-gold-200 bg-gold-900/30',
  neutral: 'border border-ground-border bg-ground-elevated text-cream/75',
  success: 'border border-success/50 bg-success/15 text-success-text',
  danger: 'border border-danger/50 bg-danger/15 text-danger-text',
  warning: 'border border-warning/50 bg-warning/15 text-warning-text'
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  /** Formats digits with `tabular-nums`. Required for prices and counts. */
  numeric?: boolean;
}

/** A small, non-interactive status or price chip. For links use `Pill`. */
export function Badge({tone = 'neutral', numeric = false, className, ...props}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-sm px-2.5 py-1 text-label whitespace-nowrap',
        TONE_CLASSES[tone],
        numeric && 'tabular font-display text-price',
        className
      )}
      {...props}
    />
  );
}
