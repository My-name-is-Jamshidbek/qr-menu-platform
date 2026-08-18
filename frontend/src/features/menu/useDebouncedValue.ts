'use client';

import {useEffect, useState} from 'react';

/**
 * Mirrors `value` after it has stopped changing for `delayMs`.
 *
 * Search filters ~105 products and re-renders the grid, which is cheap but not
 * free on the low-end phones this page is built for. Debouncing keeps typing
 * responsive: the input itself stays controlled and instant, only the filtering
 * waits for a pause.
 */
export function useDebouncedValue<TValue>(value: TValue, delayMs: number): TValue {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);

    // Clearing on every change is what makes this a debounce rather than a
    // queue of pending updates.
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
