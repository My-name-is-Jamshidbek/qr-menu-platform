'use client';

import {useTranslations} from 'next-intl';

import {Input} from '@/components/ui';

export interface MenuSearchProps {
  value: string;
  onValueChange: (value: string) => void;
  /** Id of the live region announcing how many dishes matched. */
  resultsId: string;
}

function ClearIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeWidth="1.8"
      viewBox="0 0 16 16"
    >
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  );
}

/**
 * Search box over the dishes already on the page.
 *
 * `type="search"` gives mobile keyboards a search key and, on WebKit, a native
 * clear affordance; the explicit button is there because that native control is
 * not keyboard reachable. `aria-controls`/`aria-describedby` tie the field to
 * the live region so a screen reader hears the new result count as it changes.
 */
export function MenuSearch({value, onValueChange, resultsId}: MenuSearchProps) {
  const t = useTranslations('menu.search');

  return (
    <div className="relative w-full max-w-md">
      <Input
        aria-controls={resultsId}
        aria-describedby={resultsId}
        autoComplete="off"
        inputClassName="pr-12"
        label={t('label')}
        onChange={(event) => onValueChange(event.target.value)}
        placeholder={t('placeholder')}
        type="search"
        value={value}
      />

      {value ? (
        <button
          aria-label={t('clear')}
          className="absolute right-1 bottom-0 flex size-11 items-center justify-center rounded-md text-muted transition-colors duration-[var(--motion-fast)] hover:text-gold-200"
          onClick={() => onValueChange('')}
          type="button"
        >
          <ClearIcon />
        </button>
      ) : null}
    </div>
  );
}
