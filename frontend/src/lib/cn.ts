/**
 * Class name composition.
 *
 * Deliberately dependency-free: `clsx` and `tailwind-merge` would add ~8 KB to
 * every client bundle for behaviour this project does not need. Components in
 * `src/components/ui` own their base classes and expose variants, so callers
 * append rather than override, and last-wins conflict resolution never comes up.
 */

export type ClassValue =
  | string
  | number
  | null
  | undefined
  | false
  | ClassValue[]
  | {[key: string]: boolean | null | undefined};

/**
 * Joins truthy class values into a single space-separated string.
 *
 * @example
 * cn('px-4', isActive && 'text-gold-300', {'opacity-50': disabled})
 */
export function cn(...inputs: ClassValue[]): string {
  const classes: string[] = [];

  for (const input of inputs) {
    if (!input) continue;

    if (typeof input === 'string' || typeof input === 'number') {
      classes.push(String(input));
    } else if (Array.isArray(input)) {
      const nested = cn(...input);
      if (nested) classes.push(nested);
    } else {
      for (const [key, enabled] of Object.entries(input)) {
        if (enabled) classes.push(key);
      }
    }
  }

  return classes.join(' ');
}
