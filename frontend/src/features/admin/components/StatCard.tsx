import type {ReactNode} from 'react';

import {Card} from '@/components/ui';
import {cn} from '@/lib/cn';

/**
 * One dashboard counter. The number leads and the label follows, because the
 * whole point of the screen is to be readable at a glance from behind a
 * counter, not to be studied.
 */
export interface StatCardProps {
  label: string;
  value: number;
  hint?: string;
  /** Draws attention to a number that means work is outstanding. */
  tone?: 'neutral' | 'attention';
  /** Optional link or button rendered under the hint. */
  action?: ReactNode;
}

export function StatCard({label, value, hint, tone = 'neutral', action}: StatCardProps) {
  const isAttention = tone === 'attention' && value > 0;

  return (
    <Card
      tone="surface"
      className={cn('flex flex-col gap-2 p-5', isAttention && 'border-warning/50')}
    >
      <p className="text-label text-muted uppercase">{label}</p>
      <p
        className={cn(
          'tabular font-display text-title leading-none',
          isAttention ? 'text-warning-text' : 'text-gold-300'
        )}
      >
        {value}
      </p>
      {hint ? <p className="text-label text-muted normal-case tracking-normal">{hint}</p> : null}
      {action}
    </Card>
  );
}
