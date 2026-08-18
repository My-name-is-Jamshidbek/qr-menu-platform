import {cn} from '@/lib/cn';

export type SpinnerSize = 'sm' | 'md' | 'lg';

const SIZE_CLASSES: Record<SpinnerSize, string> = {
  sm: 'size-4 border-2',
  md: 'size-6 border-2',
  lg: 'size-10 border-[3px]'
};

export interface SpinnerProps {
  size?: SpinnerSize;
  /**
   * Accessible name. Pass a translated string when the spinner is the only
   * thing on screen; omit it when a neighbouring element already announces
   * the loading state, so the status is not read out twice.
   */
  label?: string;
  className?: string;
}

/**
 * Indeterminate progress. The ring is dim gold with one bright quadrant, so the
 * rotation is legible without the element becoming a gold blob.
 *
 * Under `prefers-reduced-motion` the global rule collapses the animation, and
 * the ring then reads as a static gold arc rather than a spinning one.
 */
export function Spinner({size = 'md', label, className}: SpinnerProps) {
  return (
    <span
      role={label ? 'status' : undefined}
      aria-hidden={label ? undefined : true}
      className={cn('inline-flex items-center', className)}
    >
      <span
        className={cn(
          'inline-block animate-spin rounded-pill border-gold-800 border-t-gold-300',
          SIZE_CLASSES[size]
        )}
      />
      {label ? <span className="sr-only">{label}</span> : null}
    </span>
  );
}
