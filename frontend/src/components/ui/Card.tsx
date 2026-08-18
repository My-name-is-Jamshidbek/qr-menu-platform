import type {HTMLAttributes} from 'react';

import {cn} from '@/lib/cn';

export type CardTone = 'surface' | 'elevated';

const TONE_CLASSES: Record<CardTone, string> = {
  surface: 'bg-ground-surface',
  elevated: 'bg-ground-elevated'
};

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  tone?: CardTone;
  /**
   * Adds the hover lift used by the product grid: 1.02 scale plus a deeper
   * shadow. Reduced-motion users get the shadow without the scale, because the
   * global motion rule collapses the transition rather than the transform.
   */
  interactive?: boolean;
}

/**
 * The primary object of the menu. A gold hairline border, `lg` radius and a
 * warm shadow are what separate it from a plain grey box.
 */
export function Card({tone = 'surface', interactive = false, className, ...props}: CardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-ground-border shadow-card',
        TONE_CLASSES[tone],
        interactive &&
          'transition-[transform,box-shadow,border-color] duration-[var(--motion-base)] ease-out ' +
            'hover:-translate-y-0.5 hover:border-gold-700 hover:shadow-lifted ' +
            'focus-within:border-gold-700 focus-within:shadow-lifted ' +
            'motion-reduce:hover:translate-y-0',
        className
      )}
      {...props}
    />
  );
}

/** Header row of a card: title on the left, price badge or action on the right. */
export function CardHeader({className, ...props}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex items-start justify-between gap-4 px-5 pt-5 pb-3', className)}
      {...props}
    />
  );
}

export function CardTitle({className, ...props}: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('font-display text-card text-cream', className)} {...props} />;
}

export function CardBody({className, ...props}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-5 pb-5 text-body text-cream/75', className)} {...props} />;
}

export function CardFooter({className, ...props}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 border-t border-ground-border px-5 py-4',
        className
      )}
      {...props}
    />
  );
}
