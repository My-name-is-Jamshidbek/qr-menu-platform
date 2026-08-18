import {cn} from '@/lib/cn';

export interface MonogramPlaceholderProps {
  /**
   * Source of the monogram — the product's *translated* name. The initials are
   * derived from it so the placeholder differs per item instead of repeating
   * one generic icon down the grid.
   */
  name: string;
  className?: string;
}

/** Up to two initials, from the first two words. Handles Cyrillic and Latin alike. */
function initialsOf(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) return '';

  return words
    .slice(0, 2)
    .map((word) => [...word][0] ?? '')
    .join('')
    .toLocaleUpperCase();
}

/**
 * Stands in for a missing product image. A broken `<img>` is never acceptable,
 * and a grey box is not either — this is an embossed gold monogram on the warm
 * ground, framed by a hairline ring.
 *
 * Purely decorative: the product name is already announced by the card heading,
 * so repeating it here would make a screen reader read every item twice.
 */
export function MonogramPlaceholder({name, className}: MonogramPlaceholderProps) {
  const initials = initialsOf(name);

  return (
    <div
      aria-hidden="true"
      className={cn(
        '@container relative flex items-center justify-center overflow-hidden bg-ground-elevated',
        'bg-[radial-gradient(60%_60%_at_50%_38%,var(--gold-900),transparent_70%)]',
        className
      )}
    >
      <span className="absolute inset-3 rounded-[inherit] border border-gold-800" />
      <span className="font-display text-gold-gradient text-[clamp(1.5rem,16cqi,4rem)] leading-none font-semibold tracking-[0.04em]">
        {initials}
      </span>
    </div>
  );
}
