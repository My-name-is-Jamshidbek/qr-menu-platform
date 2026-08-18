import type {ComponentProps} from 'react';

import {Link} from '@/i18n/navigation';
import {cn} from '@/lib/cn';

const BASE_CLASSES =
  'inline-flex min-h-11 items-center justify-center rounded-pill px-4 py-2 text-label ' +
  'uppercase tracking-[0.08em] whitespace-nowrap ' +
  'transition-[background-color,border-color,color,filter] duration-[var(--motion-base)] ease-out';

const ACTIVE_CLASSES = 'bg-gold-gradient text-ink border border-gold-600/50 shadow-card';

const INACTIVE_CLASSES =
  'border border-ground-border bg-ground-surface text-cream/70 ' +
  'hover:border-gold-700 hover:text-gold-200 hover:bg-ground-elevated';

function pillClasses(active: boolean, className: string | undefined): string {
  return cn(BASE_CLASSES, active ? ACTIVE_CLASSES : INACTIVE_CLASSES, className);
}

export interface PillLinkProps extends Omit<ComponentProps<typeof Link>, 'aria-current'> {
  /** The selected category. Sets `aria-current="page"` as well as the gold fill. */
  active?: boolean;
}

/**
 * Category filter entry. It is a real locale-aware link (`/uz/menu/desserts`),
 * not a `useState` toggle, so each filter is shareable, crawlable and works
 * without JavaScript.
 */
export function PillLink({active = false, className, ...props}: PillLinkProps) {
  return (
    <Link
      aria-current={active ? 'page' : undefined}
      className={pillClasses(active, className)}
      {...props}
    />
  );
}

export interface PillProps extends ComponentProps<'span'> {
  active?: boolean;
}

/** Non-navigating variant — labels overlaid on a product image, for example. */
export function Pill({active = false, className, ...props}: PillProps) {
  return <span className={pillClasses(active, className)} {...props} />;
}
