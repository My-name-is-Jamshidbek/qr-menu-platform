import {getTranslations} from 'next-intl/server';

import {Container} from './Container';

/**
 * Closing band of every public page. Deliberately quiet: one gold hairline, a
 * wordmark and the legal line. The footer is where a gold-heavy design usually
 * collapses into noise, so it gets no fills at all.
 */
export async function SiteFooter() {
  const t = await getTranslations('common');
  const year = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t border-ground-border bg-ground-surface/50">
      <Container
        as="div"
        className="flex flex-col items-center gap-3 py-10 text-center sm:flex-row sm:justify-between sm:text-left"
      >
        <div className="flex flex-col gap-1">
          <span className="font-display text-card tracking-[0.14em] text-cream uppercase">
            {t('site.name')}
          </span>
          <span className="text-label text-muted normal-case tracking-normal">
            {t('site.tagline')}
          </span>
        </div>

        <p className="text-label text-muted normal-case tracking-normal">
          <span className="tabular">&copy; {year}</span> {t('site.name')}. {t('footer.rights')}
        </p>
      </Container>
    </footer>
  );
}
