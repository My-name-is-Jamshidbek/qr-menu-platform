'use client';

import {useEffect} from 'react';
import {useTranslations} from 'next-intl';

import {Container} from '@/components/layout';
import {Button, EmptyState} from '@/components/ui';

/**
 * Shown when the menu cannot be rendered — the API is unreachable, or it
 * answered with something the page could not use.
 *
 * A guest at a table has no way to fix this and no interest in the cause, so the
 * screen offers exactly one action: try again. `reset()` re-renders the segment,
 * which re-runs the fetch.
 */
export default function MenuError({
  error,
  reset
}: {
  error: Error & {digest?: string};
  reset: () => void;
}) {
  useEffect(() => {
    // The digest is the only handle that ties this screen to the server log
    // entry, since the real message is stripped in production.
    console.error('Menu page failed to render', error);
  }, [error]);

  const t = useTranslations('menu.error');

  return (
    <Container as="main" className="py-16">
      <EmptyState
        action={
          <Button onClick={reset} variant="secondary">
            {t('retry')}
          </Button>
        }
        description={t('description')}
        title={t('title')}
      />
    </Container>
  );
}
