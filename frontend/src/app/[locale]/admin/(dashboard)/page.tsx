import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {EmptyState} from '@/components/ui';
import {StatCard, fetchStats} from '@/features/admin';
import {Link} from '@/i18n/navigation';
import {isAppLocale} from '@/i18n/routing';

/** The dashboard: five counters that say whether the menu needs attention. */

export async function generateMetadata({params}: PageProps<'/[locale]/admin'>): Promise<Metadata> {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  const t = await getTranslations({locale, namespace: 'admin.dashboard'});
  return {title: t('title')};
}

export default async function AdminDashboardPage({params}: PageProps<'/[locale]/admin'>) {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  setRequestLocale(locale);

  const t = await getTranslations({locale, namespace: 'admin.dashboard'});

  let stats;
  try {
    stats = await fetchStats();
  } catch {
    // A dashboard that cannot count is still a working panel; say so and let
    // the person carry on to the product list.
    return <EmptyState title={t('unavailable')} />;
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="font-display text-title text-cream">{t('title')}</h1>
        <p className="text-body text-muted">{t('subtitle')}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label={t('productCount')} value={stats.product_count} />
        <StatCard label={t('availableCount')} value={stats.available_product_count} />
        <StatCard label={t('categoryCount')} value={stats.category_count} />
        <StatCard
          label={t('missingTranslationCount')}
          value={stats.missing_translation_count}
          hint={t('missingHint')}
          tone="attention"
          action={
            <Link
              href="/admin/products"
              className="mt-1 inline-flex min-h-11 items-center text-label text-gold-300 uppercase hover:text-gold-200"
            >
              {t('reviewLink')}
            </Link>
          }
        />
        <StatCard label={t('scans7d')} value={stats.scans_last_7_days} />
      </div>
    </section>
  );
}
