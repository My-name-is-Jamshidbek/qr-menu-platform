import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {ProductForm, fetchCategories, toCategoryOptions} from '@/features/admin';
import {isAppLocale} from '@/i18n/routing';

/**
 * Creating a product. Photos are not offered here: a `ProductImage` needs a
 * product to hang off, so the form saves first and the edit screen it lands on
 * carries the uploader.
 */

export async function generateMetadata({
  params
}: PageProps<'/[locale]/admin/products/new'>): Promise<Metadata> {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  const t = await getTranslations({locale, namespace: 'admin.form'});
  return {title: t('createTitle')};
}

export default async function NewProductPage({params}: PageProps<'/[locale]/admin/products/new'>) {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  setRequestLocale(locale);

  const t = await getTranslations({locale, namespace: 'admin.form'});
  const tImages = await getTranslations({locale, namespace: 'admin.images'});
  const categories = await fetchCategories();

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="font-display text-title text-cream">{t('createTitle')}</h1>
        <p className="text-body text-muted">{t('createSubtitle')}</p>
      </div>

      <ProductForm locale={locale} categories={toCategoryOptions(categories, locale)} />

      <p className="text-label text-muted normal-case tracking-normal">{tImages('saveFirst')}</p>
    </section>
  );
}
