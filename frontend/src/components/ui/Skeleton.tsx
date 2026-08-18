import {cn} from '@/lib/cn';

export interface SkeletonProps {
  className?: string;
}

/**
 * Loading placeholder. It is a warm shimmer, not the usual grey pulse: the
 * sweep runs over `--ground-elevated` with a faint gold band, so a loading grid
 * still looks like this product rather than like a generic wireframe.
 *
 * Always decorative — `aria-hidden`. The surrounding region owns the
 * `aria-busy` / `role="status"` announcement.
 */
export function Skeleton({className}: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'block rounded-sm bg-ground-elevated bg-[image:var(--gradient-skeleton)]',
        'bg-[length:200%_100%] motion-safe:animate-skeleton',
        className
      )}
    />
  );
}

/** Card-shaped skeleton matching the product grid: 4:3 image, title, price row. */
export function SkeletonCard({className}: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'overflow-hidden rounded-lg border border-ground-border bg-ground-surface',
        className
      )}
    >
      <Skeleton className="aspect-[4/3] w-full rounded-none" />
      <div className="flex flex-col gap-3 p-5">
        <Skeleton className="h-4 w-3/5" />
        <Skeleton className="h-3 w-4/5" />
        <Skeleton className="h-6 w-24 rounded-sm" />
      </div>
    </div>
  );
}
