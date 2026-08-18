import type {ButtonHTMLAttributes, ReactNode} from 'react';

import {cn} from '@/lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

/**
 * `primary` is the gold-gradient call to action with ink text — one per view.
 * `secondary` is the gold-outlined default. `ghost` is for toolbars and table
 * rows, where a border would add noise. `danger` is destructive only.
 */
const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-gold-gradient text-ink shadow-card hover:brightness-110 active:brightness-95 ' +
    'border border-gold-600/60',
  secondary:
    'border border-gold-600 text-gold-200 bg-transparent ' +
    'hover:border-gold-400 hover:bg-gold-900/40 hover:text-gold-100 active:bg-gold-900/60',
  ghost:
    'border border-transparent text-cream/80 bg-transparent ' +
    'hover:bg-ground-elevated hover:text-cream active:bg-ground-border',
  danger:
    'bg-danger text-cream border border-danger shadow-card ' +
    'hover:brightness-110 active:brightness-95'
};

/**
 * Every size clears the 44x44px minimum hit area: `sm` reaches it through
 * `min-h`, not through padding, so a short label still gets a full target.
 */
const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'min-h-11 px-3.5 py-2 text-label uppercase tracking-[0.08em]',
  md: 'min-h-11 px-5 py-2.5 text-[0.9375rem]',
  lg: 'min-h-13 px-7 py-3 text-card font-display'
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Renders full-bleed on mobile-width containers. */
  block?: boolean;
  /** Leading decorative node. Keep it non-essential — labels carry meaning. */
  iconStart?: ReactNode;
  iconEnd?: ReactNode;
}

export function Button({
  variant = 'secondary',
  size = 'md',
  block = false,
  iconStart,
  iconEnd,
  className,
  type = 'button',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex cursor-pointer items-center justify-center gap-2 rounded-md font-medium',
        'transition-[filter,background-color,border-color,color,box-shadow] duration-[var(--motion-base)] ease-out',
        'disabled:pointer-events-none disabled:opacity-45',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        block && 'w-full',
        className
      )}
      {...props}
    >
      {iconStart ? <span aria-hidden="true">{iconStart}</span> : null}
      {children}
      {iconEnd ? <span aria-hidden="true">{iconEnd}</span> : null}
    </button>
  );
}
